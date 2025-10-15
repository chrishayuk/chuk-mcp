# chuk_mcp/client/__init__.py
"""
MCP Client - Connect to and communicate with MCP servers.
"""

from .client import MCPClient
from .connection import connect_to_server

# Import transports for convenience
from ..transports import stdio_client, StdioParameters

__all__ = [
    "MCPClient",
    "connect_to_server",
    "stdio_client",
    "StdioParameters",
]
