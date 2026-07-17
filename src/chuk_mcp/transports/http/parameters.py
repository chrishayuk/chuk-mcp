# chuk_mcp/transports/http/parameters.py
"""Streamable HTTP transport parameters — Rust-backed via chuk_mcp_rs.

Kept as an import path for backward compatibility with downstream consumers
(e.g. chuk-tool-processor) that import
``chuk_mcp.transports.http.parameters.StreamableHTTPParameters``.
"""

from ..._rust import StreamableHTTPParameters

__all__ = ["StreamableHTTPParameters"]
