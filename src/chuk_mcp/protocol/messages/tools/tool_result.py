# chuk_mcp/protocol/messages/tools/tool_result.py
from typing import Any, Dict, List, Optional
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


class ToolResult(McpPydanticBase):
    """Model representing the result of a tool invocation - spec compliant."""

    content: List[Dict[str, Any]]
    """List of content blocks returned by the tool."""

    isError: bool = False
    """Whether the tool execution resulted in an error."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field, serialized as '_meta' in JSON."""

    model_config = {"extra": "allow"}
