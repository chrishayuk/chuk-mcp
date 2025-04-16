# tests/mcp/transport/stdio/test_stdio_client_context.py
import pytest
import anyio
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client, StdioClient
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

pytestmark = [pytest.mark.asyncio]

async def test_stdio_client_context_yields_client():
    """`async with stdio_client(...) as client` should give you a StdioClient."""
    server = StdioServerParameters(command="echo", args=[])
    async with stdio_client(server) as client:
        assert isinstance(client, StdioClient)
    # After exit, the client.task_group should be torn down
    # (no exception, just ensure __aexit__ completes)

async def test_stdio_client_context_unpack_fails():
    """
    Ensure that people don't accidentally write:
        async with stdio_client(...) as (r, w)
    since stdio_client now yields a single StdioClient, not a tuple.
    """
    server = StdioServerParameters(command="echo", args=[])
    ctx = stdio_client(server)
    with pytest.raises(TypeError):
        # trying to unpack should give a TypeError
        async with ctx as (_r, _w):
            pass
