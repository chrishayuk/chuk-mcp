# chuk_mcp/protocol/messages/roots/send_messages.py
"""
Roots feature implementation for the Model Context Protocol.

This module implements the client-side roots feature, which allows servers
to discover what directories and files the client has access to.
"""

from typing import Dict, Any, List, Optional
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class Root(McpPydanticBase):
    """
    Represents a root directory or file that the server can operate on.
    """

    uri: str
    """
    The URI identifying the root. This *must* start with file:// for now.
    This restriction may be relaxed in future versions of the protocol to allow
    other URI schemes.
    """

    name: Optional[str] = None
    """
    An optional name for the root. This can be used to provide a human-readable
    identifier for the root, which may be useful for display purposes or for
    referencing the root in other parts of the application.
    """

    model_config = {"extra": "allow"}

    def __post_init__(self):
        """Validate the root URI."""
        if not self.uri.startswith("file://"):
            raise ValueError(f"Root URI must start with 'file://', got: {self.uri}")


class ListRootsResult(McpPydanticBase):
    """
    The client's response to a roots/list request from the server.
    """

    roots: List[Root]
    """Array of Root objects representing directories/files the server can operate on."""

    model_config = {"extra": "allow"}


async def send_roots_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    timeout: float = 60.0,
) -> ListRootsResult:
    """
    Send a 'roots/list' response when requested by the server.

    This is typically called in response to a server's roots/list request.
    The client should return the list of directories/files it allows the
    server to access.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        timeout: Timeout in seconds for the response

    Returns:
        ListRootsResult with typed Root objects

    Raises:
        Exception: If the request fails
    """
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.ROOTS_LIST,
        timeout=timeout,
    )

    return ListRootsResult.model_validate(response)


async def handle_roots_list_request(
    roots: List[Root], request_id: Any
) -> JSONRPCMessage:
    """
    Handle an incoming roots/list request from the server.

    This should be called when the client receives a roots/list request.
    It creates the appropriate response message.

    Args:
        roots: List of Root objects to return
        request_id: The ID from the incoming request

    Returns:
        JSONRPCMessage response to send back
    """
    from chuk_mcp.protocol.messages.json_rpc_message import create_response

    result = ListRootsResult(roots=roots)

    return create_response(id=request_id, result=result.model_dump())


async def send_roots_list_changed_notification(
    write_stream: MemoryObjectSendStream,
) -> None:
    """
    Send a notification that the roots list has changed.

    This notification should be sent whenever the client adds, removes,
    or modifies any root. The server should then request an updated list
    of roots using the ListRootsRequest.

    Args:
        write_stream: Stream to send the notification to
    """
    from chuk_mcp.protocol.messages.json_rpc_message import create_notification

    notification = create_notification(
        method=MessageMethod.NOTIFICATION_ROOTS_LIST_CHANGED, params={}
    )

    try:
        await write_stream.send(notification)
    except Exception as e:
        import logging

        logging.error(f"Failed to send roots list changed notification: {e}")


# Helper functions


def create_root(uri: str, name: Optional[str] = None) -> Root:
    """
    Create a Root object.

    Args:
        uri: File URI (must start with "file://")
        name: Optional human-readable name

    Returns:
        Root object

    Raises:
        ValueError: If URI doesn't start with "file://"
    """
    return Root(uri=uri, name=name)


def create_file_root(path: str, name: Optional[str] = None) -> Root:
    """
    Create a Root object from a file system path.

    Args:
        path: Absolute file system path
        name: Optional human-readable name

    Returns:
        Root object
    """
    import os
    from urllib.parse import quote

    # Ensure absolute path
    abs_path = os.path.abspath(path)

    # Convert to file URI
    # On Windows, we need to add an extra slash
    if os.name == "nt":
        uri = f"file:///{quote(abs_path.replace(os.sep, '/'))}"
    else:
        uri = f"file://{quote(abs_path)}"

    return Root(uri=uri, name=name or os.path.basename(abs_path))


def parse_file_root(root: Root) -> str:
    """
    Parse a Root object to get the file system path.

    Args:
        root: Root object with file:// URI

    Returns:
        Absolute file system path

    Raises:
        ValueError: If URI doesn't start with "file://"
    """
    from urllib.parse import unquote, urlparse

    if not root.uri.startswith("file://"):
        raise ValueError(f"Expected file:// URI, got: {root.uri}")

    parsed = urlparse(root.uri)
    path = unquote(parsed.path)

    # On Windows, remove the leading slash
    import os

    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return path


# Client implementation helpers


class RootsManager:
    """
    Helper class to manage roots on the client side.

    This class helps track which roots are available and handles
    notifications when the list changes.
    """

    def __init__(self, write_stream: Optional[MemoryObjectSendStream] = None):
        """
        Initialize the roots manager.

        Args:
            write_stream: Optional stream for sending notifications
        """
        self._roots: Dict[str, Root] = {}
        self._write_stream = write_stream

    def add_root(self, root: Root) -> None:
        """Add a root to the list."""
        self._roots[root.uri] = root
        self._notify_changed()

    def remove_root(self, uri: str) -> None:
        """Remove a root by URI."""
        if uri in self._roots:
            del self._roots[uri]
            self._notify_changed()

    def get_roots(self) -> List[Root]:
        """Get the current list of roots."""
        return list(self._roots.values())

    def clear(self) -> None:
        """Clear all roots."""
        if self._roots:
            self._roots.clear()
            self._notify_changed()

    def _notify_changed(self) -> None:
        """Send a notification that the roots list changed."""
        if self._write_stream:
            import asyncio

            asyncio.create_task(
                send_roots_list_changed_notification(self._write_stream)
            )

    async def handle_list_request(self, request_id: Any) -> JSONRPCMessage:
        """
        Handle a roots/list request.

        Args:
            request_id: The request ID to use in the response

        Returns:
            Response message
        """
        return await handle_roots_list_request(
            roots=self.get_roots(), request_id=request_id
        )


__all__ = [
    # Types
    "Root",
    "ListRootsResult",
    # Main functions
    "send_roots_list",
    "handle_roots_list_request",
    "send_roots_list_changed_notification",
    # Helper functions
    "create_root",
    "create_file_root",
    "parse_file_root",
    # Manager class
    "RootsManager",
]
