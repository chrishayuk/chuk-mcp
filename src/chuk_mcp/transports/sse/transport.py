# chuk_mcp/transports/sse/transport.py
"""
SSE (Server-Sent Events) transport implementation for chuk_mcp.

This transport provides the connection layer for SSE-based MCP servers.
Protocol messages are handled by chuk_mcp.protocol.messages.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, Optional, Tuple

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import SSEParameters


class SSETransport(Transport):
    """
    SSE transport that provides streams for MCP communication.
    
    The actual MCP protocol messages are handled by chuk_mcp.protocol.messages.
    This transport just manages the SSE connection and message routing.
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
        
        # Message handling
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
        # Set up HTTP client with headers
        client_headers = {}
        client_headers.update(self.headers)  # self.headers is guaranteed to be dict now
        
        # Auto-detect bearer token from environment if not provided
        if not any("authorization" in k.lower() for k in client_headers.keys()):
            bearer_token = os.getenv("MCP_BEARER_TOKEN")
            if bearer_token:
                if bearer_token.startswith("Bearer "):
                    client_headers["Authorization"] = bearer_token
                else:
                    client_headers["Authorization"] = f"Bearer {bearer_token}"

        self._client = httpx.AsyncClient(
            headers=client_headers,
            timeout=self.timeout,
        )

        # Create memory streams for message routing
        from anyio import create_memory_object_stream
        self._incoming_send, self._incoming_recv = create_memory_object_stream(100)
        self._outgoing_send, self._outgoing_recv = create_memory_object_stream(100)

        # Start SSE connection
        self._sse_task = asyncio.create_task(self._sse_connection_handler())
        
        # Start message handler for outgoing messages
        self._outgoing_task = asyncio.create_task(self._outgoing_message_handler())
        
        # Wait for SSE connection to establish
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=self.timeout)
            return self
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout waiting for SSE connection")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
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

        # Clear state
        self._message_url = None
        self._session_id = None
        self._connected.clear()
        self._pending_requests.clear()

        return False

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        # SSE transport doesn't need special version handling
        pass

    async def _sse_connection_handler(self) -> None:
        """Handle the SSE connection and message routing."""
        if not self._client:
            return

        try:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            
            async with self._client.stream(
                "GET", f"{self.base_url}/sse", headers=headers
            ) as response:
                response.raise_for_status()
                
                event_type = None
                async for line in response.aiter_lines():
                    if not line:
                        continue
                        
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                        
                    elif line.startswith("data: ") and event_type:
                        data = line[6:].strip()
                        
                        if event_type == "endpoint":
                            # Got the endpoint URL for messages (should be /mcp?session_id=...)
                            if not data.startswith("/mcp"):
                                # Handle legacy format
                                if "/messages?" in data:
                                    # Convert legacy /messages?session_id=... to /mcp?session_id=...
                                    session_part = data.split("session_id=")[1] if "session_id=" in data else ""
                                    data = f"/mcp?session_id={session_part}"
                                else:
                                    # Default fallback
                                    data = "/mcp"
                            
                            self._message_url = f"{self.base_url}{data}"
                            
                            # Extract session_id if present
                            if "session_id=" in data:
                                self._session_id = data.split("session_id=")[1].split("&")[0]
                            
                            # Set connected event
                            self._connected.set()
                            
                        elif event_type == "message":
                            # Incoming JSON-RPC message
                            try:
                                message_data = json.loads(data)
                                await self._handle_incoming_message(message_data)
                            except json.JSONDecodeError:
                                pass
                                
        except asyncio.CancelledError:
            pass
        except Exception:
            # Set connected even on error to prevent hanging
            if not self._connected.is_set():
                self._connected.set()
          
    async def _handle_incoming_message(self, message_data: Dict[str, Any]) -> None:
        """Route incoming message to the appropriate handler."""
        # Convert to JSONRPCMessage and send to incoming stream
        try:
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
            message = JSONRPCMessage.model_validate(message_data)
            
            if self._incoming_send:
                await self._incoming_send.send(message)
                
        except Exception:
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
        except Exception:
            pass

    async def _send_message_via_http(self, message) -> None:
        """Send a message via HTTP POST to the message endpoint."""
        if not self._client or not self._message_url:
            return

        try:
            # Convert message to dict for JSON serialization
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump(exclude_none=True)
            elif hasattr(message, 'dict'):
                message_dict = message.dict(exclude_none=True)
            else:
                message_dict = message

            headers = {"Content-Type": "application/json"}
            
            # Send the message
            response = await self._client.post(
                self._message_url,
                json=message_dict,
                headers=headers
            )
            
            # For SSE, we expect 202 Accepted (async response via SSE)
            # or immediate response for some message types
            if response.status_code not in (200, 202):
                response.raise_for_status()
                
        except Exception:
            # Silently fail - let the protocol layer handle timeouts
            pass