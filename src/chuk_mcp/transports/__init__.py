# chuk_mcp/transports/__init__.py
"""
MCP transport implementations for chuk_mcp — Rust-backed via chuk_mcp_rs.

The stdio transport is provided by the Rust core. HTTP and SSE transports are
implemented in the Rust core as well and are surfaced through the high-level
client rather than as standalone Python transport classes.
"""

from .stdio import StdioParameters, StdioServerParameters, stdio_client

__all__ = ["StdioParameters", "StdioServerParameters", "stdio_client"]


def get_available_transports():
    """Get list of available transport types."""
    return ["stdio", "http", "sse"]
