"""Public-API integration tests for the Rust-backed chuk_mcp.

These replace the old anyio-plumbing message tests (which were bound to the
deleted pure-Python implementation). They drive the public API end-to-end:

* stdio: a chuk_mcp.MCPServer fixture spoken to by the client + send_* API
* Streamable HTTP: the HTTP transport against a threaded HTTP MCP server
* typed results, capabilities accessor, and the error hierarchy
* the exact import paths that downstream consumers (chuk-tool-processor,
  chuk-mcp-server) depend on
"""

import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import chuk_mcp
from chuk_mcp import (
    StdioServerParameters,
    connect_to_server,
    stdio_client,
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    NonRetryableError,
    McpError,
)

# asyncio_mode = auto (see pyproject), so async tests run without an explicit mark.

ECHO_SERVER = str(Path(__file__).parent / "_stdio_echo_server.py")


def _server_params():
    return StdioServerParameters(command=sys.executable, args=[ECHO_SERVER])


# --------------------------------------------------------------------------
# Import-surface compliance (downstream consumers)
# --------------------------------------------------------------------------


def test_downstream_import_paths():
    """The exact import paths chuk-tool-processor and chuk-mcp-server use."""
    # chuk-tool-processor
    from chuk_mcp.config import load_config  # noqa: F401
    from chuk_mcp.transports.stdio import stdio_client as _sc  # noqa: F401
    from chuk_mcp.transports.stdio.parameters import StdioParameters  # noqa: F401
    from chuk_mcp.transports.http.parameters import (  # noqa: F401
        StreamableHTTPParameters,
    )
    from chuk_mcp.transports.http.transport import (  # noqa: F401
        StreamableHTTPTransport,
    )

    # chuk-mcp-server
    from chuk_mcp.protocol.messages.tools.tool import Tool  # noqa: F401
    from chuk_mcp.protocol.messages.tools.tool_input_schema import (  # noqa: F401
        ToolInputSchema,
    )
    from chuk_mcp.protocol.messages.resources.resource import Resource  # noqa: F401
    from chuk_mcp.protocol.types import (  # noqa: F401
        CURRENT_VERSION,
        ServerInfo,
        ServerCapabilities,
        ToolsCapability,
        MCPError,
        ValidationError,
        create_text_content,
        content_to_dict,
    )


def test_public_all_resolves():
    missing = [n for n in chuk_mcp.__all__ if not hasattr(chuk_mcp, n)]
    assert not missing, missing


# --------------------------------------------------------------------------
# stdio: high-level client
# --------------------------------------------------------------------------


async def test_stdio_high_level_client():
    async with await connect_to_server(_server_params()) as client:
        assert client.server_info.name == "integration-echo"
        # typed capabilities accessor
        assert bool(client.capabilities.tools) is True
        assert client.capabilities.prompts is None

        assert await client.ping() is True

        tools = await client.list_tools()
        assert sorted(t.name for t in tools) == ["add", "greet"]

        result = await client.call_tool("greet", {"name": "Integration"})
        assert result.text == "Hello, Integration!"
        assert result.isError is False
        # Phase 3: a legacy result (no resultType on the wire) normalises upward
        # to "complete", and .value is the flattened 0.9-era accessor, while the
        # existing .text accessor keeps working unchanged.
        assert result.resultType == "complete"
        assert result.value == "Hello, Integration!"

        add = await client.call_tool("add", {"a": 3, "b": 4})
        assert json.loads(add.text)["sum"] == 7

        resources = await client.list_resources()
        assert resources[0].uri == "demo://motd"
        contents = await client.read_resource("demo://motd")
        assert contents.contents[0].text == "integration message of the day"


# --------------------------------------------------------------------------
# stdio: low-level send_* API
# --------------------------------------------------------------------------


async def test_stdio_low_level_api():
    async with stdio_client(_server_params()) as (read, write):
        init = await send_initialize(read, write)
        assert init.serverInfo.name == "integration-echo"
        # send_initialize is the *legacy* handshake, so it negotiates the latest
        # legacy revision, never the stateless CURRENT_VERSION (2026-07-28),
        # which has no `initialize` step.
        assert init.protocolVersion == chuk_mcp.LATEST_LEGACY_VERSION

        assert await send_ping(read, write) is True

        tools = await send_tools_list(read, write)
        assert [t.name for t in tools.tools] == ["add", "greet"]

        result = await send_tools_call(read, write, "greet", {"name": "Low"})
        assert result.text == "Hello, Low!"

        resources = await send_resources_list(read, write)
        assert resources.resources[0].uri == "demo://motd"
        contents = await send_resources_read(read, write, "demo://motd")
        assert contents.contents[0].text == "integration message of the day"


async def test_error_hierarchy():
    async with await connect_to_server(_server_params()) as client:
        with pytest.raises(NonRetryableError) as excinfo:
            await client.call_tool("does-not-exist", {})
        assert isinstance(excinfo.value, McpError)


# --------------------------------------------------------------------------
# Streamable HTTP transport
# --------------------------------------------------------------------------


class _McpHttpHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        message_id, method = body.get("id"), body.get("method")
        if message_id is None:  # notification
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            return

        if method == "initialize":
            result = {
                "protocolVersion": body["params"]["protocolVersion"],
                "serverInfo": {"name": "http-echo", "version": "1.0"},
                "capabilities": {"tools": {}},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]}
        elif method == "tools/call":
            text = body["params"]["arguments"].get("text", "")
            result = {"content": [{"type": "text", "text": f"echo:{text}"}]}
        else:
            result = {}

        payload = json.dumps(
            {"jsonrpc": "2.0", "id": message_id, "result": result}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


async def test_streamable_http_transport():
    from chuk_mcp.transports.http.transport import StreamableHTTPTransport
    from chuk_mcp.transports.http.parameters import StreamableHTTPParameters

    server = ThreadingHTTPServer(("127.0.0.1", 0), _McpHttpHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        params = StreamableHTTPParameters(
            url=f"http://127.0.0.1:{port}/mcp", timeout=10.0
        )
        transport = StreamableHTTPTransport(params)
        await transport.__aenter__()
        try:
            read, write = await transport.get_streams()
            init = await send_initialize(read, write)
            assert init.serverInfo.name == "http-echo"
            assert await send_ping(read, write) is True
            tools = await send_tools_list(read, write)
            assert tools.tools[0].name == "echo"
            result = await send_tools_call(read, write, "echo", {"text": "hi"})
            assert result.text == "echo:hi"
        finally:
            await transport.__aexit__(None, None, None)
    finally:
        server.shutdown()
