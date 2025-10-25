# chuk_mcp/protocol/messages/notifications.py
"""
Comprehensive notification handling for the Model Context Protocol.
Implements all notification types defined in the MCP specification.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, Optional, Union
from anyio.streams.memory import MemoryObjectSendStream

from chuk_mcp.protocol.messages.json_rpc_message import (
    create_notification,
)
from chuk_mcp.protocol.messages.message_method import MessageMethod


async def send_progress_notification(
    write_stream: MemoryObjectSendStream,
    progress_token: Union[str, int],
    progress: float,
    total: Optional[float] = None,
    message: Optional[str] = None,
) -> None:
    """
    Send a progress notification to inform about long-running operations.

    Args:
        write_stream: Stream to send the notification to
        progress_token: Token from the initial request's _meta.progressToken
        progress: Current progress value (should increase over time)
        total: Total expected progress (if known)
        message: Human-readable progress message
    """
    params = {
        "progressToken": progress_token,
        "progress": progress,
    }

    if total is not None:
        params["total"] = total

    if message is not None:
        params["message"] = message

    notification = create_notification(
        method=MessageMethod.NOTIFICATION_PROGRESS, params=params
    )

    try:
        await write_stream.send(notification)
        logging.debug(
            f"Sent progress notification: {progress}/{total if total else '?'}"
        )
    except Exception as e:
        logging.error(f"Failed to send progress notification: {e}")


async def handle_progress_notification(
    callback: Callable[
        [Union[str, int], float, Optional[float], Optional[str]], Awaitable[None]
    ],
    notification: Dict[str, Any],
) -> None:
    """
    Handle incoming progress notifications.

    Args:
        callback: Async function to call with (token, progress, total, message)
        notification: The notification message
    """
    if notification.get("method") != MessageMethod.NOTIFICATION_PROGRESS:
        return

    params = notification.get("params", {})
    await callback(
        params.get("progressToken"),
        params.get("progress", 0),
        params.get("total"),
        params.get("message"),
    )


# Cancellation Notifications


async def send_cancelled_notification(
    write_stream: MemoryObjectSendStream,
    request_id: Union[str, int],
    reason: Optional[str] = None,
) -> None:
    """
    Send a cancellation notification to cancel a previously-issued request.

    Args:
        write_stream: Stream to send the notification to
        request_id: ID of the request to cancel
        reason: Optional reason for cancellation
    """
    params = {"requestId": request_id}

    if reason is not None:
        params["reason"] = reason

    notification = create_notification(
        method=MessageMethod.NOTIFICATION_CANCELLED, params=params
    )

    try:
        await write_stream.send(notification)
        logging.debug(f"Sent cancellation for request {request_id}")
    except Exception as e:
        logging.error(f"Failed to send cancellation notification: {e}")


async def handle_cancelled_notification(
    callback: Callable[[Union[str, int], Optional[str]], Awaitable[None]],
    notification: Dict[str, Any],
) -> None:
    """
    Handle incoming cancellation notifications.

    Args:
        callback: Async function to call with (request_id, reason)
        notification: The notification message
    """
    if notification.get("method") != MessageMethod.NOTIFICATION_CANCELLED:
        return

    params = notification.get("params", {})
    await callback(params.get("requestId"), params.get("reason"))


# Logging Notifications


async def handle_logging_message_notification(
    callback: Callable[[str, Any, Optional[str]], Awaitable[None]],
    notification: Dict[str, Any],
) -> None:
    """
    Handle incoming logging message notifications from the server.

    Args:
        callback: Async function to call with (level, data, logger)
        notification: The notification message
    """
    if notification.get("method") != MessageMethod.NOTIFICATION_MESSAGE:
        return

    params = notification.get("params", {})
    await callback(
        params.get("level", "info"), params.get("data"), params.get("logger")
    )


# Roots Notifications (Client feature)


async def send_roots_list_changed_notification(
    write_stream: MemoryObjectSendStream,
) -> None:
    """
    Send a notification that the roots list has changed.

    Args:
        write_stream: Stream to send the notification to
    """
    notification = create_notification(
        method=MessageMethod.NOTIFICATION_ROOTS_LIST_CHANGED, params={}
    )

    try:
        await write_stream.send(notification)
        logging.debug("Sent roots list changed notification")
    except Exception as e:
        logging.error(f"Failed to send roots list changed notification: {e}")


# Unified Notification Handler


class NotificationHandler:
    """
    Centralized notification handler for all MCP notifications.
    Register callbacks for different notification types.
    """

    def __init__(self) -> None:
        self.handlers: Dict[str, Callable] = {}

    def register(self, method: str, handler: Callable) -> None:
        """Register a handler for a specific notification method."""
        self.handlers[method] = handler
        logging.debug(f"Registered handler for {method}")

    async def handle(self, notification: Dict[str, Any]) -> None:
        """Route notification to the appropriate handler."""
        method = notification.get("method")
        if not method:
            logging.warning("Received notification without method")
            return

        handler = self.handlers.get(method)
        if handler:
            try:
                await handler(notification)
            except Exception as e:
                logging.error(f"Error handling {method} notification: {e}")
        else:
            logging.debug(f"No handler registered for {method}")

    def register_defaults(self):
        """Register default handlers that just log notifications."""

        async def log_notification(notification: Dict[str, Any]) -> None:
            method = notification.get("method")
            params = notification.get("params", {})
            logging.debug(f"Notification {method}: {params}")

        # Register all known notification types
        for method in [
            MessageMethod.NOTIFICATION_INITIALIZED,
            MessageMethod.NOTIFICATION_PROGRESS,
            MessageMethod.NOTIFICATION_CANCELLED,
            MessageMethod.NOTIFICATION_MESSAGE,
            MessageMethod.NOTIFICATION_RESOURCES_LIST_CHANGED,
            MessageMethod.NOTIFICATION_RESOURCES_UPDATED,
            MessageMethod.NOTIFICATION_TOOLS_LIST_CHANGED,
            MessageMethod.NOTIFICATION_PROMPTS_LIST_CHANGED,
            MessageMethod.NOTIFICATION_ROOTS_LIST_CHANGED,
        ]:
            self.register(method, log_notification)
