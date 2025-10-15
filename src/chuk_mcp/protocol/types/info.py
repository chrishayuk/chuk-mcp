# chuk_mcp/protocol/types/info.py
"""
MCP client and server information types.

These types provide identification and versioning information about
MCP clients and servers during initialization.
"""

from typing import Optional
from ..mcp_pydantic_base import McpPydanticBase


class ServerInfo(McpPydanticBase):
    """Information about the server implementation - matches official MCP specification."""

    name: str
    """The programmatic name of the server."""

    version: str
    """Version of the server implementation."""

    title: Optional[str] = None
    """
    Intended for UI and end-user contexts — optimized to be human-readable and easily understood,
    even by those unfamiliar with domain-specific terminology.
    If not provided, the name should be used for display.
    """

    model_config = {"extra": "allow"}


class ClientInfo(McpPydanticBase):
    """Information about the client implementation - matches official MCP specification."""

    name: str = "chuk-mcp-client"
    """The programmatic name of the client."""

    version: str = "0.3"
    """Version of the client implementation."""

    title: Optional[str] = None
    """
    Intended for UI and end-user contexts — optimized to be human-readable and easily understood,
    even by those unfamiliar with domain-specific terminology.
    If not provided, the name should be used for display.
    """

    model_config = {"extra": "allow"}


# Legacy aliases for backward compatibility
MCPServerInfo = ServerInfo
MCPClientInfo = ClientInfo
