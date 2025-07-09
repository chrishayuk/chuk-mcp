# chuk_mcp/transports/http/__init__.py
"""
HTTP transport implementation for chuk_mcp.

This transport provides HTTP-based communication with MCP servers,
following the same patterns as stdio and SSE transports.

Key Features:
- Standard HTTP/HTTPS communication
- Bearer token authentication support
- Protocol version compliance (2025-06-18+)
- Custom headers and timeouts
- Proper resource cleanup

Usage:
    from chuk_mcp.transports.http import HTTPTransport, HTTPParameters, http_client
    
    # Using the transport directly
    params = HTTPParameters(url="https://api.example.com/mcp")
    transport = HTTPTransport(params)
    
    # Using the context manager
    async with http_client(params) as (read_stream, write_stream):
        # Send/receive messages
        pass
"""

from .transport import HTTPTransport
from .parameters import HTTPParameters
from .http_client import http_client

__all__ = ["HTTPTransport", "HTTPParameters", "http_client"]