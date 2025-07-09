# chuk_mcp/transports/http/transport.py
"""
HTTP transport implementation for chuk_mcp - Updated for 2025-06-18 compliance.

This transport provides the connection layer for HTTP-based MCP servers.
Protocol messages are handled by chuk_mcp.protocol.messages.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import HTTPParameters


class HTTPTransport(Transport):
    """
    HTTP transport that provides streams for MCP communication.
    
    Follows the same pattern as StdioTransport - just provides the connection
    and streams. Protocol messages are handled by chuk_mcp.protocol.messages.
    
    Updated for 2025-06-18 compliance:
    - Requires MCP-Protocol-Version header in all requests
    - Proper OAuth 2.0 Resource Server behavior
    """

    def __init__(self, parameters: HTTPParameters):
        super().__init__(parameters)
        self.url = parameters.url
        self.headers = parameters.headers or {}
        self.timeout = parameters.timeout
        self.method = getattr(parameters, 'method', 'POST')

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Protocol version tracking (required for 2025-06-18+)
        self._negotiated_version: Optional[str] = None
        
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
        """Enter async context and set up HTTP connection."""
        # Set up HTTP client with headers
        client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        client_headers.update(self.headers)
        
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

        # Start message handler for outgoing messages
        import asyncio
        asyncio.create_task(self._outgoing_handler())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup."""
        # Close streams
        if self._incoming_send:
            await self._incoming_send.aclose()
        if self._outgoing_send:
            await self._outgoing_send.aclose()

        # Close HTTP client
        if self._client:
            await self._client.aclose()

        return False

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version (REQUIRED for 2025-06-18+)."""
        self._negotiated_version = version
        import logging
        logging.getLogger(__name__).info(f"HTTP transport protocol version set to: {version}")

    async def _outgoing_handler(self) -> None:
        """Handle outgoing messages from the write stream."""
        if not self._outgoing_recv:
            return
            
        try:
            async for message in self._outgoing_recv:
                response_message = await self._send_message(message)
                if response_message and self._incoming_send:
                    await self._incoming_send.send(response_message)
        except Exception:
            pass

    async def _send_message(self, message):
        """Send a message via HTTP and return the response message."""
        if not self._client:
            return None

        try:
            # Convert message to dict
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump(exclude_none=True)
            elif hasattr(message, 'dict'):
                message_dict = message.dict(exclude_none=True)
            else:
                message_dict = message

            # Prepare headers for this request
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # CRITICAL: Add MCP-Protocol-Version header (required for 2025-06-18+)
            if self._negotiated_version:
                request_headers["MCP-Protocol-Version"] = self._negotiated_version
            else:
                # If no version negotiated yet, this might be the initialization request
                # Some servers might accept requests without the header during initialization
                import logging
                logging.getLogger(__name__).debug("No protocol version set, sending request without MCP-Protocol-Version header")

            # Send HTTP request
            response = await self._client.request(
                self.method,
                self.url,
                json=message_dict,
                headers=request_headers
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Convert response back to JSONRPCMessage
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
            return JSONRPCMessage.model_validate(response_data)
                
        except Exception as e:
            # Return error response for failed requests
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
            import logging
            logging.getLogger(__name__).error(f"HTTP request failed: {e}")
            
            return JSONRPCMessage(
                jsonrpc="2.0",
                id=getattr(message, 'id', None),
                error={
                    "code": -32603,
                    "message": f"HTTP transport error: {str(e)}"
                }
            )

    def get_protocol_version(self) -> Optional[str]:
        """Get the current negotiated protocol version."""
        return self._negotiated_version

    def is_version_header_required(self) -> bool:
        """Check if MCP-Protocol-Version header is required."""
        # Header is required for 2025-06-18+ after initial negotiation
        if not self._negotiated_version:
            return False
            
        try:
            # Parse version to check if >= 2025-06-18
            parts = self._negotiated_version.split('-')
            if len(parts) != 3:
                return False
                
            year, month, day = map(int, parts)
            
            # 2025-06-18 and later require the header
            if year > 2025:
                return True
            elif year == 2025 and month > 6:
                return True
            elif year == 2025 and month == 6 and day >= 18:
                return True
                
            return False
        except (ValueError, TypeError, IndexError):
            return False