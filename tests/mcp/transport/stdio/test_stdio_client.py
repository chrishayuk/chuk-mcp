# tests/mcp/transport/stdio/test_stdio_client.py
import pytest
import anyio
import json
import logging
from unittest.mock import AsyncMock, patch, MagicMock

from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client, StdioClient
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

pytestmark = [pytest.mark.asyncio]
pytest.importorskip("chuk_mcp.mcp_client.transport.stdio.stdio_client")

###############################################################################
# Helpers & fixtures                                                          #
###############################################################################

def make_message(id=None, *, result=None, method=None, params=None):
    d = {"jsonrpc": "2.0"}
    if id is not None:
        d["id"] = id
    if method is not None:
        d["method"] = method
    if params is not None:
        d["params"] = params
    if result is not None:
        d["result"] = result
    return JSONRPCMessage.model_validate(d)

class MockProcess:
    """Thin stub for *anyio.abc.Process*."""

    def __init__(self, exit_code: int = 0):
        self.pid = 4242
        self._exit_code = exit_code
        self.returncode = None
        # stdin mocks need send & aclose for _stdin_writer
        self.stdin = AsyncMock()
        self.stdin.send = AsyncMock()
        self.stdin.aclose = AsyncMock()
        self.stdout = None  # patched per-test

    async def wait(self):
        self.returncode = self._exit_code
        return self._exit_code

    def terminate(self):
        self.returncode = self._exit_code

    def kill(self):
        self.returncode = self._exit_code

