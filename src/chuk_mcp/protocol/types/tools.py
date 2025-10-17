# chuk_mcp/protocol/types/tools.py
"""
Tool-related types and utilities for MCP.

Updated for 2025-06-18 specification to include structured tool output support.
"""

from typing import List, Dict, Any, Optional, Literal, Callable, Sequence
from ..mcp_pydantic_base import McpPydanticBase, Field
from .content import Content


class ToolInputSchema(McpPydanticBase):
    """JSON Schema for tool input validation."""

    type: str = "object"
    """The type of the schema (typically 'object' for tool inputs)."""

    properties: Optional[Dict[str, Any]] = None
    """Properties of the input object."""

    required: Optional[List[str]] = None
    """List of required property names."""

    model_config = {"extra": "allow"}


class Tool(McpPydanticBase):
    """Definition of a tool that can be invoked."""

    name: str
    """Unique identifier for the tool."""

    description: Optional[str] = None
    """Human-readable description of what the tool does."""

    inputSchema: ToolInputSchema
    """JSON Schema defining the expected input format."""

    model_config = {"extra": "allow"}


class StructuredContent(McpPydanticBase):
    """
    Structured content for tool outputs (NEW in 2025-06-18).

    This allows tools to return structured data alongside or instead of text content.
    """

    type: Literal["structured"] = "structured"
    """The type identifier for structured content."""

    data: Dict[str, Any]
    """The structured data returned by the tool."""

    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    """Optional JSON Schema describing the structure of the data."""

    mimeType: Optional[str] = None
    """Optional MIME type for the structured data (e.g., 'application/json')."""

    model_config = {"extra": "allow"}


class ToolResult(McpPydanticBase):
    """
    Result of tool execution.

    Updated for 2025-06-18 to support structured content.
    """

    content: Optional[List[Content]] = None
    """Textual/media content returned by the tool."""

    structuredContent: Optional[List[StructuredContent]] = None
    """Structured content returned by the tool (NEW in 2025-06-18)."""

    isError: Optional[bool] = None
    """Whether this result represents an error."""

    model_config = {"extra": "allow"}


class CallToolRequest(McpPydanticBase):
    """Request to call a tool."""

    method: Literal["tools/call"] = "tools/call"

    params: "CallToolParams"


class CallToolParams(McpPydanticBase):
    """Parameters for calling a tool."""

    name: str
    """Name of the tool to call."""

    arguments: Optional[Dict[str, Any]] = None
    """Arguments to pass to the tool."""


class CallToolResult(McpPydanticBase):
    """Response from calling a tool."""

    content: Optional[List[Content]] = None
    """Content returned by the tool."""

    structuredContent: Optional[List[StructuredContent]] = None
    """Structured content returned by the tool (NEW in 2025-06-18)."""

    isError: Optional[bool] = None
    """Whether the tool execution resulted in an error."""

    model_config = {"extra": "allow"}


# Helper functions for creating tool results


def create_text_tool_result(text: str, is_error: bool = False) -> ToolResult:
    """Create a simple text tool result."""
    from .content import create_text_content

    content: Sequence[Content] = [create_text_content(text)]
    return ToolResult(content=content, isError=is_error)  # type: ignore[arg-type]


def create_structured_tool_result(
    data: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    mime_type: str = "application/json",
    is_error: bool = False,
) -> ToolResult:
    """
    Create a structured tool result (NEW in 2025-06-18).

    Args:
        data: The structured data to return
        schema: Optional JSON Schema describing the data
        mime_type: MIME type for the data
        is_error: Whether this represents an error
    """
    structured_content = StructuredContent(
        type="structured", data=data, schema_=schema, mimeType=mime_type
    )

    return ToolResult(structuredContent=[structured_content], isError=is_error)


def create_mixed_tool_result(
    text_content: Optional[List[Content]] = None,
    structured_content: Optional[List[StructuredContent]] = None,
    is_error: bool = False,
) -> ToolResult:
    """
    Create a tool result with both text and structured content.

    Args:
        text_content: Optional text/media content
        structured_content: Optional structured content
        is_error: Whether this represents an error
    """
    return ToolResult(
        content=text_content, structuredContent=structured_content, isError=is_error
    )


