# chuk_mcp/transports/http/transport.py
"""Streamable HTTP transport implementation — Rust-backed via chuk_mcp_rs.

Kept as an import path for backward compatibility with downstream consumers
(e.g. chuk-tool-processor) that import
``chuk_mcp.transports.http.transport.StreamableHTTPTransport``.
"""

from ..._rust import StreamableHTTPParameters, StreamableHTTPTransport

__all__ = ["StreamableHTTPTransport", "StreamableHTTPParameters"]
