# chuk_mcp/transports/http/__init__.py
"""
Streamable HTTP Transport for MCP

This implements the modern MCP specification (2025-03-26) that replaces
the deprecated SSE transport.

Key Features:
- Single HTTP endpoint for all communication
- Support for both immediate JSON and streaming SSE responses
- Proper session management with Mcp-Session-Id headers
- Automatic retry and error handling
- Memory stream-based communication compatible with existing MCP clients
- Backwards compatibility detection and fallback to SSE

The Streamable HTTP transport provides:
1. Stateless HTTP requests for simple operations
2. Optional SSE streaming for complex operations
3. Better infrastructure compatibility
4. Simplified server implementation
5. Improved error handling and reconnection
"""

from .transport import StreamableHTTPTransport
from .parameters import StreamableHTTPParameters
from .http_client import (
    http_client,
    streamable_http_client,
    create_http_parameters_from_url,
    is_streamable_http_url,
    detect_transport_type,
    try_http_with_sse_fallback,
)

__all__ = [
    "StreamableHTTPTransport",
    "StreamableHTTPParameters",
    "http_client",
    "streamable_http_client",
    "create_http_parameters_from_url",
    "is_streamable_http_url",
    "detect_transport_type",
    "try_http_with_sse_fallback",
]