def create_error_tool_result(
    error_message: str, error_data: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """
    Create an error tool result with optional structured error data.

    Args:
        error_message: Human-readable error message
        error_data: Optional structured error data
    """
    from .content import create_text_content

    content: Sequence[Content] = [create_text_content(error_message)]
    structured_content = None

    if error_data:
        structured_content = [
            StructuredContent(
                type="structured", data=error_data, mimeType="application/json"
            )
        ]

    return ToolResult(
        content=content,  # type: ignore[arg-type]
        structuredContent=structured_content,
        isError=True,
    )


# Validation helpers


def validate_tool_result(result: ToolResult) -> bool:
    """
    Validate that a tool result has at least some content.

    Args:
        result: The tool result to validate

    Returns:
        True if the result has content or structured content, False otherwise
    """
    # Check if result is None
    if result is None:
        return False

    # Check for text content
    has_content = result.content is not None and len(result.content) > 0

    # Check for structured content
    has_structured = (
        result.structuredContent is not None and len(result.structuredContent) > 0
    )

    # Result is valid if it has either type of content
    return has_content or has_structured


def tool_result_to_dict(result: ToolResult) -> Dict[str, Any]:
    """Convert a tool result to a dictionary for JSON serialization."""
    if hasattr(result, "model_dump"):
        return result.model_dump(exclude_none=True)
    elif isinstance(result, dict):
        return result
    else:
        raise ValueError(f"Invalid tool result type: {type(result)}")


def parse_tool_result(data: Dict[str, Any]) -> ToolResult:
    """Parse a dictionary into a ToolResult object."""
    return ToolResult.model_validate(data)


# Example usage for servers


class ToolRegistry:
    """
    Example tool registry that supports structured output.

    This shows how to implement tools that return structured data.
    """

    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {}
        self.handlers: Dict[str, Callable] = {}

    def register_tool(self, tool: Tool, handler: Callable):
        """Register a tool with its handler."""
        self.tools[tool.name] = tool
        self.handlers[tool.name] = handler

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool and return its result."""
        if name not in self.handlers:
            return create_error_tool_result(f"Tool '{name}' not found")

        try:
            handler = self.handlers[name]
            result = await handler(arguments)

            # If handler returns a ToolResult, use it directly
            if isinstance(result, ToolResult):
                return result

            # If handler returns a dict, treat as structured content
            elif isinstance(result, dict):
                return create_structured_tool_result(result)

            # If handler returns a string, treat as text content
            elif isinstance(result, str):
                return create_text_tool_result(result)

            # Otherwise, convert to structured content
            else:
                return create_structured_tool_result({"result": result})

        except Exception as e:
            return create_error_tool_result(
                f"Tool execution error: {str(e)}",
                {"exception_type": type(e).__name__, "exception_message": str(e)},
            )


# Example tool implementations


async def example_structured_tool(arguments: Dict[str, Any]) -> ToolResult:
    """
    Example tool that returns structured data.

    This demonstrates the new structured content feature in 2025-06-18.
    """
    query = arguments.get("query", "")

    # Simulate some analysis
    analysis_result = {
        "query": query,
        "word_count": len(query.split()),
        "character_count": len(query),
        "analysis_timestamp": "2025-07-09T00:00:00Z",
        "sentiment": "neutral",
        "keywords": query.split()[:3],  # First 3 words as keywords
    }

    # Return both text explanation and structured data
    from .content import create_text_content

    text_content = [
        create_text_content(
            f"Analyzed query '{query}': {analysis_result['word_count']} words, "
            f"{analysis_result['character_count']} characters"
        )
    ]

    structured_content = [
        StructuredContent(
            type="structured",
            data=analysis_result,
            schema_={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "word_count": {"type": "integer"},
                    "character_count": {"type": "integer"},
                    "analysis_timestamp": {"type": "string", "format": "date-time"},
                    "sentiment": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
            },
            mimeType="application/json",
        )
    ]

    return ToolResult(
        content=text_content,  # type: ignore[arg-type]
        structuredContent=structured_content,
        isError=False,
    )


__all__ = [
    # Core types
    "Tool",
    "ToolInputSchema",
    "ToolResult",
    "StructuredContent",
    "CallToolRequest",
    "CallToolParams",
    "CallToolResult",
    # Helper functions
    "create_text_tool_result",
    "create_structured_tool_result",
    "create_mixed_tool_result",
    "create_error_tool_result",
    "validate_tool_result",
    "tool_result_to_dict",
    "parse_tool_result",
    # Registry and examples
    "ToolRegistry",
    "example_structured_tool",
]
