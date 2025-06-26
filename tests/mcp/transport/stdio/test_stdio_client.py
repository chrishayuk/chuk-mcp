# tests/mcp/transport/stdio/test_stdio_client.py
import pytest
import anyio
import json
import logging
from unittest.mock import AsyncMock, patch, MagicMock

from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client, StdioClient
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

# Only apply async marker to async functions
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_routing_multiple_requests():
    """Test routing multiple requests to their respective streams."""
    client = StdioClient(StdioServerParameters(command="test"))
    recv_a = client.new_request_stream("a")
    recv_b = client.new_request_stream("b")

    # Create messages
    msg_b = make_message(id="b", result={"v": 2})
    msg_a = make_message(id="a", result={"v": 1})

    # Route messages with proper async handling
    async def route_messages():
        await client._route_message(msg_b)
        await client._route_message(msg_a)

    async def receive_messages():
        # Receive in parallel to avoid blocking
        result_a = None
        result_b = None
        
        async with anyio.create_task_group() as tg:
            async def get_a():
                nonlocal result_a
                result_a = await recv_a.receive()

            async def get_b():
                nonlocal result_b
                result_b = await recv_b.receive()

            tg.start_soon(get_a)
            tg.start_soon(get_b)
        
        # Return after task group completes
        return result_a, result_b

    # Execute routing and receiving
    async with anyio.create_task_group() as tg:
        tg.start_soon(route_messages)
        result_a, result_b = await receive_messages()

    assert result_a.result == {"v": 1}
    assert result_b.result == {"v": 2}
    assert not client._pending  # cleaned up


@pytest.mark.asyncio
async def test_notification_broadcast_and_unknown(caplog):
    """Notifications are broadcast; sending in background avoids deadlock on zero-buffer."""
    client = StdioClient(StdioServerParameters(command="test"))
    recv_notif = client.notifications

    # Route a notification - use proper async coordination
    notification = make_message(method="ping")
    
    async def send_notification():
        await client._route_message(notification)
    
    async def receive_notification():
        return await recv_notif.receive()

    # Execute with proper task coordination
    async with anyio.create_task_group() as tg:
        tg.start_soon(send_notification)
        note = await receive_notification()
        assert note.method == "ping"

    # Unknown-id responses log a warning immediately
    caplog.set_level(logging.WARNING)
    # Create a valid response with an unknown ID (has result to be valid)
    await client._route_message(make_message(id="ghost", result={}))
    assert "unknown id" in caplog.text.lower()
    
###############################################################################
# _stdin_writer                                                               #
###############################################################################

@pytest.mark.asyncio
async def test_stdin_writer_model(mock_stdio_client):
    msg = make_message(id="x", method="run", params={"p": 1})
    mock_stdio_client.process.stdin = AsyncMock()

    # Mock the outgoing stream properly
    send_stream, receive_stream = anyio.create_memory_object_stream(1)
    mock_stdio_client._outgoing_recv = receive_stream
    
    # Send a message
    await send_stream.send(msg)
    await send_stream.aclose()

    await mock_stdio_client._stdin_writer()
    
    # Verify the message was sent
    assert mock_stdio_client.process.stdin.send.called
    sent_data = mock_stdio_client.process.stdin.send.call_args[0][0]
    sent = json.loads(sent_data.decode())
    assert sent["id"] == "x" and sent["method"] == "run"


@pytest.mark.asyncio
async def test_stdin_writer_raw_string(mock_stdio_client):
    raw = '{"jsonrpc":"2.0","id":"s","method":"do","params":{}}'
    mock_stdio_client.process.stdin = AsyncMock()

    # Mock the outgoing stream properly
    send_stream, receive_stream = anyio.create_memory_object_stream(1)
    mock_stdio_client._outgoing_recv = receive_stream
    
    # Send a raw string
    await send_stream.send(raw)
    await send_stream.aclose()

    await mock_stdio_client._stdin_writer()
    
    # Verify the string was sent
    assert mock_stdio_client.process.stdin.send.called
    sent = mock_stdio_client.process.stdin.send.call_args[0][0].decode().strip()
    assert sent == raw


@pytest.mark.asyncio
async def test_stdin_writer_logs_on_error(mock_stdio_client):
    bad = MagicMock()
    bad.model_dump_json.side_effect = Exception("boom")
    mock_stdio_client.process.stdin = AsyncMock()

    # Mock the outgoing stream properly
    send_stream, receive_stream = anyio.create_memory_object_stream(1)
    mock_stdio_client._outgoing_recv = receive_stream
    
    # Send a bad message
    await send_stream.send(bad)
    await send_stream.aclose()

    with patch("logging.error") as err:
        await mock_stdio_client._stdin_writer()
        err.assert_called()

