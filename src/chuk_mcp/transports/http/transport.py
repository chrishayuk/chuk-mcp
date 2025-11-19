# chuk_mcp/transports/http/transport.py
"""
Streamable HTTP transport implementation for MCP - Clean version.

This version properly handles SSE responses and connection management with
minimal error logging for expected conditions.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional, Tuple

# PERFORMANCE: Use fast JSON implementation (orjson if available, stdlib json fallback)
from chuk_mcp.protocol import fast_json as json

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import StreamableHTTPParameters

logger = logging.getLogger(__name__)


class StreamableHTTPTransport(Transport):
    """
    Streamable HTTP transport for MCP (spec 2025-03-26).

    Clean version with proper SSE handling and minimal error logging.
    """

    def __init__(self, parameters: StreamableHTTPParameters):
        super().__init__(parameters)
        self.endpoint_url = parameters.url
        self.headers = parameters.headers or {}
        self.timeout = parameters.timeout
        self.enable_streaming = parameters.enable_streaming
        self.max_concurrent_requests = parameters.max_concurrent_requests

        # Session management
        self._session_id: Optional[str] = parameters.session_id
        self._connected = asyncio.Event()

        # Message handling - using futures for compatibility
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_lock = asyncio.Lock()

        # Request handling
        self._outgoing_task: Optional[asyncio.Task] = None
        self._request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Memory streams for chuk_mcp message API
        self._incoming_send: Optional[MemoryObjectSendStream] = None
        self._incoming_recv: Optional[MemoryObjectReceiveStream] = None
        self._outgoing_send: Optional[MemoryObjectSendStream] = None
        self._outgoing_recv: Optional[MemoryObjectReceiveStream] = None

    async def get_streams(
        self,
    ) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        if not self._incoming_recv or not self._outgoing_send:
            raise RuntimeError("Transport not started - use as async context manager")
        return self._incoming_recv, self._outgoing_send

    async def __aenter__(self):
        """Enter async context and set up HTTP transport."""
        # Create memory streams
        from anyio import create_memory_object_stream

        self._incoming_send, self._incoming_recv = create_memory_object_stream(100)
        self._outgoing_send, self._outgoing_recv = create_memory_object_stream(100)

        # Start message handler
        self._outgoing_task = asyncio.create_task(self._outgoing_message_handler())

        # Signal connection is ready
        self._connected.set()
        logger.debug(f"Streamable HTTP transport ready: {self.endpoint_url}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        # Cancel tasks
        if self._outgoing_task and not self._outgoing_task.done():
            self._outgoing_task.cancel()
            try:
                await self._outgoing_task
            except asyncio.CancelledError:
                pass

        # Close streams
        if self._incoming_send:
            await self._incoming_send.aclose()
        if self._outgoing_send:
            await self._outgoing_send.aclose()

        return False

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        pass

    async def _outgoing_message_handler(self) -> None:
        """Handle outgoing messages from the write stream."""
        if not self._outgoing_recv:
            return

        try:
            async for message in self._outgoing_recv:
                await self._send_message_via_http(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in outgoing message handler: {e}")

    async def _send_message_via_http(self, message) -> None:
        """Send a message via HTTP POST with streamable response handling."""
        # Use semaphore to limit concurrent requests
        async with self._request_semaphore:
            await self._send_message_internal(message)

    async def _send_message_internal(self, message) -> None:
        """Internal message sending with proper SSE handling."""
        try:
            # Convert message to dict
            if hasattr(message, "model_dump"):
                message_dict = message.model_dump(exclude_none=True)
            elif isinstance(message, dict):
                message_dict = message
            else:
                logger.error(f"Cannot serialize message of type {type(message)}")
                return

            message_id = message_dict.get("id")
            method = message_dict.get("method", "unknown")

            logger.debug(f"Sending HTTP message: {method} (id: {message_id})")

            # Prepare headers - MUST accept both JSON and SSE
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }

            # Copy headers from transport configuration
            if self.headers:
                for key, value in self.headers.items():
                    # Don't override Content-Type or Accept
                    if key not in ["Content-Type", "Accept"]:
                        headers[key] = value

            # Add bearer token if configured (and not already present)
            if "Authorization" not in headers:
                bearer_token = os.getenv("MCP_BEARER_TOKEN")
                if bearer_token:
                    if bearer_token.startswith("Bearer "):
                        headers["Authorization"] = bearer_token
                    else:
                        headers["Authorization"] = f"Bearer {bearer_token}"

            # Add session ID if available
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id

            # Create a new client for each request to avoid connection reuse issues
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                try:
                    response = await client.post(
                        self.endpoint_url, json=message_dict, headers=headers
                    )

                    logger.debug(f"HTTP response status: {response.status_code}")
                    logger.debug(f"HTTP response headers: {dict(response.headers)}")

                    # Handle error status codes
                    if response.status_code >= 400:
                        error_text = response.text
                        logger.debug(
                            f"Server error for {message_id}: HTTP {response.status_code}: {error_text}"
                        )

                        # Send error response
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "error": {
                                "code": -32603,
                                "message": f"HTTP {response.status_code}: {error_text}",
                            },
                        }
                        await self._route_response(error_response)
                        return

                    # Extract session ID from response if provided
                    if "mcp-session-id" in response.headers:
                        self._session_id = response.headers["mcp-session-id"]
                        logger.debug(f"Updated session ID: {self._session_id}")

                    content_type = response.headers.get("content-type", "")

                    if "application/json" in content_type:
                        # Immediate JSON response
                        try:
                            response_data = response.json()
                            logger.debug(
                                f"Got immediate JSON response for {message_id}"
                            )
                            await self._route_response(response_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {"code": -32700, "message": "Parse error"},
                            }
                            await self._route_response(error_response)

                    elif "text/event-stream" in content_type:
                        # SSE streaming response
                        logger.debug(f"Processing SSE response for {message_id}")
                        await self._process_sse_response(response, message_id)
                    else:
                        # Unexpected content type - try to parse as JSON anyway
                        logger.debug(f"Unexpected content type: {content_type}")
                        try:
                            # Try to read the response body
                            response_text = response.text

                            # Empty response (like 202 Accepted with no body)
                            if not response_text:
                                logger.debug(f"Empty response body for {message_id}")
                                # For notifications, this is fine
                                if not message_id:
                                    return
                                # For requests, send an empty success response
                                success_response = {
                                    "jsonrpc": "2.0",
                                    "id": message_id,
                                    "result": {},
                                }
                                await self._route_response(success_response)
                                return

                            # If it looks like SSE, process it as SSE
                            if response_text.startswith(
                                "event:"
                            ) or response_text.startswith("data:"):
                                await self._process_sse_text(response_text, message_id)
                            else:
                                # Try JSON parsing
                                response_data = json.loads(response_text)
                                await self._route_response(response_data)
                        except Exception as e:
                            logger.debug(f"Could not parse response: {e}")
                            # For empty 202 responses, don't treat as error
                            if response.status_code == 202:
                                logger.debug(f"202 Accepted for {message_id}")
                                return
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {"code": -32603, "message": str(e)},
                            }
                            await self._route_response(error_response)

                except asyncio.TimeoutError:
                    logger.error(f"Timeout for {message_id}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {"code": -32000, "message": "Request timeout"},
                    }
                    await self._route_response(error_response)

                except Exception as e:
                    logger.debug(f"Error sending message {message_id}: {e}")
                    # Connection errors are common and will be retried
                    if (
                        "disconnected" in str(e).lower()
                        or "connection" in str(e).lower()
                    ):
                        logger.debug(
                            f"Connection error for {message_id}, will be retried"
                        )
                    else:
                        logger.error(f"Error sending message {message_id}: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {"code": -32603, "message": str(e)},
                    }
                    await self._route_response(error_response)

        except Exception as e:
            logger.error(f"Error in HTTP message sending: {e}")
            import traceback

            traceback.print_exc()

    async def _process_sse_response(
        self, response: httpx.Response, message_id: str
    ) -> None:
        """Process SSE streaming response."""
        try:
            buffer = ""
            current_event = None
            event_data: list[str] = []

            # Read the full response if not streaming
            if hasattr(response, "text"):
                # Response is already fully loaded
                text = response.text
                await self._process_sse_text(text, message_id)
                return

            # Process streaming response
            async for chunk in response.aiter_text(chunk_size=1024):
                if not chunk:
                    continue

                buffer += chunk

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.rstrip("\r")

                    if not line:
                        # Empty line marks end of event
                        if current_event and event_data:
                            await self._process_sse_event(
                                current_event, event_data, message_id
                            )
                        current_event = None
                        event_data = []
                        continue

                    # Parse SSE format
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                    elif line.startswith("data: "):
                        data = line[6:]  # Keep formatting
                        event_data.append(data)

            # Process any remaining event
            if current_event and event_data:
                await self._process_sse_event(current_event, event_data, message_id)

        except Exception as e:
            logger.error(f"Error processing SSE response: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": -32603, "message": str(e)},
            }
            await self._route_response(error_response)

    async def _process_sse_text(self, text: str, message_id: str) -> None:
        """Process SSE text that's already fully loaded."""
        try:
            lines = text.split("\n")
            current_event = None
            event_data: list[str] = []

            for line in lines:
                line = line.rstrip("\r")

                if not line:
                    # Empty line marks end of event
                    if current_event and event_data:
                        await self._process_sse_event(
                            current_event, event_data, message_id
                        )
                    current_event = None
                    event_data = []
                    continue

                # Parse SSE format
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: "):
                    data = line[6:]  # Keep formatting
                    event_data.append(data)

            # Process any remaining event
            if current_event and event_data:
                await self._process_sse_event(current_event, event_data, message_id)

        except Exception as e:
            logger.error(f"Error processing SSE text: {e}")

    async def _process_sse_event(
        self, event_type: str, data_lines: list, message_id: str
    ) -> None:
        """Process a complete SSE event."""
        try:
            # Join data lines
            full_data = "\n".join(data_lines)

            logger.debug(f"Processing SSE event '{event_type}' for {message_id}")

            # Handle message events (the actual response)
            if event_type in ["message", "response", None]:
                if full_data.strip().startswith("{"):
                    try:
                        response_data = json.loads(full_data.strip())
                        await self._route_response(response_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SSE message JSON: {e}")

        except Exception as e:
            logger.error(f"Error processing SSE event: {e}")

    async def _route_response(self, response_data: Dict[str, Any]) -> None:
        """Route response to the appropriate handler."""
        try:
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

            # Create JSON-RPC message
            message = JSONRPCMessage.model_validate(response_data)  # type: ignore[attr-defined]

            # Check if this is a response (has id but no method)
            if hasattr(message, "id") and message.id and not hasattr(message, "method"):
                # It's a response - check if someone is waiting for it
                message_id = str(message.id)
                if message_id in self._pending_requests:
                    future = self._pending_requests.pop(message_id)
                    if not future.done():
                        future.set_result(response_data)
                        logger.debug(f"Completed pending request {message_id}")
                        return

            # Otherwise route to incoming stream
            if self._incoming_send:
                await self._incoming_send.send(message)
                logger.debug(
                    f"Routed message to incoming stream: {message.method or 'response'}"
                )

        except Exception as e:
            logger.error(f"Error routing response: {e}")
            logger.error(f"Response data: {response_data}")

    async def wait_for_response(
        self, message_id: str, timeout: float | None = None
    ) -> Dict[str, Any]:
        """Wait for a response with the given message ID."""
        future = self._pending_requests.get(message_id)
        if not future:
            future = asyncio.Future()
            self._pending_requests[message_id] = future

        try:
            if timeout:
                return await asyncio.wait_for(future, timeout=timeout)
            else:
                return await future
        finally:
            # Clean up
            self._pending_requests.pop(message_id, None)

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "session_id": self._session_id,
            "pending_requests": len(self._pending_requests),
            "connected": self._connected.is_set(),
        }
