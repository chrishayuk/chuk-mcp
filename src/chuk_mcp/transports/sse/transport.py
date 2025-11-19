# chuk_mcp/transports/sse/transport.py
"""
Universal SSE transport that handles multiple SSE server patterns:
1. Session-based pattern (like your server): /sse → /messages/?session_id=xxx
2. Direct endpoint pattern: /sse → /mcp?session_id=xxx
3. Immediate HTTP responses (200 status)
4. Async SSE message events (202 status)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

# PERFORMANCE: Use fast JSON implementation (orjson if available, stdlib json fallback)
from chuk_mcp.protocol import fast_json as json

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import SSEParameters

logger = logging.getLogger(__name__)


class SSETransport(Transport):
    """
    Universal SSE transport that handles multiple response patterns.

    Supports various SSE server implementations:
    1. Session-based servers that use /messages/ endpoints
    2. Direct endpoint servers that use /mcp endpoints
    3. Servers with immediate HTTP responses (200)
    4. Servers with async SSE responses (202)
    """

    def __init__(self, parameters: SSEParameters):
        super().__init__(parameters)
        self.base_url = parameters.url.rstrip("/")
        self.headers = parameters.headers or {}
        self.timeout = parameters.timeout
        self.bearer_token = parameters.bearer_token

        # HTTP clients
        self._stream_client: Optional[httpx.AsyncClient] = None
        self._send_client: Optional[httpx.AsyncClient] = None

        # SSE connection state
        self._message_url: Optional[str] = None
        self._session_id: Optional[str] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._outgoing_task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()

        # SSE stream context
        self._sse_response = None
        self._sse_stream_context: Optional[Any] = None

        # Message handling - support both immediate and async responses
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_lock = asyncio.Lock()

        # Memory streams for chuk_mcp message API
        self._incoming_send: Optional[MemoryObjectSendStream] = None
        self._incoming_recv: Optional[MemoryObjectReceiveStream] = None
        self._outgoing_send: Optional[MemoryObjectSendStream] = None
        self._outgoing_recv: Optional[MemoryObjectReceiveStream] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {}
        headers.update(self.headers)

        # Add bearer token if available and not already in headers
        if not any("authorization" in k.lower() for k in headers.keys()):
            # Use provided bearer token only
            if self.bearer_token:
                if self.bearer_token.startswith("Bearer "):
                    headers["Authorization"] = self.bearer_token
                else:
                    headers["Authorization"] = f"Bearer {self.bearer_token}"
                logger.debug("Added authorization header")

        return headers

    async def get_streams(
        self,
    ) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        if not self._incoming_recv or not self._outgoing_send:
            raise RuntimeError("Transport not started - use as async context manager")
        return self._incoming_recv, self._outgoing_send

    async def __aenter__(self):
        """Enter async context and set up SSE connection."""
        try:
            logger.info(f"Initializing SSE transport to {self.base_url}")

            # Create HTTP clients with proper headers
            client_headers = self._get_headers()

            self._stream_client = httpx.AsyncClient(
                headers=client_headers,
                timeout=httpx.Timeout(self.timeout),
            )

            self._send_client = httpx.AsyncClient(
                headers=client_headers,
                timeout=httpx.Timeout(self.timeout),
            )

            # Create memory streams
            from anyio import create_memory_object_stream

            self._incoming_send, self._incoming_recv = create_memory_object_stream(100)
            self._outgoing_send, self._outgoing_recv = create_memory_object_stream(100)

            # Start SSE connection
            self._sse_task = asyncio.create_task(self._handle_sse_connection())

            # Start message handler
            self._outgoing_task = asyncio.create_task(self._outgoing_message_handler())

            # Wait for SSE connection to establish
            try:
                await asyncio.wait_for(self._connected.wait(), timeout=self.timeout)
                logger.info(f"SSE connection established to {self.base_url}")
                return self

            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for SSE connection to {self.base_url}")
                await self._cleanup()
                raise RuntimeError("Timeout waiting for SSE connection")

        except Exception as e:
            logger.error(f"Error in SSE transport __aenter__: {e}")
            await self._cleanup()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
        await self._cleanup()
        return False

    async def _cleanup(self):
        """Clean up all resources."""
        # Cancel pending requests
        if hasattr(self, "_pending_requests"):
            for future in self._pending_requests.values():
                if not future.done():
                    future.cancel()
            self._pending_requests.clear()

        # Cancel tasks
        if hasattr(self, "_sse_task") and self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

        if (
            hasattr(self, "_outgoing_task")
            and self._outgoing_task
            and not self._outgoing_task.done()
        ):
            self._outgoing_task.cancel()
            try:
                await self._outgoing_task
            except asyncio.CancelledError:
                pass

        # Close SSE stream context
        if hasattr(self, "_sse_stream_context") and self._sse_stream_context:
            try:
                await self._sse_stream_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._sse_stream_context = None

        # Close streams
        if hasattr(self, "_incoming_send") and self._incoming_send:
            await self._incoming_send.aclose()
        if hasattr(self, "_outgoing_send") and self._outgoing_send:
            await self._outgoing_send.aclose()

        # Close HTTP clients
        if hasattr(self, "_stream_client") and self._stream_client:
            await self._stream_client.aclose()
            self._stream_client = None

        if hasattr(self, "_send_client") and self._send_client:
            await self._send_client.aclose()
            self._send_client = None

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        # SSE transport doesn't need version-specific handling
        pass

    async def _handle_sse_connection(self) -> None:
        """Handle the SSE connection for universal response patterns."""
        if not self._stream_client:
            logger.error("No HTTP client available for SSE connection")
            return

        try:
            headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}

            sse_endpoint = f"{self.base_url}/sse"
            logger.info(f"Connecting to SSE endpoint: {sse_endpoint}")

            self._sse_stream_context = self._stream_client.stream(
                "GET", sse_endpoint, headers=headers
            )
            assert self._sse_stream_context is not None

            # Use configured timeout for the initial connection attempt
            # This ensures we fail fast if the endpoint doesn't exist
            try:
                self._sse_response = await asyncio.wait_for(
                    self._sse_stream_context.__aenter__(),  # type: ignore[arg-type,func-returns-value]
                    timeout=min(
                        self.timeout, 15.0
                    ),  # Use configured timeout, max 15 seconds for initial connection
                )
            except asyncio.TimeoutError:
                raise RuntimeError(f"Timeout connecting to SSE endpoint {sse_endpoint}")

            assert self._sse_response is not None
            if self._sse_response.status_code != 200:
                raise RuntimeError(
                    f"SSE connection failed with status {self._sse_response.status_code}"
                )

            logger.info(
                f"SSE stream connected, status: {self._sse_response.status_code}"
            )

            # Process SSE stream
            await self._process_sse_stream()

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
            import traceback

            logger.debug(f"SSE error traceback: {traceback.format_exc()}")
        finally:
            if not self._connected.is_set():
                logger.warning("Setting connected event in SSE handler finally block")
                self._connected.set()

    async def _process_sse_stream(self):
        """Process the SSE event stream."""
        current_event = None
        buffer = ""

        assert self._sse_response is not None
        async for chunk in self._sse_response.aiter_text():
            if not chunk:
                continue

            buffer += chunk

            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.rstrip("\r")

                if not line:
                    # Empty line marks end of event
                    current_event = None
                    continue

                # Parse SSE format
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    logger.debug(f"SSE event type: {current_event}")

                elif line.startswith("data: "):
                    data = line[6:].strip()

                    # Handle different event types
                    if current_event == "endpoint":
                        await self._handle_endpoint_event(data)
                    elif current_event == "message":
                        await self._handle_message_event(data)
                    elif current_event == "keepalive":
                        logger.debug("Received keepalive")
                    else:
                        # Handle data without explicit event type
                        # Check if it's an endpoint announcement (contains /messages/ or /mcp)
                        if not self._message_url and (
                            "/messages/" in data or "/mcp" in data
                        ):
                            await self._handle_endpoint_event(data)
                        # Check if it's JSON-RPC data
                        elif data.startswith("{") and '"jsonrpc"' in data:
                            await self._handle_message_event(data)
                        else:
                            logger.debug(f"Unknown data: {data[:100]}...")

    async def _handle_endpoint_event(self, data: str) -> None:
        """Handle the endpoint event from SSE."""
        logger.info(f"Processing endpoint event: '{data}'")

        try:
            endpoint_path = data.strip()

            # Build full message URL
            if endpoint_path.startswith("/"):
                self._message_url = f"{self.base_url}{endpoint_path}"
            else:
                # Handle various formats
                if "=" in endpoint_path and not endpoint_path.startswith("http"):
                    # Assume it's query parameters
                    if "/messages/" in self.base_url:
                        self._message_url = f"{self.base_url}?{endpoint_path}"
                    else:
                        self._message_url = f"{self.base_url}/messages/?{endpoint_path}"
                else:
                    # Direct URL
                    self._message_url = endpoint_path

            # Extract session ID from various patterns
            if "session_id=" in self._message_url:
                self._session_id = self._message_url.split("session_id=")[1].split("&")[
                    0
                ]
                logger.info(f"Session ID: {self._session_id}")

            logger.info(f"Message URL set to: {self._message_url}")

            # Signal connection is ready
            self._connected.set()

        except Exception as e:
            logger.error(f"Error handling endpoint event: {e}")
            # Set a fallback message URL
            self._message_url = f"{self.base_url}/messages/"
            self._connected.set()

    async def _handle_message_event(self, data: str) -> None:
        """Handle a message event from SSE."""
        try:
            message_data = json.loads(data)
            logger.debug(
                f"Received SSE message: {message_data.get('method', 'response')} (id: {message_data.get('id')})"
            )

            # Check if this is a response to a pending request
            message_id = message_data.get("id")
            if message_id is not None:
                message_id = str(message_id)
                async with self._message_lock:
                    if message_id in self._pending_requests:
                        future = self._pending_requests.pop(message_id)
                        if not future.done():
                            future.set_result(message_data)
                            logger.debug(
                                f"Resolved pending request {message_id} via SSE"
                            )
                        return  # Don't route to incoming stream

            # If not a response to pending request, route to incoming stream
            await self._route_incoming_message(message_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            logger.debug(f"Raw data: {data[:200]}...")
        except Exception as e:
            logger.error(f"Error handling message event: {e}")

    async def _route_incoming_message(self, message_data: Dict[str, Any]) -> None:
        """Route incoming message to the incoming stream."""
        try:
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

            message = JSONRPCMessage.model_validate(message_data)  # type: ignore[attr-defined]

            if self._incoming_send:
                await self._incoming_send.send(message)
                logger.debug(f"Routed incoming message: {message.method or 'response'}")

        except Exception as e:
            logger.error(f"Error routing incoming message: {e}")
            logger.debug(f"Message data: {message_data}")

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
        """Send a message via HTTP POST with universal response handling."""
        if not self._send_client or not self._message_url:
            logger.error("Cannot send message: client or message URL not available")
            return

        try:
            # Convert message to dict
            if hasattr(message, "model_dump"):
                message_dict = message.model_dump(exclude_none=True)
            elif isinstance(message, dict):
                message_dict = message
            else:
                logger.error(f"Cannot serialize message of type {type(message)}")
                return

            headers = {"Content-Type": "application/json"}

            logger.debug(
                f"Sending to {self._message_url}: {message_dict.get('method', 'notification')} (id: {message_dict.get('id')})"
            )

            # Handle different message types
            message_id = message_dict.get("id")

            if message_id is not None:
                # Request - setup for response handling
                message_id = str(message_id)
                future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
                async with self._message_lock:
                    self._pending_requests[message_id] = future
                    logger.debug(f"Added pending request: {message_id}")

                try:
                    # Send the request
                    response = await self._send_client.post(
                        self._message_url, json=message_dict, headers=headers
                    )

                    logger.debug(f"HTTP response status: {response.status_code}")

                    if response.status_code == 200:
                        # Immediate HTTP response
                        response_data = response.json()
                        logger.debug(f"Got immediate HTTP response for {message_id}")

                        # Cancel and remove the future
                        async with self._message_lock:
                            if message_id in self._pending_requests:
                                future = self._pending_requests.pop(message_id)
                                if not future.done():
                                    future.cancel()

                        # Route response to incoming stream
                        await self._route_incoming_message(response_data)

                    elif response.status_code == 202:
                        # Async SSE response expected
                        logger.debug(
                            f"Message {message_id} accepted, waiting for SSE response"
                        )
                        try:
                            # Wait for SSE response with timeout
                            response_message = await asyncio.wait_for(
                                future, timeout=self.timeout
                            )
                            logger.debug(f"Got async SSE response for {message_id}")
                            # Route to incoming stream
                            await self._route_incoming_message(response_message)
                        except asyncio.TimeoutError:
                            logger.error(
                                f"Timeout waiting for SSE response to message {message_id}"
                            )
                            # Send timeout error
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {"code": -32000, "message": "Request timeout"},
                            }
                            await self._route_incoming_message(error_response)
                        except asyncio.CancelledError:
                            logger.debug(f"Request {message_id} was cancelled")
                    else:
                        # Unexpected status
                        logger.warning(
                            f"Unexpected response status: {response.status_code}"
                        )
                        # Try to parse response anyway
                        try:
                            response_data = response.json()
                            await self._route_incoming_message(response_data)
                        except Exception:
                            # Send error response
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": f"HTTP {response.status_code}: {response.text[:100]}",
                                },
                            }
                            await self._route_incoming_message(error_response)

                except Exception as e:
                    logger.error(f"Error sending request: {e}")
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {"code": -32603, "message": str(e)},
                    }
                    await self._route_incoming_message(error_response)
                finally:
                    # Clean up pending request
                    async with self._message_lock:
                        self._pending_requests.pop(message_id, None)

            else:
                # Notification - no response expected
                response = await self._send_client.post(
                    self._message_url, json=message_dict, headers=headers
                )
                logger.debug(f"Notification sent, status: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending message via HTTP: {e}")
            import traceback

            traceback.print_exc()

    def is_connected(self) -> bool:
        """Check if the transport is connected."""
        return self._connected.is_set() and self._message_url is not None

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"SSETransport(url={self.base_url}, status={status}, session={self._session_id})"