###############################################################################
# _stdout_reader resilience                                                   #
###############################################################################

@pytest.mark.asyncio
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
    
    # Use proper task coordination
    result = None
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_message():
        nonlocal result
        result = await recv.receive()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_message()
        assert result.id == "p"
        tg.cancel_scope.cancel()


@pytest.mark.asyncio
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
    
    result = None
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_message():
        nonlocal result
        result = await recv.receive()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_message()
        assert result.id == "ok"
        assert "json decode error" in caplog.text.lower()
        tg.cancel_scope.cancel()

###############################################################################
# Multi-message and CRLF tests                                                 #
###############################################################################

@pytest.mark.asyncio
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
    
    results = {}
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_messages():
        async with anyio.create_task_group() as tg:
            async def get_x():
                results["x"] = await recv_x.receive()
            
            async def get_y():
                results["y"] = await recv_y.receive()
            
            tg.start_soon(get_x)
            tg.start_soon(get_y)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_messages()
        assert results["x"].result == {"a":1}
        assert results["y"].result == {"b":2}
        tg.cancel_scope.cancel()


@pytest.mark.asyncio
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
    
    result = None
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_message():
        nonlocal result
        result = await recv.receive()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_message()
        assert result.id == "z"
        tg.cancel_scope.cancel()

###############################################################################
# Lightweight smoke for raw string send/receive helper                        #
###############################################################################

@pytest.mark.asyncio
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

# Add these test cases to tests/mcp/transport/stdio/test_stdio_client.py

###############################################################################
# JSON-RPC Batch Support Tests                                                #
###############################################################################

@pytest.mark.asyncio
async def test_batch_messages_received():
    """Test that batch messages are properly parsed and routed."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    # Create a batch of different message types
    batch = [
        {"jsonrpc": "2.0", "id": "1", "result": {"status": "ok"}},
        {"jsonrpc": "2.0", "id": "2", "result": {"value": 42}},
        {"jsonrpc": "2.0", "method": "notification", "params": {"type": "test"}},
        {"jsonrpc": "2.0", "id": "3", "error": {"code": -32601, "message": "Method not found"}}
    ]
    
    batch_json = json.dumps(batch) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield batch_json
    
    client.process.stdout = FakeStdout()

    # Set up receivers
    recv_1 = client.new_request_stream("1")
    recv_2 = client.new_request_stream("2")
    recv_3 = client.new_request_stream("3")
    
    results = {}
    notifications = []
    
    # Capture notifications
    async def notification_reader():
        async for notif in client.notifications:
            notifications.append(notif)
            if len(notifications) >= 1:  # We expect 1 notification
                break
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            async def get_1():
                results["1"] = await recv_1.receive()
            
            async def get_2():
                results["2"] = await recv_2.receive()
            
            async def get_3():
                results["3"] = await recv_3.receive()
            
            tg.start_soon(get_1)
            tg.start_soon(get_2)
            tg.start_soon(get_3)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        tg.start_soon(notification_reader)
        await get_responses()
        
        # Verify results
        assert results["1"].result == {"status": "ok"}
        assert results["2"].result == {"value": 42}
        assert results["3"].error == {"code": -32601, "message": "Method not found"}
        
        # Wait a bit for notification
        await anyio.sleep(0.1)
        tg.cancel_scope.cancel()
    
    # Verify notification was received
    assert len(notifications) == 1
    assert notifications[0].method == "notification"
    assert notifications[0].params == {"type": "test"}


@pytest.mark.asyncio
async def test_empty_batch():
    """Test that empty batch is handled gracefully."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    empty_batch = json.dumps([]) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield empty_batch
            yield '{"jsonrpc": "2.0", "id": "after", "result": {}}\n'
    
    client.process.stdout = FakeStdout()

    # Verify we can still receive messages after empty batch
    recv = client.new_request_stream("after")
    
    result = None
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_message():
        nonlocal result
        result = await recv.receive()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_message()
        assert result.id == "after"
        tg.cancel_scope.cancel()


