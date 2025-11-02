# chuk_mcp/protocol/messages/prompts/send_messages.py
from typing import Optional, Dict, Any
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

# chuk_mcp imports
from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from .prompt import ListPromptsResult, GetPromptResult


async def send_prompts_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    cursor: Optional[str] = None,
    timeout: float = 60.0,
) -> ListPromptsResult:
    """
    Send a 'prompts/list' message to get available prompts.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        cursor: Optional pagination cursor
        timeout: Timeout in seconds for the response

    Returns:
        ListPromptsResult with typed Prompt objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    params = {"cursor": cursor} if cursor else {}

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.PROMPTS_LIST,
        params=params,
        timeout=timeout,
    )

    return ListPromptsResult.model_validate(response)


async def send_prompts_get(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> GetPromptResult:
    """
    Send a 'prompts/get' message to retrieve a specific prompt by name and apply arguments.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        name: Name of the prompt to retrieve
        arguments: Optional dictionary of arguments to customize the prompt
        timeout: Timeout in seconds for the response

    Returns:
        GetPromptResult with typed PromptMessage objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    # Validate inputs to prevent common errors
    if not isinstance(name, str):
        raise TypeError(f"Prompt name must be a string, got {type(name).__name__}")

    if arguments is not None and not isinstance(arguments, dict):
        raise TypeError(
            f"Prompt arguments must be a dictionary, got {type(arguments).__name__}"
        )

    # Construct the parameters with proper validation
    params: Dict[str, Any] = {"name": name}
    if arguments:
        params["arguments"] = arguments

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.PROMPTS_GET,
        params=params,
        timeout=timeout,
    )

    return GetPromptResult.model_validate(response)
