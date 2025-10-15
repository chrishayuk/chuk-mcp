# chuk_mcp/transports/sse/__init__.py
"""
SSE (Server-Sent Events) Transport for MCP

⚠️ DEPRECATION NOTICE:
The SSE transport has been deprecated as of MCP specification version 2025-03-26.
Please consider migrating to the Streamable HTTP transport when available.

This implementation maintains backwards compatibility with existing SSE-based MCP servers
while providing the functionality needed for current deployments.

Key Features:
- Universal SSE response handling (immediate HTTP + async SSE)
- Automatic session management
- Bearer token authentication support
- Proper error handling and cleanup
- Memory stream-based communication compatible with existing MCP clients
"""

from .transport import SSETransport
from .parameters import SSEParameters
from .sse_client import (
    sse_client,
    try_sse_with_fallback,
    create_sse_parameters_from_url,
    is_sse_url,
)

__all__ = [
    "SSETransport",
    "SSEParameters",
    "sse_client",
    "try_sse_with_fallback",
    "create_sse_parameters_from_url",
    "is_sse_url",
]
