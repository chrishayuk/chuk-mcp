# chuk_mcp/protocol/messages/logging/send_messages.py
"""
Logging message functions for the Model Context Protocol.

This module implements logging-related message functions.
"""

from typing import Dict, Any, Literal
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod

# Type for log levels
LogLevel = Literal[
    "debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"
]


async def send_logging_set_level(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    level: LogLevel,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Send a request to set the logging level on the server.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        level: The logging level to set
        timeout: Timeout in seconds for the response

    Returns:
        Response from the server

    Raises:
        Exception: If the server returns an error or the request fails
    """
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.LOGGING_SET_LEVEL,
        params={"level": level},
        timeout=timeout,
    )

    return response


__all__ = ["send_logging_set_level", "LogLevel"]
