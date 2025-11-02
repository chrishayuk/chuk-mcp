# chuk_mcp/protocol/messages/completion/send_messages.py
"""
Completion feature implementation for the Model Context Protocol.

This module implements argument completion functionality, allowing servers
to provide autocompletion suggestions for tool and resource arguments.
"""

from typing import Dict, Any, List, Optional, Union, Literal
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class ResourceReference(McpPydanticBase):
    """A reference to a resource or resource template definition."""

    type: Literal["ref/resource"] = "ref/resource"

    uri: str
    """The URI or URI template of the resource."""

    model_config = {"extra": "allow"}


class PromptReference(McpPydanticBase):
    """Identifies a prompt."""

    type: Literal["ref/prompt"] = "ref/prompt"

    name: str
    """The name of the prompt or prompt template."""

    model_config = {"extra": "allow"}


# Union type for references
Reference = Union[ResourceReference, PromptReference]


class ArgumentInfo(McpPydanticBase):
    """The argument's information for completion."""

    name: str
    """The name of the argument."""

    value: str
    """The value of the argument to use for completion matching."""

    model_config = {"extra": "allow"}


class CompletionResult(McpPydanticBase):
    """The completion options returned by the server."""

    values: List[str]
    """
    An array of completion values. Must not exceed 100 items.
    """

    total: Optional[int] = None
    """
    The total number of completion options available. 
    This can exceed the number of values actually sent in the response.
    """

    hasMore: Optional[bool] = None
    """
    Indicates whether there are additional completion options beyond those 
    provided in the current response, even if the exact total is unknown.
    """

    model_config = {"extra": "allow"}

    def __post_init__(self):
        """Validate completion result."""
        if len(self.values) > 100:
            raise ValueError("Completion values must not exceed 100 items")


async def send_completion_complete(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    ref: Union[Dict[str, Any], Reference],
    argument: Union[Dict[str, Any], ArgumentInfo],
    timeout: float = 60.0,
) -> CompletionResult:
    """
    Request completion options for a partially-typed argument.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        ref: Reference to the resource or prompt (either dict or Reference object)
        argument: The argument info (either dict or ArgumentInfo object)
        timeout: Timeout in seconds for the response

    Returns:
        CompletionResult with typed completion values

    Raises:
        Exception: If the server returns an error or the request fails
    """
    # Convert objects to dicts if needed
    ref_dict = ref.model_dump() if hasattr(ref, "model_dump") else ref
    arg_dict = argument.model_dump() if hasattr(argument, "model_dump") else argument

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.COMPLETION_COMPLETE,
        params={"ref": ref_dict, "argument": arg_dict},
        timeout=timeout,
    )

    completion_data = response.get("completion", {})
    return CompletionResult.model_validate(completion_data)


# Helper functions


def create_resource_reference(uri: str) -> ResourceReference:
    """
    Create a resource reference for completion.

    Args:
        uri: The URI or URI template of the resource

    Returns:
        ResourceReference object
    """
    return ResourceReference(type="ref/resource", uri=uri)


def create_prompt_reference(name: str) -> PromptReference:
    """
    Create a prompt reference for completion.

    Args:
        name: The name of the prompt or prompt template

    Returns:
        PromptReference object
    """
    return PromptReference(type="ref/prompt", name=name)


def create_argument_info(name: str, value: str) -> ArgumentInfo:
    """
    Create argument information for completion.

    Args:
        name: The name of the argument
        value: The current value to complete

    Returns:
        ArgumentInfo object
    """
    return ArgumentInfo(name=name, value=value)


async def complete_resource_argument(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    resource_uri: str,
    argument_name: str,
    argument_value: str,
    timeout: float = 60.0,
) -> CompletionResult:
    """
    Helper function to get completions for a resource argument.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        resource_uri: URI of the resource
        argument_name: Name of the argument to complete
        argument_value: Current value of the argument
        timeout: Timeout in seconds

    Returns:
        CompletionResult with suggested values
    """
    return await send_completion_complete(
        read_stream=read_stream,
        write_stream=write_stream,
        ref=create_resource_reference(resource_uri),
        argument=create_argument_info(argument_name, argument_value),
        timeout=timeout,
    )


async def complete_prompt_argument(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    prompt_name: str,
    argument_name: str,
    argument_value: str,
    timeout: float = 60.0,
) -> CompletionResult:
    """
    Helper function to get completions for a prompt argument.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        prompt_name: Name of the prompt
        argument_name: Name of the argument to complete
        argument_value: Current value of the argument
        timeout: Timeout in seconds

    Returns:
        CompletionResult with suggested values
    """
    return await send_completion_complete(
        read_stream=read_stream,
        write_stream=write_stream,
        ref=create_prompt_reference(prompt_name),
        argument=create_argument_info(argument_name, argument_value),
        timeout=timeout,
    )


