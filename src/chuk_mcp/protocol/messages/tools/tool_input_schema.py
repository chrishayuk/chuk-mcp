# chuk_mcp/protocol/messages/tools/tool_input_schema.py
from typing import Any, Dict, List, Optional
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class ToolInputSchema(McpPydanticBase):
    """Model representing a tool input schema in the MCP protocol - spec compliant."""

    type: str
    """The schema type (typically 'object')."""

    properties: Dict[str, Any]
    """Schema properties defining the tool parameters."""

    required: Optional[List[str]] = None
    """List of required parameter names."""

    model_config = {"extra": "allow"}
