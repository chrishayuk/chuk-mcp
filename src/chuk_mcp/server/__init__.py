# chuk_mcp/server/__init__.py
"""
MCP Server — Rust-backed via chuk_mcp_rs.

``MCPServer`` (tool/resource registration, protocol handling, sessions, and the
stdio serve loop via ``run_stdio()``) is implemented in the Rust core.
"""

from .._rust import MCPServer

__all__ = ["MCPServer"]
