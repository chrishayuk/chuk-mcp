# chuk_mcp/chuk_mcp.mcp_client/messages/initialize/chuk_mcp.mcp_client_info.py
from typing import Optional
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase

class MCPClientInfo(McpPydanticBase):
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