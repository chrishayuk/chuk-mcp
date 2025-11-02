# chuk_mcp/protocol/messages/tools/send_messages.py
from typing import Optional, Dict, Any, List
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

# chuk_mcp imports
from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase
from .tool import Tool
from .tool_result import ToolResult


class ListToolsResult(McpPydanticBase):
    """Result of listing tools."""

    tools: List[Tool]
    """List of available tools."""

    nextCursor: Optional[str] = None
    """Pagination cursor for fetching more tools."""

    model_config = {"extra": "allow"}


async def send_tools_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    cursor: Optional[str] = None,
    timeout: float = 60.0,
) -> ListToolsResult:
    """
    Send a 'tools/list' message to get available tools.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        cursor: Optional pagination cursor
        timeout: Timeout in seconds for the response

    Returns:
        ListToolsResult with typed Tool objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    params = {"cursor": cursor} if cursor else {}

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.TOOLS_LIST,
        params=params,
        timeout=timeout,
    )

    return ListToolsResult.model_validate(response)


async def send_tools_call(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    name: str,
    arguments: Dict[str, Any],
    timeout: float = 60.0,
) -> ToolResult:
    """
    Send a 'tools/call' message to invoke a tool.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        name: Name of the tool to call
        arguments: Dictionary of arguments to pass to the tool
        timeout: Timeout in seconds for the response

    Returns:
        ToolResult with typed content

    Raises:
        Exception: If the server returns an error or the request fails
    """
    # Validate inputs to prevent common errors
    if not isinstance(name, str):
        raise TypeError(f"Tool name must be a string, got {type(name).__name__}")

    if not isinstance(arguments, dict):
        raise TypeError(
            f"Tool arguments must be a dictionary, got {type(arguments).__name__}"
        )

    # Construct the parameters with proper validation
    params = {"name": name, "arguments": arguments}

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.TOOLS_CALL,
        params=params,
        timeout=timeout,
    )

    return ToolResult.model_validate(response)
