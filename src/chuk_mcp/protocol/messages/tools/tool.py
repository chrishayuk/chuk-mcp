# chuk_mcp/protocol/messages/tools/tool.py
from typing import Any, Dict, Optional
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


class Tool(McpPydanticBase):
    """Model representing a tool in the MCP protocol - spec compliant."""

    name: str
    """The programmatic name of the tool."""

    description: Optional[str] = None
    """A human-readable description of the tool."""

    inputSchema: Dict[str, Any]
    """A JSON Schema object defining the expected parameters for the tool."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field, serialized as '_meta' in JSON."""

    model_config = {"extra": "allow"}
