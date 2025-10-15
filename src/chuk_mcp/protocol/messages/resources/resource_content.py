# chuk_mcp/protocol/messages/resources/resource_content.py
from typing import Optional, Dict, Any
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


class ResourceContent(McpPydanticBase):
    """Model representing resource content in the MCP protocol - spec compliant."""

    uri: str
    """The URI of this resource."""

    mimeType: Optional[str] = None
    """The MIME type of this resource, if known."""

    text: Optional[str] = None
    """The text content. Only set if the resource can be represented as text."""

    blob: Optional[str] = None
    """Base64-encoded binary data. Only set for binary resources."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field, serialized as '_meta' in JSON."""

    model_config = {"extra": "allow"}
