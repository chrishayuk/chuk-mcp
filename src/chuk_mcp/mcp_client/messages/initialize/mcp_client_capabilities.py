# chuk_mcp/mcp_client/messages/initialize/mcp_client_capabilities.py
from typing import Optional, Dict, Any
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field

class RootsCapability(McpPydanticBase):
    """Capability for root operations - spec compliant."""
    listChanged: Optional[bool] = None
    """Whether the client supports notifications for changes to the roots list."""
    model_config = {"extra": "allow"}

class SamplingCapability(McpPydanticBase):
    """Capability for sampling operations - spec compliant."""
    model_config = {"extra": "allow"}

class ElicitationCapability(McpPydanticBase):
    """Capability for elicitation operations - spec compliant."""
    model_config = {"extra": "allow"}

class MCPClientCapabilities(McpPydanticBase):
    """Capabilities a client may support - matches official MCP specification."""
    
    experimental: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)
    """Experimental, non-standard capabilities that the client supports."""
    
    sampling: Optional[SamplingCapability] = None
    """Present if the client supports sampling from an LLM."""
    
    elicitation: Optional[ElicitationCapability] = None
    """Present if the client supports elicitation from the user."""
    
    roots: Optional[RootsCapability] = Field(default_factory=lambda: RootsCapability(listChanged=True))
    """Present if the client supports listing roots."""
    
    model_config = {"extra": "allow"}