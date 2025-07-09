# chuk_mcp/transports/http/http_client.py
"""
HTTP client context manager similar to stdio_client.
"""
from contextlib import asynccontextmanager
from typing import Tuple

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .transport import HTTPTransport
from .parameters import HTTPParameters

__all__ = ["http_client"]


@asynccontextmanager
async def http_client(parameters: HTTPParameters) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
    """
    Create an HTTP client and return streams that work with send_message.
    
    Usage:
        async with http_client(http_params) as (read_stream, write_stream):
            response = await send_message(read_stream, write_stream, "ping")
    
    Args:
        parameters: HTTP transport parameters
        
    Returns:
        Tuple of (read_stream, write_stream) for JSON-RPC communication
    """
    transport = HTTPTransport(parameters)
    
    try:
        async with transport:
            yield await transport.get_streams()
    except Exception as e:
        # Let exceptions propagate
        raise