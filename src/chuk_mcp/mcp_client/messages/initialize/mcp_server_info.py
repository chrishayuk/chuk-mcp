# chuk_mcp/chuk_mcp.mcp_client/messages/initialize/mcp_server_info.py
from typing import Optional
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase

class MCPServerInfo(McpPydanticBase):
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