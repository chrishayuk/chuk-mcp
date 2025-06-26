# chuk_mcp/mcp_client/messages/initialize/mcp_server_capabilities.py
from typing import Optional, Dict, Any
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field

class LoggingCapability(McpPydanticBase):
    """Capability for logging operations - spec compliant."""
    model_config = {"extra": "allow"}

class PromptsCapability(McpPydanticBase):
    """Capability for prompts operations - spec compliant."""
    listChanged: Optional[bool] = None
    """Whether this server supports notifications for changes to the prompt list."""
    model_config = {"extra": "allow"}

class ResourcesCapability(McpPydanticBase):
    """Capability for resources operations - spec compliant."""
    subscribe: Optional[bool] = None
    """Whether this server supports subscribing to resource updates."""
    listChanged: Optional[bool] = None
    """Whether this server supports notifications for changes to the resource list."""
    model_config = {"extra": "allow"}

class ToolsCapability(McpPydanticBase):
    """Capability for tools operations - spec compliant."""
    listChanged: Optional[bool] = None
    """Whether this server supports notifications for changes to the tool list."""
    model_config = {"extra": "allow"}

class CompletionCapability(McpPydanticBase):
    """Capability for completion operations - spec compliant."""
    model_config = {"extra": "allow"}

class MCPServerCapabilities(McpPydanticBase):
    """Capabilities that a server may support - matches official MCP specification."""
    
    experimental: Optional[Dict[str, Dict[str, Any]]] = None
    """Experimental, non-standard capabilities that the server supports."""
    
    logging: Optional[LoggingCapability] = None
    """Present if the server supports sending log messages to the client."""
    
    prompts: Optional[PromptsCapability] = None
    """Present if the server offers any prompt templates."""
    
    resources: Optional[ResourcesCapability] = None
    """Present if the server offers any resources to read."""
    
    tools: Optional[ToolsCapability] = None
    """Present if the server offers any tools to call."""
    
    completion: Optional[CompletionCapability] = None
    """Present if the server supports argument completion."""
    
    model_config = {"extra": "allow"}
