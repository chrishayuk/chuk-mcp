# chuk_mcp/client/__init__.py
"""
MCP Client — Rust-backed via chuk_mcp_rs.

Connect to and communicate with MCP servers. Both the high-level ``MCPClient``
and the ``connect_to_server`` convenience are implemented in the Rust core.
"""

from .._rust import MCPClient, StdioParameters, connect_to_server, stdio_client

__all__ = ["MCPClient", "connect_to_server", "stdio_client", "StdioParameters"]
