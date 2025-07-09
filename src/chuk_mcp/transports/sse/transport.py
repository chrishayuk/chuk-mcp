# chuk_mcp/transports/sse/transport.py - CORRECTLY FIXED VERSION
"""
Universal SSE transport that handles both SSE response patterns:
1. Immediate HTTP responses (like your example server)
2. Async SSE message events (like the queue-based server)

FIXED: Properly handles async responses on the same SSE connection
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import SSEParameters

logger = logging.getLogger(__name__)


class SSETransport(Transport):
    """
    Universal SSE transport that handles multiple response patterns.
    
    1. Connects to /sse for SSE stream
    2. Waits for 'endpoint' event to get message URL  
    3. Sends MCP messages via HTTP POST to message URL
    4. Handles responses via either:
       - Immediate HTTP response (200 status)
       - Async SSE message events (202 status + SSE on SAME connection)
    """

    def __init__(self, parameters: SSEParameters):
        super().__init__(parameters)
        self.base_url = parameters.url.rstrip("/")
        self.headers = parameters.headers or {}
        self.timeout = parameters.timeout

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # SSE connection state
        self._message_url: Optional[str] = None
        self._session_id: Optional[str] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._outgoing_task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()
        
        # Message handling - support both immediate and async responses
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_lock = asyncio.Lock()
        
        # Memory streams for chuk_mcp message API
        self._incoming_send: Optional[MemoryObjectSendStream] = None
        self._incoming_recv: Optional[MemoryObjectReceiveStream] = None
        self._outgoing_send: Optional[MemoryObjectSendStream] = None
        self._outgoing_recv: Optional[MemoryObjectReceiveStream] = None

    async def get_streams(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        if not self._incoming_recv or not self._outgoing_send:
            raise RuntimeError("Transport not started - use as async context manager")
        return self._incoming_recv, self._outgoing_send

    async def __aenter__(self):
        """Enter async context and set up SSE connection."""
        # Set up HTTP client with proper headers
        client_headers = {}
        client_headers.update(self.headers)
        
        # Auto-detect bearer token from environment if not provided
        if not any("authorization" in k.lower() for k in client_headers.keys()):
            bearer_token = os.getenv("MCP_BEARER_TOKEN")
            if bearer_token:
                if bearer_token.startswith("Bearer "):
                    client_headers["Authorization"] = bearer_token
                else:
                    client_headers["Authorization"] = f"Bearer {bearer_token}"
                logger.info("Using bearer token from MCP_BEARER_TOKEN environment variable")

        self._client = httpx.AsyncClient(
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
            raise RuntimeError("Timeout waiting for SSE connection")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        # Cancel tasks
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

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

        # Close HTTP client
        if self._client:
            await self._client.aclose()
            self._client = None

        return False

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        pass

    async def _handle_sse_connection(self) -> None:
        """Handle the SSE connection for universal response patterns."""
        if not self._client:
            logger.error("No HTTP client available for SSE connection")
            return

        try:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            
            logger.info(f"Connecting to SSE endpoint: {self.base_url}/sse")
            
            async with self._client.stream(
                "GET", f"{self.base_url}/sse", headers=headers
            ) as response:
                response.raise_for_status()
                logger.info(f"SSE stream connected, status: {response.status_code}")
                
                # Parse SSE events - handle both event: and data: patterns
                current_event = None
                buffer = ""
                
                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    
                    buffer += chunk
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.rstrip('\r')  # Remove \r if present
                        
                        logger.debug(f"SSE line: '{line}'")
                        
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
                            logger.debug(f"SSE data for event '{current_event}': {data}")
                            
                            if current_event == "endpoint":
                                await self._handle_endpoint_event(data)
                                
                            elif current_event == "message":
                                await self._handle_message_event(data)
                                
                            elif current_event == "keepalive":
                                logger.debug("Received keepalive")
                            
                            else:
                                # Handle JSON data without explicit event type
                                # Some servers send responses without event: lines
                                if data.startswith('{') and '"jsonrpc"' in data:
                                    logger.info(f"Handling JSON-RPC message without event type: {data[:100]}...")
                                    await self._handle_message_event(data)
                                else:
                                    logger.debug(f"Unknown data format: {data}")
                        
                        elif line.startswith("id: "):
                            # SSE event ID - we can ignore this for now
                            event_id = line[4:].strip()
                            logger.debug(f"SSE event ID: {event_id}")
                        
                        elif line.startswith(": "):
                            # SSE comment - ignore
                            logger.debug(f"SSE comment: {line}")
                        
                        else:
                            logger.debug(f"Unknown SSE line format: {line}")
                        
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

    async def _handle_endpoint_event(self, data: str) -> None:
        """Handle the endpoint event from SSE."""
        logger.info(f"Processing endpoint event: '{data}'")
        
        try:
            # The server sends the endpoint path like "/mcp?session_id=abc123"
            endpoint_path = data.strip()
            
            if endpoint_path.startswith('/'):
                self._message_url = f"{self.base_url}{endpoint_path}"
            else:
                # Fallback for other formats
                self._message_url = f"{self.base_url}/mcp?{endpoint_path}" if '=' in endpoint_path else f"{self.base_url}/mcp"
            
            # Extract session ID
            if 'session_id=' in endpoint_path:
                self._session_id = endpoint_path.split('session_id=')[1].split('&')[0]
                logger.info(f"Session ID: {self._session_id}")
            
            logger.info(f"Message URL set to: {self._message_url}")
            
            # Signal connection is ready
            self._connected.set()
            
        except Exception as e:
            logger.error(f"Error handling endpoint event: {e}")

    async def _handle_message_event(self, data: str) -> None:
        """Handle a message event from SSE."""
        logger.debug(f"Processing message event: {data}")
        
        try:
            message_data = json.loads(data)
            logger.info(f"Received SSE message: {message_data.get('method', 'response')} (id: {message_data.get('id')})")
            
            # Handle response for pending requests FIRST
            message_id = message_data.get("id")
            if message_id:
                async with self._message_lock:
                    if message_id in self._pending_requests:
                        future = self._pending_requests.pop(message_id)
                        if not future.done():
                            future.set_result(message_data)
                            logger.info(f"✅ Completed pending request {message_id} via SSE")
                        return  # Don't route to incoming stream - this was a response
            
            # If not a response to pending request, route to incoming stream
            # This handles server-initiated messages (notifications, requests)
            await self._handle_incoming_message(message_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            logger.error(f"Raw data: {data}")
        except Exception as e:
            logger.error(f"Error handling message event: {e}")
            import traceback
            logger.debug(f"Message handling traceback: {traceback.format_exc()}")

    async def _handle_incoming_message(self, message_data: Dict[str, Any]) -> None:
        """Route incoming message to the appropriate handler."""
        try:
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
            message = JSONRPCMessage.model_validate(message_data)
            
            if self._incoming_send:
                await self._incoming_send.send(message)
                logger.debug(f"Routed incoming message: {message.method or 'response'}")
                
        except Exception as e:
            logger.error(f"Error routing incoming message: {e}")
            logger.error(f"Message data: {message_data}")

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
        if not self._client or not self._message_url:
            logger.error("Cannot send message: client or message URL not available")
            return

        try:
            # Convert message to dict
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump(exclude_none=True)
            elif isinstance(message, dict):
                message_dict = message
            else:
                logger.error(f"Cannot serialize message of type {type(message)}")
                return

            headers = {"Content-Type": "application/json"}
            
            logger.info(f"Sending message to {self._message_url}: {message_dict.get('method')} (id: {message_dict.get('id')})")
            
            # Handle different message types
            message_id = message_dict.get('id')
            
            if message_id:
                # Request - setup for response handling
                future = asyncio.Future()
                async with self._message_lock:
                    self._pending_requests[message_id] = future
                    logger.debug(f"Added pending request: {message_id}")

                try:
                    # Send the request
                    response = await self._client.post(
                        self._message_url,
                        json=message_dict,
                        headers=headers
                    )
                    
                    logger.debug(f"Message sent, status: {response.status_code}")
                    
                    if response.status_code == 200:
                        # IMMEDIATE HTTP RESPONSE (like your example server)
                        response_data = response.json()
                        logger.info(f"Got immediate HTTP response for {message_id}")
                        # Cancel the future since we got immediate response
                        async with self._message_lock:
                            if message_id in self._pending_requests:
                                future = self._pending_requests.pop(message_id)
                                if not future.done():
                                    future.cancel()
                        # Send response back via incoming stream
                        await self._handle_incoming_message(response_data)
                        
                    elif response.status_code == 202:
                        # ASYNC SSE RESPONSE - wait for response on existing SSE connection
                        logger.info(f"Server accepted message {message_id} - waiting for response via SSE")
                        try:
                            # Wait for SSE response with timeout
                            response_message = await asyncio.wait_for(future, timeout=self.timeout)
                            logger.info(f"✅ Got async SSE response for {message_id}")
                            # Route the response to the incoming stream for protocol handling
                            await self._handle_incoming_message(response_message)
                        except asyncio.TimeoutError:
                            logger.error(f"❌ Timeout waiting for SSE response to message {message_id}")
                            # Clean up the pending request
                            async with self._message_lock:
                                self._pending_requests.pop(message_id, None)
                            raise
                        except asyncio.CancelledError:
                            logger.debug(f"Request {message_id} was cancelled")
                            
                    else:
                        logger.warning(f"Unexpected response status: {response.status_code}")
                        # Clean up pending request
                        async with self._message_lock:
                            self._pending_requests.pop(message_id, None)
                        # Try to parse as JSON anyway
                        try:
                            response_data = response.json()
                            await self._handle_incoming_message(response_data)
                        except:
                            logger.error(f"Could not parse response for status {response.status_code}")
                        
                except Exception as e:
                    # Clean up pending request on error
                    async with self._message_lock:
                        self._pending_requests.pop(message_id, None)
                    raise
                    
            else:
                # Notification - no response expected
                response = await self._client.post(
                    self._message_url,
                    json=message_dict,
                    headers=headers
                )
                logger.debug(f"Notification sent, status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending message via HTTP: {e}")
            import traceback
            traceback.print_exc()