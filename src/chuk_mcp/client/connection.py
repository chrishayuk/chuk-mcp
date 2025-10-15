# chuk_mcp/client/connection.py
"""
Connection utilities and context managers.
"""

from contextlib import asynccontextmanager
from typing import Union

from .client import MCPClient
from ..transports.base import Transport
from ..transports.stdio import StdioTransport, StdioParameters


@asynccontextmanager
async def connect_to_server(transport_config: Union[Transport, StdioParameters]):
    """
    Connect to an MCP server with automatic initialization.

    Args:
        transport_config: Either a Transport instance or parameters to create one

    Usage:
        # Using transport directly
        transport = StdioTransport(StdioParameters(command="python", args=["server.py"]))
        async with connect_to_server(transport) as client:
            tools = await client.list_tools()

        # Using parameters (convenience)
        params = StdioParameters(command="python", args=["server.py"])
        async with connect_to_server(params) as client:
            tools = await client.list_tools()
    """
    # Create transport if parameters were provided
    if isinstance(transport_config, StdioParameters):
        transport: Transport = StdioTransport(transport_config)
    else:
        transport = transport_config

    async with transport:
        client = MCPClient(transport)
        await client.initialize()
        yield client
