# chuk_mcp/protocol/messages/resources/send_messages.py
from typing import Optional, List
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

# chuk_mcp imports
from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase
from .resource import Resource
from .resource_content import ResourceContent
from .resource_template import ResourceTemplate


class ListResourcesResult(McpPydanticBase):
    """Result of listing resources."""

    resources: List[Resource]
    """List of available resources."""

    nextCursor: Optional[str] = None
    """Pagination cursor for fetching more resources."""

    model_config = {"extra": "allow"}


class ReadResourceResult(McpPydanticBase):
    """Result of reading a resource."""

    contents: List[ResourceContent]
    """Resource contents."""

    model_config = {"extra": "allow"}


class ListResourceTemplatesResult(McpPydanticBase):
    """Result of listing resource templates."""

    resourceTemplates: List[ResourceTemplate]
    """List of available resource templates."""

    nextCursor: Optional[str] = None
    """Pagination cursor for fetching more templates."""

    model_config = {"extra": "allow"}


async def send_resources_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    cursor: Optional[str] = None,
    timeout: float = 60.0,
) -> ListResourcesResult:
    """
    Send a 'resources/list' message and return typed results.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        cursor: Optional pagination cursor
        timeout: Timeout in seconds for the response

    Returns:
        ListResourcesResult with typed Resource objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    params = {"cursor": cursor} if cursor else {}

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.RESOURCES_LIST,
        params=params,
        timeout=timeout,
    )

    return ListResourcesResult.model_validate(response)


async def send_resources_read(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    uri: str,
    timeout: float = 60.0,
) -> ReadResourceResult:
    """
    Send a 'resources/read' message to retrieve resource contents.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        uri: URI of the resource to read
        timeout: Timeout in seconds for the response

    Returns:
        ReadResourceResult with typed ResourceContent objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.RESOURCES_READ,
        params={"uri": uri},
        timeout=timeout,
    )

    return ReadResourceResult.model_validate(response)


async def send_resources_templates_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    timeout: float = 60.0,
) -> ListResourceTemplatesResult:
    """
    Send a 'resources/templates/list' message to get available resource templates.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        timeout: Timeout in seconds for the response

    Returns:
        ListResourceTemplatesResult with typed ResourceTemplate objects

    Raises:
        Exception: If the server returns an error or the request fails
    """
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.RESOURCES_TEMPLATES_LIST,
        timeout=timeout,
    )

    return ListResourceTemplatesResult.model_validate(response)


async def send_resources_subscribe(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    uri: str,
    timeout: float = 60.0,
) -> bool:
    """
    Send a 'resources/subscribe' message to subscribe to resource changes.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        uri: URI of the resource to subscribe to
        timeout: Timeout in seconds for the response

    Returns:
        bool: True if subscription was successful, False otherwise

    Raises:
        Exception: If the server returns an error or the request fails
    """
    try:
        response = await send_message(
            read_stream=read_stream,
            write_stream=write_stream,
            method=MessageMethod.RESOURCES_SUBSCRIBE,
            params={"uri": uri},
            timeout=timeout,
        )

        # Any non-error response indicates success
        return response is not None
    except Exception:
        # Subscription failed
        return False


async def send_resources_unsubscribe(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    uri: str,
    timeout: float = 60.0,
) -> bool:
    """
    Send a 'resources/unsubscribe' message to unsubscribe from resource changes.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        uri: URI of the resource to unsubscribe from
        timeout: Timeout in seconds for the response

    Returns:
        bool: True if unsubscription was successful, False otherwise

    Raises:
        Exception: If the server returns an error or the request fails
    """
    try:
        response = await send_message(
            read_stream=read_stream,
            write_stream=write_stream,
            method=MessageMethod.RESOURCES_UNSUBSCRIBE,
            params={"uri": uri},
            timeout=timeout,
        )

        # Any non-error response indicates success
        return response is not None
    except Exception as e:
        # Log the error for debugging
        import logging

        logging.error(f"Failed to unsubscribe from resource {uri}: {e}")
        # Unsubscription failed
        return False