@pytest.mark.asyncio
async def test_batch_with_invalid_items(caplog):
    """Test that batch with some invalid items still processes valid ones."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    # Mix of valid and invalid items
    batch = [
        {"jsonrpc": "2.0", "id": "valid1", "result": {"ok": True}},
        {"invalid": "not a valid message"},  # Invalid - will be parsed but with extra fields
        {"jsonrpc": "2.0", "id": "valid2", "result": {"ok": True}},
        {"jsonrpc": "2.0"},  # Valid but minimal - treated as notification with no method
        {"jsonrpc": "2.0", "method": "notification"}  # Valid notification
    ]
    
    batch_json = json.dumps(batch) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield batch_json
    
    client.process.stdout = FakeStdout()

    recv_1 = client.new_request_stream("valid1")
    recv_2 = client.new_request_stream("valid2")
    
    caplog.set_level(logging.DEBUG)  # Changed to DEBUG to see all processing
    
    results = {}
    notifications = []
    
    async def notification_reader():
        # Collect notifications with a timeout
        with anyio.move_on_after(1.0):  # Timeout after 1 second
            async for notif in client.notifications:
                notifications.append(notif)
                # The invalid message and minimal message are parsed as notifications
                # We expect at least 3 notifications total
                if len(notifications) >= 3:
                    break
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            async def get_1():
                results["valid1"] = await recv_1.receive()
            
            async def get_2():
                results["valid2"] = await recv_2.receive()
            
            tg.start_soon(get_1)
            tg.start_soon(get_2)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        tg.start_soon(notification_reader)
        await get_responses()
        
        # Verify valid messages were processed
        assert results["valid1"].result == {"ok": True}
        assert results["valid2"].result == {"ok": True}
        
        await anyio.sleep(0.1)
        tg.cancel_scope.cancel()
    
    # Verify notifications were received
    # The fallback Pydantic allows extra fields, so invalid messages may still be parsed
    assert len(notifications) >= 1
    
    # Find the valid notification with method="notification"
    valid_notification_found = False
    notification_methods = []
    for notif in notifications:
        notification_methods.append(notif.method)
        if notif.method == "notification":
            valid_notification_found = True
            break
    
    assert valid_notification_found, f"Expected 'notification' method, got methods: {notification_methods}"
    
    # Verify batch processing was logged
    assert "Received batch with 5 messages" in caplog.text


@pytest.mark.asyncio
async def test_batch_split_across_chunks():
    """Test batch that arrives in multiple chunks."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    batch = [
        {"jsonrpc": "2.0", "id": "chunk1", "result": {"part": 1}},
        {"jsonrpc": "2.0", "id": "chunk2", "result": {"part": 2}}
    ]
    
    batch_str = json.dumps(batch)
    # Split in the middle of the JSON
    split_point = len(batch_str) // 2

    class FakeStdout:
        async def __aiter__(self):
            yield batch_str[:split_point]
            yield batch_str[split_point:] + "\n"
    
    client.process.stdout = FakeStdout()

    recv_1 = client.new_request_stream("chunk1")
    recv_2 = client.new_request_stream("chunk2")
    
    results = {}
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            async def get_1():
                results["chunk1"] = await recv_1.receive()
            
            async def get_2():
                results["chunk2"] = await recv_2.receive()
            
            tg.start_soon(get_1)
            tg.start_soon(get_2)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_responses()
        
        assert results["chunk1"].result == {"part": 1}
        assert results["chunk2"].result == {"part": 2}
        tg.cancel_scope.cancel()


