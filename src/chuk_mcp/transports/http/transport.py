# chuk_mcp/transports/http/transport.py
"""
Streamable HTTP transport implementation for MCP.

This implements the new MCP specification (2025-03-26) that replaces SSE transport.
Supports both simple HTTP responses and optional SSE streaming upgrades.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple, Set

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import StreamableHTTPParameters

logger = logging.getLogger(__name__)


class StreamableHTTPTransport(Transport):
    """
    Streamable HTTP transport for MCP (spec 2025-03-26).
    
    This transport:
    1. Uses a single HTTP endpoint for all communication
    2. Sends JSON-RPC messages via HTTP POST
    3. Handles both immediate JSON responses and streaming SSE responses
    4. Supports session management and reconnection
    5. Provides the modern replacement for deprecated SSE transport
    """

    def __init__(self, parameters: StreamableHTTPParameters):
        super().__init__(parameters)
        self.endpoint_url = parameters.url
        self.headers = parameters.headers or {}
        self.timeout = parameters.timeout
        self.enable_streaming = parameters.enable_streaming
        max_concurrent_requests = parameters.max_concurrent_requests

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # Session management
        self._session_id: Optional[str] = parameters.session_id
        self._connected = asyncio.Event()
        
        # Message handling
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_lock = asyncio.Lock()
        
        # Streaming SSE connection (optional)
        self._sse_task: Optional[asyncio.Task] = None
        self._streaming_response: Optional[httpx.Response] = None
        
        # Request handling
        self._outgoing_task: Optional[asyncio.Task] = None
        self._request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Memory streams for chuk_mcp message API
        self._incoming_send: Optional[MemoryObjectSendStream] = None
        self._incoming_recv: Optional[MemoryObjectReceiveStream] = None
        self._outgoing_send: Optional[MemoryObjectSendStream] = None
        self._outgoing_recv: Optional[MemoryObjectReceiveStream] = None

        # Connection health monitoring
        self._last_successful_request: Optional[float] = None
        self._consecutive_failures = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 30.0

    async def get_streams(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        if not self._incoming_recv or not self._outgoing_send:
            raise RuntimeError("Transport not started - use as async context manager")
        return self._incoming_recv, self._outgoing_send

    async def __aenter__(self):
        """Enter async context and set up HTTP transport."""
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

        # Start message handler
        self._outgoing_task = asyncio.create_task(self._outgoing_message_handler())
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        # Signal connection is ready (no handshake needed for HTTP)
        self._connected.set()
        logger.info(f"Streamable HTTP transport ready: {self.endpoint_url}")
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
        # Cancel health monitoring
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

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

        # Close streaming response if open
        if self._streaming_response:
            await self._streaming_response.aclose()
            self._streaming_response = None

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

    async def _health_monitor(self):
        """Monitor connection health and attempt recovery if needed."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Check if we've had recent successful requests
                now = time.time()
                if (self._last_successful_request and 
                    now - self._last_successful_request > self._health_check_interval * 2):
                    
                    logger.debug("Performing health check...")
                    await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")

    async def _perform_health_check(self):
        """Perform a health check ping."""
        try:
            if not self._client:
                return
                
            # Send a simple ping
            ping_message = {
                "jsonrpc": "2.0",
                "id": f"health-check-{time.time()}",
                "method": "ping"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id
            
            response = await asyncio.wait_for(
                self._client.post(
                    self.endpoint_url,
                    json=ping_message,
                    headers=headers
                ),
                timeout=10.0
            )
            
            if response.status_code == 200:
                self._mark_success()
                logger.debug("Health check passed")
            else:
                self._mark_failure()
                logger.warning(f"Health check failed: HTTP {response.status_code}")
                
        except Exception as e:
            self._mark_failure()
            logger.warning(f"Health check failed: {e}")
            
            # Attempt reconnection if too many failures
            if self._consecutive_failures >= 3:
                logger.info("Attempting reconnection due to health check failures")
                await self.reconnect()

    def _mark_success(self):
        """Mark a successful request."""
        self._last_successful_request = time.time()
        self._consecutive_failures = 0

    def _mark_failure(self):
        """Mark a failed request."""
        self._consecutive_failures += 1

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
        if not self._client:
            logger.error("Cannot send message: HTTP client not available")
            return

        # Use semaphore to limit concurrent requests
        async with self._request_semaphore:
            await self._send_message_internal(message)

    async def _send_message_internal(self, message) -> None:
        """Internal message sending with proper error handling."""
        try:
            # Convert message to dict
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump(exclude_none=True)
            elif isinstance(message, dict):
                message_dict = message
            else:
                logger.error(f"Cannot serialize message of type {type(message)}")
                return

            # Prepare headers for streamable HTTP
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            # Add session ID if available
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id

            logger.info(f"Sending HTTP message: {message_dict.get('method')} (id: {message_dict.get('id')})")
            
            # Handle different message types
            message_id = message_dict.get('id')
            
            if message_id:
                # Request - setup for response handling
                future = asyncio.Future()
                async with self._message_lock:
                    self._pending_requests[message_id] = future
                    logger.debug(f"Added pending request: {message_id}")

                try:
                    # Use asyncio.wait_for with proper timeout handling
                    timeout_duration = self.timeout * 0.9  # Slightly less than client timeout
                    
                    response_task = self._client.post(
                        self.endpoint_url,
                        json=message_dict,
                        headers=headers
                    )
                    
                    response = await asyncio.wait_for(response_task, timeout=timeout_duration)
                    
                    logger.debug(f"HTTP response status: {response.status_code}")
                    logger.debug(f"HTTP response headers: {dict(response.headers)}")
                    
                    # Handle error status codes
                    if response.status_code >= 400:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"Server error for {message_id}: {error_msg}")
                        
                        # Complete the future with error
                        async with self._message_lock:
                            if message_id in self._pending_requests:
                                future = self._pending_requests.pop(message_id)
                                if not future.done():
                                    future.set_exception(Exception(error_msg))
                        self._mark_failure()
                        return
                    
                    # Extract session ID from response if provided
                    if "mcp-session-id" in response.headers:
                        self._session_id = response.headers["mcp-session-id"]
                        logger.debug(f"Updated session ID: {self._session_id}")
                    
                    content_type = response.headers.get("content-type", "")
                    
                    if "application/json" in content_type:
                        # IMMEDIATE JSON RESPONSE - FIXED: Complete future instead of canceling
                        response_data = response.json()
                        logger.debug(f"Got immediate JSON response for {message_id}")
                        
                        # Complete the future with the response data
                        async with self._message_lock:
                            if message_id in self._pending_requests:
                                future = self._pending_requests.pop(message_id)
                                if not future.done():
                                    # Don't cancel - set the result so protocol layer gets response
                                    future.set_result(response_data)
                                    logger.debug(f"✅ Completed pending request {message_id} with immediate response")
                        
                        # Also route response to incoming stream for notifications/events
                        await self._handle_incoming_message(response_data)
                        
                    elif "text/event-stream" in content_type and self.enable_streaming:
                        # STREAMING SSE RESPONSE
                        logger.info(f"🌊 Got streaming SSE response for {message_id}")
                        logger.debug(f"Response headers: {dict(response.headers)}")
                        
                        # Start SSE processing for this response
                        self._streaming_response = response
                        if not self._sse_task or self._sse_task.done():
                            self._sse_task = asyncio.create_task(
                                self._handle_sse_stream(response, message_id, future)
                            )
                        else:
                            # Handle response in existing SSE task
                            await self._handle_sse_response(response, message_id, future)
                    
                    else:
                        logger.warning(f"Unexpected content type: {content_type}")
                        # Try to parse as JSON anyway
                        try:
                            response_data = response.json()
                            
                            # Complete the future
                            async with self._message_lock:
                                if message_id in self._pending_requests:
                                    future = self._pending_requests.pop(message_id)
                                    if not future.done():
                                        future.set_result(response_data)
                            
                            await self._handle_incoming_message(response_data)
                            
                        except Exception as parse_error:
                            logger.error(f"Could not parse response for {message_id}: {parse_error}")
                            # Complete future with error
                            async with self._message_lock:
                                if message_id in self._pending_requests:
                                    future = self._pending_requests.pop(message_id)
                                    if not future.done():
                                        future.set_exception(parse_error)
                            self._mark_failure()
                            return
                    
                    # Mark success
                    self._mark_success()
                        
                except asyncio.TimeoutError:
                    # Handle timeout specifically
                    logger.error(f"Timeout waiting for response to {message_id} after {timeout_duration}s")
                    async with self._message_lock:
                        if message_id in self._pending_requests:
                            future = self._pending_requests.pop(message_id)
                            if not future.done():
                                future.set_exception(asyncio.TimeoutError(f"Request {message_id} timed out"))
                    self._mark_failure()
                    
                except Exception as e:
                    # Clean up pending request on error
                    async with self._message_lock:
                        if message_id in self._pending_requests:
                            future = self._pending_requests.pop(message_id)
                            if not future.done():
                                future.set_exception(e)
                    self._mark_failure()
                    logger.error(f"Error sending message {message_id}: {e}")
                    raise
                    
            else:
                # Notification - no response expected
                try:
                    response = await asyncio.wait_for(
                        self._client.post(
                            self.endpoint_url,
                            json=message_dict,
                            headers=headers
                        ),
                        timeout=self.timeout * 0.5  # Shorter timeout for notifications
                    )
                    logger.debug(f"Notification sent, status: {response.status_code}")
                    
                    if response.status_code < 400:
                        self._mark_success()
                    else:
                        self._mark_failure()
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Notification timeout for {message_dict.get('method')}")
                    self._mark_failure()
                    # Don't raise for notifications, just log
                    
        except Exception as e:
            self._mark_failure()
            logger.error(f"Error in HTTP message sending: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _handle_sse_stream(self, response: httpx.Response, initial_message_id: str, initial_future: asyncio.Future) -> None:
        """Handle SSE streaming response from server."""
        try:
            logger.info(f"🔄 Starting SSE stream processing for message {initial_message_id}")
            
            buffer = ""
            current_event = None
            message_parts = {}  # Track multi-part messages
            
            # Set timeout for SSE stream
            stream_timeout = self.timeout * 2  # Allow longer for streams
            start_time = asyncio.get_event_loop().time()
            
            # Process stream with timeout - FIXED: Proper async iteration with timeout
            chunk_count = 0
            async for chunk in response.aiter_text(chunk_size=1024):
                # Check for timeout
                if asyncio.get_event_loop().time() - start_time > stream_timeout:
                    logger.error(f"SSE stream timed out after {stream_timeout}s for message {initial_message_id}")
                    if not initial_future.done():
                        initial_future.set_exception(asyncio.TimeoutError("SSE stream timed out"))
                    return
                
                chunk_count += 1
                logger.debug(f"📦 SSE chunk {chunk_count} ({len(chunk)} chars): {chunk[:100]}...")
                
                if not chunk:
                    continue
                    
                buffer += chunk
                
                # Process complete lines
                lines_processed = 0
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.rstrip('\r')
                    lines_processed += 1
                    
                    logger.debug(f"📝 SSE line {lines_processed}: '{line}'")
                    
                    if not line:
                        # Empty line marks end of event - process if we have data
                        if current_event and 'data' in message_parts:
                            logger.info(f"🎯 Processing complete SSE event: {current_event}")
                            await self._process_sse_event(current_event, message_parts, initial_message_id, initial_future)
                        
                        # Reset for next event
                        current_event = None
                        message_parts = {}
                        continue
                        
                    # Parse SSE format
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                        logger.info(f"📋 SSE event type: {current_event}")
                        
                    elif line.startswith("data: "):
                        data = line[6:]  # Don't strip - preserve formatting
                        logger.debug(f"📄 SSE data: {data[:200]}...")
                        
                        # Accumulate data parts
                        if 'data' not in message_parts:
                            message_parts['data'] = []
                        message_parts['data'].append(data)
                        
                    elif line.startswith("id: "):
                        # SSE event ID for resumption
                        message_parts['id'] = line[4:].strip()
                        logger.debug(f"🆔 SSE event ID: {message_parts['id']}")
                        
                    elif line.startswith("retry: "):
                        # Retry interval
                        try:
                            message_parts['retry'] = int(line[7:].strip())
                            logger.debug(f"🔄 SSE retry: {message_parts['retry']}")
                        except ValueError:
                            pass
            
            logger.info(f"📊 SSE stream ended for {initial_message_id}. Processed {chunk_count} chunks.")
            
            # Process any remaining buffered event
            if current_event and 'data' in message_parts:
                logger.info(f"🎯 Processing final SSE event: {current_event}")
                await self._process_sse_event(current_event, message_parts, initial_message_id, initial_future)
                
        except asyncio.TimeoutError:
            logger.error(f"SSE stream timed out for message {initial_message_id}")
            if not initial_future.done():
                initial_future.set_exception(asyncio.TimeoutError("SSE stream timed out"))
        except asyncio.CancelledError:
            logger.debug(f"SSE stream cancelled for message {initial_message_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for message {initial_message_id}: {e}")
            if not initial_future.done():
                initial_future.set_exception(e)
        finally:
            # Ensure response is closed
            if not response.is_closed:
                await response.aclose()
            
            # Complete any remaining pending request
            if not initial_future.done():
                initial_future.cancel()

    async def _process_sse_event(self, event_type: str, message_parts: dict, initial_message_id: str, initial_future: asyncio.Future):
        """Process a complete SSE event."""
        try:
            # Reconstruct data from parts
            data_parts = message_parts.get('data', [])
            if not data_parts:
                logger.warning(f"⚠️ SSE event '{event_type}' has no data parts")
                return
                
            # Join data parts with newlines (SSE spec)
            full_data = '\n'.join(data_parts)
            
            logger.info(f"🎯 Processing SSE event '{event_type}' with {len(full_data)} chars of data")
            logger.debug(f"📄 Event data: {full_data[:300]}...")
            
            # Handle different event types
            if event_type in ['message', 'response', 'completion', None]:  # FIXED: Added 'completion'
                # Standard JSON-RPC message or completion event
                if full_data.strip().startswith('{') and '"jsonrpc"' in full_data:
                    logger.info(f"✅ Processing JSON-RPC message from SSE event '{event_type}'")
                    await self._handle_sse_message(full_data.strip())
                elif event_type == 'completion':
                    # Handle completion event - could be final result
                    logger.info(f"🏁 Completion event received for {initial_message_id}: {full_data[:100]}...")
                    
                    # Parse the completion data
                    try:
                        completion_data = json.loads(full_data.strip())
                        logger.info("📊 Parsing completion event as JSON")
                        
                        # Check if it's already a JSON-RPC response
                        if 'jsonrpc' in completion_data and 'id' in completion_data:
                            # It's already a proper JSON-RPC response
                            await self._handle_sse_message(full_data.strip())
                        else:
                            # Convert completion event to JSON-RPC response
                            logger.info("🔄 Converting completion event to JSON-RPC response")
                            completion_response = {
                                "jsonrpc": "2.0",
                                "id": initial_message_id,
                                "result": {
                                    "content": [{
                                        "type": "text",
                                        "text": f"Completion: {completion_data.get('type', 'unknown')} at {completion_data.get('timestamp', 'unknown time')}"
                                    }],
                                    "isError": False
                                }
                            }
                            await self._handle_sse_message(json.dumps(completion_response))
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse completion event as JSON: {e}")
                        # Create a simple text response with the message ID
                        completion_response = {
                            "jsonrpc": "2.0",
                            "id": initial_message_id,  # FIXED: Use the actual message ID
                            "result": {
                                "content": [{
                                    "type": "text",
                                    "text": f"Tool completed: {full_data.strip()}"
                                }],
                                "isError": False
                            }
                        }
                        await self._handle_sse_message(json.dumps(completion_response))
                else:
                    logger.warning(f"⚠️ Event '{event_type}' data doesn't look like JSON: {full_data[:100]}...")
            
            elif event_type == 'error':
                # Server sent an error event
                error_msg = full_data.strip()
                logger.error(f"❌ Server error via SSE: {error_msg}")
                
                # Complete initial future with error if it matches
                if not initial_future.done():
                    initial_future.set_exception(Exception(f"Server error: {error_msg}"))
            
            elif event_type == 'close' or event_type == 'end':
                # Stream is ending
                logger.info(f"🔚 SSE stream ending for {initial_message_id}")
                
            elif event_type in ['progress', 'status', 'update']:
                # Progress/status events - handle but don't complete the future
                logger.info(f"📈 Progress event for {initial_message_id}: {full_data[:100]}...")
                if full_data.strip().startswith('{'):
                    try:
                        await self._handle_sse_message(full_data.strip())
                    except json.JSONDecodeError:
                        pass
                
            else:
                # Unknown event type - try to process as JSON anyway
                logger.info(f"❓ Unknown SSE event type '{event_type}', attempting JSON parse")
                if full_data.strip().startswith('{'):
                    try:
                        logger.info("📊 Parsing unknown event as JSON")
                        await self._handle_sse_message(full_data.strip())
                    except json.JSONDecodeError:
                        logger.warning(f"❌ Could not parse unknown event type '{event_type}' as JSON: {full_data[:100]}...")
                else:
                    logger.warning(f"⚠️ Unknown event '{event_type}' doesn't look like JSON: {full_data[:100]}...")
                    
        except Exception as e:
            logger.error(f"💥 Error processing SSE event '{event_type}': {e}")
            logger.error(f"Event data: {full_data[:200]}...")
            import traceback
            traceback.print_exc()

    async def _handle_sse_response(self, response: httpx.Response, message_id: str, future: asyncio.Future) -> None:
        """Handle a single SSE response."""
        # This would be used if we need to handle multiple concurrent SSE streams
        # For now, we use the main SSE stream handler
        pass

    async def _handle_sse_message(self, data: str) -> None:
        """Handle a JSON-RPC message from SSE stream."""
        try:
            message_data = json.loads(data)
            logger.info(f"📨 Received SSE message: {message_data.get('method', 'response')} (id: {message_data.get('id')})")
            
            # Handle response for pending requests
            message_id = message_data.get("id")
            if message_id:
                async with self._message_lock:
                    if message_id in self._pending_requests:
                        future = self._pending_requests.pop(message_id)
                        if not future.done():
                            future.set_result(message_data)
                            logger.info(f"✅ Completed pending request {message_id} via SSE")
                            return
                    else:
                        logger.warning(f"⚠️ No pending request found for message ID {message_id}")
            
            # Route to incoming stream for protocol layer
            await self._handle_incoming_message(message_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse SSE JSON: {e}")
            logger.error(f"Raw data: {data[:200]}...")
        except Exception as e:
            logger.error(f"💥 Error handling SSE message: {e}")
            import traceback
            traceback.print_exc()

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

    async def reconnect(self) -> bool:
        """Attempt to reconnect to the server."""
        try:
            logger.info(f"Attempting to reconnect to {self.endpoint_url}")
            
            # Close existing client
            if self._client:
                await self._client.aclose()
            
            # Create new client
            client_headers = {}
            client_headers.update(self.headers)
            
            self._client = httpx.AsyncClient(
                headers=client_headers,
                timeout=httpx.Timeout(self.timeout),
            )
            
            # Test connection
            await self._perform_health_check()
            
            if self._consecutive_failures == 0:
                logger.info("Reconnection successful")
                return True
            else:
                logger.error("Reconnection failed health check")
                return False
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "session_id": self._session_id,
            "last_successful_request": self._last_successful_request,
            "consecutive_failures": self._consecutive_failures,
            "pending_requests": len(self._pending_requests),
            "connected": self._connected.is_set()
        }