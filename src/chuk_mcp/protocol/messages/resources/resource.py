# chuk_mcp/protocol/messages/resources/resource.py
from typing import Optional, Dict, Any
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


class Resource(McpPydanticBase):
    """Model representing a resource in the MCP protocol - spec compliant."""

    uri: str
    """The URI of this resource."""

    name: str
    """The programmatic name of the resource."""

    description: Optional[str] = None
    """A description of what this resource represents."""

    mimeType: Optional[str] = None
    """The MIME type of this resource, if known."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field, serialized as '_meta' in JSON."""

    model_config = {"extra": "allow"}