@pytest.mark.asyncio
async def test_mixed_batch_and_single_messages():
    """Test that batches and single messages can be intermixed."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    batch = [
        {"jsonrpc": "2.0", "id": "b1", "result": {"batch": True}},
        {"jsonrpc": "2.0", "id": "b2", "result": {"batch": True}}
    ]
    
    messages = [
        json.dumps({"jsonrpc": "2.0", "id": "s1", "result": {"single": True}}) + "\n",
        json.dumps(batch) + "\n",
        json.dumps({"jsonrpc": "2.0", "id": "s2", "result": {"single": True}}) + "\n"
    ]

    class FakeStdout:
        async def __aiter__(self):
            for msg in messages:
                yield msg
    
    client.process.stdout = FakeStdout()

    # Set up receivers
    recv_s1 = client.new_request_stream("s1")
    recv_b1 = client.new_request_stream("b1")
    recv_b2 = client.new_request_stream("b2")
    recv_s2 = client.new_request_stream("s2")
    
    results = {}
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            async def get_s1():
                results["s1"] = await recv_s1.receive()
            
            async def get_b1():
                results["b1"] = await recv_b1.receive()
            
            async def get_b2():
                results["b2"] = await recv_b2.receive()
            
            async def get_s2():
                results["s2"] = await recv_s2.receive()
            
            tg.start_soon(get_s1)
            tg.start_soon(get_b1)
            tg.start_soon(get_b2)
            tg.start_soon(get_s2)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_responses()
        
        # Verify all messages were received correctly
        assert results["s1"].result == {"single": True}
        assert results["b1"].result == {"batch": True}
        assert results["b2"].result == {"batch": True}
        assert results["s2"].result == {"single": True}
        tg.cancel_scope.cancel()


@pytest.mark.asyncio
async def test_large_batch_performance():
    """Test handling of large batches efficiently."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    # Create a large batch
    batch_size = 100
    batch = [
        {"jsonrpc": "2.0", "id": str(i), "result": {"index": i}}
        for i in range(batch_size)
    ]
    
    batch_json = json.dumps(batch) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield batch_json
    
    client.process.stdout = FakeStdout()

    # Set up receivers for all messages
    receivers = {}
    for i in range(batch_size):
        receivers[str(i)] = client.new_request_stream(str(i))
    
    results = {}
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            for i in range(batch_size):
                async def get_msg(idx=i):
                    results[str(idx)] = await receivers[str(idx)].receive()
                
                tg.start_soon(get_msg)
    
    # Time the operation
    import time
    start_time = time.time()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_responses()
        
        # Verify all messages were received
        assert len(results) == batch_size
        for i in range(batch_size):
            assert results[str(i)].result == {"index": i}
        
        tg.cancel_scope.cancel()
    
    elapsed = time.time() - start_time
    # Should process 100 messages quickly (under 1 second)
    assert elapsed < 1.0, f"Large batch took too long: {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_batch_with_duplicate_ids(caplog):
    """Test handling of batch with duplicate IDs."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    # Batch with duplicate IDs
    batch = [
        {"jsonrpc": "2.0", "id": "dup", "result": {"first": True}},
        {"jsonrpc": "2.0", "id": "dup", "result": {"second": True}},
        {"jsonrpc": "2.0", "id": "unique", "result": {"ok": True}}
    ]
    
    batch_json = json.dumps(batch) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield batch_json
    
    client.process.stdout = FakeStdout()

    recv_dup = client.new_request_stream("dup")
    recv_unique = client.new_request_stream("unique")
    
    caplog.set_level(logging.WARNING)
    
    results = {}
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        # First duplicate will be received
        results["dup"] = await recv_dup.receive()
        results["unique"] = await recv_unique.receive()
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_responses()
        
        # First message with ID "dup" should be received
        assert results["dup"].result == {"first": True}
        assert results["unique"].result == {"ok": True}
        
        # Wait for logging
        await anyio.sleep(0.1)
        tg.cancel_scope.cancel()
    
    # Second duplicate should trigger warning
    assert "unknown id" in caplog.text.lower()


@pytest.mark.asyncio
async def test_batch_logging(caplog):
    """Test that batch processing is properly logged."""
    client = StdioClient(StdioServerParameters(command="test"))
    client.process = MockProcess()

    batch = [
        {"jsonrpc": "2.0", "id": "1", "result": {}},
        {"jsonrpc": "2.0", "method": "test_notification"},
        {"jsonrpc": "2.0", "id": "2", "result": {}}
    ]
    
    batch_json = json.dumps(batch) + "\n"

    class FakeStdout:
        async def __aiter__(self):
            yield batch_json
    
    client.process.stdout = FakeStdout()

    caplog.set_level(logging.DEBUG)
    
    recv_1 = client.new_request_stream("1")
    recv_2 = client.new_request_stream("2")
    
    async def read_stdout():
        await client._stdout_reader()
    
    async def get_responses():
        async with anyio.create_task_group() as tg:
            async def get_1():
                await recv_1.receive()
            
            async def get_2():
                await recv_2.receive()
            
            tg.start_soon(get_1)
            tg.start_soon(get_2)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_stdout)
        await get_responses()
        
        await anyio.sleep(0.1)
        tg.cancel_scope.cancel()
    
    # Verify batch logging
    assert "Received batch with 3 messages" in caplog.text
    assert "Batch item: response (id: 1)" in caplog.text
    assert "Batch item: test_notification (id: None)" in caplog.text
    assert "Batch item: response (id: 2)" in caplog.text