# chuk_mcp/transports/sse/sse_client.py
"""
SSE client context manager similar to stdio_client.
"""
from contextlib import asynccontextmanager
from typing import Tuple

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .transport import SSETransport
from .parameters import SSEParameters

__all__ = ["sse_client"]


@asynccontextmanager
async def sse_client(parameters: SSEParameters) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
    """
    Create an SSE client and return streams that work with send_message.
    
    Usage:
        async with sse_client(sse_params) as (read_stream, write_stream):
            response = await send_message(read_stream, write_stream, "ping")
    
    Args:
        parameters: SSE transport parameters
        
    Returns:
        Tuple of (read_stream, write_stream) for JSON-RPC communication
    """
    transport = SSETransport(parameters)
    
    try:
        async with transport:
            yield await transport.get_streams()
    except Exception as e:
        # Let exceptions propagate
        raise