@pytest.fixture
def mock_stdio_client():
    """A *StdioClient* with a mocked subprocess and writer coroutine."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()
    return client

###############################################################################
# Parameter validation                                                        #
###############################################################################

async def test_stdio_client_invalid_parameters():
    with pytest.raises(ValueError, match="Server command must not be empty"):
        async with stdio_client(StdioServerParameters(command="", args=[])):
            pass

    bad = StdioServerParameters(command="echo", args=[])
    bad.args = "oops"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="list or tuple"):
        async with stdio_client(bad):
            pass

###############################################################################
# Routing + notification broadcast                                            #
###############################################################################

async def test_routing_multiple_requests():
    client = StdioClient(StdioServerParameters(command="test"))
    recv_a = client.new_request_stream("a")
    recv_b = client.new_request_stream("b")

    await client._route_message(make_message(id="b", result={"v": 2}))
    await client._route_message(make_message(id="a", result={"v": 1}))

    assert (await recv_a.receive()).result == {"v": 1}
    assert (await recv_b.receive()).result == {"v": 2}
    assert not client._pending  # cleaned up

async def test_notification_broadcast_and_unknown(caplog):
    """Notifications are broadcast; sending in background avoids deadlock on zero-buffer."""
    client = StdioClient(StdioServerParameters(command="test"))
    recv_notif = client.notifications

    # Route a notification in the background so send doesn't block
    async with anyio.create_task_group() as tg:
        tg.start_soon(client._route_message, make_message(method="ping"))
        note = await recv_notif.receive()
        assert note.method == "ping"
        tg.cancel_scope.cancel()

    # Unknown-id responses log a warning immediately
    caplog.set_level(logging.WARNING)
    await client._route_message(make_message(id="ghost"))
    assert "unknown id" in caplog.text.lower()

###############################################################################
# _stdin_writer                                                               #
###############################################################################

async def test_stdin_writer_model(mock_stdio_client):
    msg = make_message(id="x", method="run", params={"p": 1})
    mock_stdio_client.process.stdin = AsyncMock()

    async def gen():
        yield (msg.id, msg)
    mock_stdio_client._client_out = gen

    await mock_stdio_client._stdin_writer()
    sent = json.loads(mock_stdio_client.process.stdin.send.call_args[0][0].decode())
    assert sent["id"] == "x" and sent["method"] == "run"

async def test_stdin_writer_raw_string(mock_stdio_client):
    raw = '{"jsonrpc":"2.0","id":"s","method":"do","params":{}}'
    mock_stdio_client.process.stdin = AsyncMock()

    async def gen():
        yield (None, raw)
    mock_stdio_client._client_out = gen

    await mock_stdio_client._stdin_writer()
    sent = mock_stdio_client.process.stdin.send.call_args[0][0].decode().strip()
    assert sent == raw

async def test_stdin_writer_logs_on_error(mock_stdio_client):
    bad = MagicMock()
    bad.model_dump_json.side_effect = Exception("boom")
    mock_stdio_client.process.stdin = AsyncMock()

    async def gen():
        yield ("z", bad)
    mock_stdio_client._client_out = gen

    with patch("logging.error") as err:
        await mock_stdio_client._stdin_writer()
        err.assert_called()

###############################################################################
# _stdout_reader resilience                                                   #
###############################################################################

async def test_partial_line_parsing():
    client = StdioClient(StdioServerParameters(command="test"))
    full = '{"jsonrpc":"2.0","id":"p","result":{}}\n'
    client.process = MockProcess()

    class FakeStdout:
        async def __aiter__(self):
            yield full[:8]
            yield full[8:]
    client.process.stdout = FakeStdout()

    recv = client.new_request_stream("p")
    async with anyio.create_task_group() as tg:
        tg.start_soon(client._stdout_reader)
        assert (await recv.receive()).id == "p"
        tg.cancel_scope.cancel()

async def test_non_json_line_ignored(caplog):
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    class FakeStdout:
        async def __aiter__(self):
            yield "oops\n"
            yield '{"jsonrpc":"2.0","id":"ok","result":{}}\n'
    client.process.stdout = FakeStdout()

    caplog.set_level(logging.ERROR)
    recv = client.new_request_stream("ok")
    async with anyio.create_task_group() as tg:
        tg.start_soon(client._stdout_reader)
        assert (await recv.receive()).id == "ok"
        assert "json decode error" in caplog.text.lower()
        tg.cancel_scope.cancel()

###############################################################################
# Multi-message and CRLF tests                                                 #
###############################################################################

async def test_multiple_messages_in_one_chunk():
    """Two JSON-RPC messages in a single chunk get routed separately."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    msgs = [
        {"jsonrpc":"2.0","id":"x","result":{"a":1}},
        {"jsonrpc":"2.0","id":"y","result":{"b":2}}
    ]
    chunk = "\n".join(json.dumps(m) for m in msgs) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield chunk
    client.process.stdout = FakeStdout()

    recv_x = client.new_request_stream("x")
    recv_y = client.new_request_stream("y")
    async with anyio.create_task_group() as tg:
        tg.start_soon(client._stdout_reader)
        rx = await recv_x.receive()
        ry = await recv_y.receive()
        assert rx.result == {"a":1}
        assert ry.result == {"b":2}
        tg.cancel_scope.cancel()

async def test_crlf_line_endings():
    """CRLF (\r\n) terminated lines parse correctly."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    msg = {"jsonrpc":"2.0","id":"z","result":{}}
    chunk = json.dumps(msg) + "\r\n"

    class FakeStdout:
        async def __aiter__(self):
            yield chunk
    client.process.stdout = FakeStdout()

    recv = client.new_request_stream("z")
    async with anyio.create_task_group() as tg:
        tg.start_soon(client._stdout_reader)
        rz = await recv.receive()
        assert rz.id == "z"
        tg.cancel_scope.cancel()

###############################################################################
# Lightweight smoke for raw string send/receive helper                        #
###############################################################################

async def test_send_tool_execute_smoke():
    read_stream = AsyncMock()
    write_stream = AsyncMock()

    read_stream.receive.return_value = json.dumps({
        "jsonrpc": "2.0",
        "id": "t",
        "result": {"ok": True}
    })

    msg = json.dumps({
        "jsonrpc": "2.0",
        "id": "t",
        "method": "tools/exec",
        "params": {}
    })

    await write_stream.send(msg)
    response_raw = await read_stream.receive()
    response = json.loads(response_raw)
    assert response["id"] == "t" and response["result"]["ok"] is True
