# chuk_mcp/protocol/messages/resources/resource_template.py
from typing import Optional, Dict, Any
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


class ResourceTemplate(McpPydanticBase):
    """Model representing a resource template in the MCP protocol - spec compliant."""

    uriTemplate: str
    """A URI template (RFC 6570) for constructing resource URIs."""

    name: str
    """The programmatic name of the template."""

    description: Optional[str] = None
    """A human-readable description of what this template is for."""

    mimeType: Optional[str] = None
    """The MIME type for resources matching this template, if consistent."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field, serialized as '_meta' in JSON."""

    model_config = {"extra": "allow"}