class CompletionProvider:
    """
    Helper class for implementing server-side completion support.

    Servers can use this class to manage completion handlers for
    different resources and prompts.
    """

    def __init__(self) -> None:
        """Initialize the completion provider."""
        self._resource_handlers: Dict[str, Any] = {}
        self._prompt_handlers: Dict[str, Any] = {}

    def register_resource_handler(self, uri_pattern: str, handler: Any) -> None:
        """
        Register a completion handler for a resource URI pattern.

        Args:
            uri_pattern: URI or pattern to match
            handler: Async function (argument_name, argument_value) -> List[str]
        """
        self._resource_handlers[uri_pattern] = handler

    def register_prompt_handler(self, prompt_name: str, handler: Any) -> None:
        """
        Register a completion handler for a prompt.

        Args:
            prompt_name: Name of the prompt
            handler: Async function (argument_name, argument_value) -> List[str]
        """
        self._prompt_handlers[prompt_name] = handler

    async def handle_completion_request(
        self, ref: Dict[str, Any], argument: Dict[str, Any]
    ) -> CompletionResult:
        """
        Handle a completion request.

        Args:
            ref: Reference to resource or prompt
            argument: Argument information

        Returns:
            CompletionResult with suggested values

        Raises:
            ValueError: If no handler is found
        """
        ref_type = ref.get("type")
        arg_name = argument.get("name")
        arg_value = argument.get("value", "")

        handler = None

        if ref_type == "ref/resource":
            uri = ref.get("uri")
            if uri:
                # Simple pattern matching - could be enhanced
                for pattern, h in self._resource_handlers.items():
                    if pattern in uri or pattern == uri:
                        handler = h
                        break
        elif ref_type == "ref/prompt":
            name = ref.get("name")
            if name:
                handler = self._prompt_handlers.get(name)

        if not handler:
            raise ValueError(f"No completion handler found for {ref}")

        # Call the handler
        values = await handler(arg_name, arg_value)

        # Ensure we don't exceed 100 items
        has_more = len(values) > 100
        if has_more:
            values = values[:100]

        return CompletionResult(
            values=values, total=len(values) if not has_more else None, hasMore=has_more
        )


# Utility functions for common completion scenarios


async def complete_file_path(
    current_value: str,
    base_dir: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    max_results: int = 50,
) -> List[str]:
    """
    Generate file path completions.

    Args:
        current_value: Current path value
        base_dir: Base directory to search from
        extensions: Optional list of file extensions to filter
        max_results: Maximum number of results

    Returns:
        List of suggested file paths
    """
    import os
    from pathlib import Path

    suggestions = []

    # Determine the directory to search
    if os.path.isabs(current_value):
        search_dir = os.path.dirname(current_value)
        prefix = os.path.basename(current_value)
    else:
        search_dir = base_dir or os.getcwd()
        prefix = current_value

    try:
        path = Path(search_dir)
        for item in path.iterdir():
            if item.name.startswith(prefix):
                if extensions:
                    if item.is_file() and item.suffix in extensions:
                        suggestions.append(str(item))
                else:
                    suggestions.append(str(item))

                if len(suggestions) >= max_results:
                    break
    except Exception:
        pass

    return suggestions


async def complete_enum_value(
    current_value: str, allowed_values: List[str], case_sensitive: bool = False
) -> List[str]:
    """
    Generate completions for enum-like values.

    Args:
        current_value: Current value
        allowed_values: List of allowed values
        case_sensitive: Whether to match case-sensitively

    Returns:
        List of matching values
    """
    if not case_sensitive:
        current_lower = current_value.lower()
        return [val for val in allowed_values if val.lower().startswith(current_lower)]
    else:
        return [val for val in allowed_values if val.startswith(current_value)]


__all__ = [
    # Types
    "ResourceReference",
    "PromptReference",
    "Reference",
    "ArgumentInfo",
    "CompletionResult",
    # Main function
    "send_completion_complete",
    # Helper functions
    "create_resource_reference",
    "create_prompt_reference",
    "create_argument_info",
    "complete_resource_argument",
    "complete_prompt_argument",
    # Provider class
    "CompletionProvider",
    # Utility functions
    "complete_file_path",
    "complete_enum_value",
]
