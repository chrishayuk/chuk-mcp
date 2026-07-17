"""
Server Helper Functions for chuk-mcp E2E Examples.

The stdio serve loop now lives in the Rust core: ``MCPServer.run_stdio()``
reads newline-delimited JSON-RPC on stdin/stdout and dispatches to the
registered tool/resource handlers. This helper is kept as a thin wrapper so the
existing examples keep working unchanged.
"""

import logging

from chuk_mcp.server import MCPServer

logger = logging.getLogger(__name__)


async def run_stdio_server(mcp_server: MCPServer):
    """
    Run an MCP server using stdio transport (Rust-backed).

    Args:
        mcp_server: The MCPServer instance with registered handlers.
    """
    await mcp_server.run_stdio()
