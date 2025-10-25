# tests/mcp/messages/test_send_resources_unsubscribe.py
import pytest
import anyio

from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.resources.send_messages import (
    send_resources_subscribe,
    send_resources_unsubscribe,
)

pytestmark = [pytest.mark.asyncio]


async def test_send_resources_unsubscribe_success():
    """Test successful resource unsubscribe."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    test_uri = "file:///test/document.txt"

    async def mock_server():
        # Receive the unsubscribe request
        req = await write_receive.receive()
        assert req.method == "resources/unsubscribe"
        assert req.params == {"uri": test_uri}

        # Send success response
        response = JSONRPCMessage(id=req.id, result={})
        await read_send.send(response)

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        # Call unsubscribe
        result = await send_resources_unsubscribe(
            read_stream=read_receive, write_stream=write_send, uri=test_uri, timeout=2.0
        )

        assert result is True


async def test_send_resources_unsubscribe_error():
    """Test resource unsubscribe with error response."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    test_uri = "file:///nonexistent.txt"

    async def mock_server():
        # Receive the unsubscribe request
        req = await write_receive.receive()
        assert req.method == "resources/unsubscribe"

        # Send error response
        response = JSONRPCMessage(
            id=req.id, error={"code": -32004, "message": "Resource not found"}
        )
        await read_send.send(response)

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        # Call unsubscribe - should return False on error
        result = await send_resources_unsubscribe(
            read_stream=read_receive, write_stream=write_send, uri=test_uri, timeout=2.0
        )

        assert result is False


async def test_send_resources_unsubscribe_timeout():
    """Test resource unsubscribe with timeout."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    test_uri = "file:///slow.txt"

    async def mock_server():
        # Receive but don't respond
        await write_receive.receive()
        await anyio.sleep(5)  # Longer than timeout

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        # Call unsubscribe - should return False on timeout
        result = await send_resources_unsubscribe(
            read_stream=read_receive,
            write_stream=write_send,
            uri=test_uri,
            timeout=0.5,
        )

        assert result is False


async def test_subscribe_then_unsubscribe():
    """Test subscribing and then unsubscribing from a resource."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    test_uri = "file:///watched.txt"
    subscribed = False

    async def mock_server():
        nonlocal subscribed

        # Handle subscribe
        req1 = await write_receive.receive()
        if req1.method == "resources/subscribe":
            subscribed = True
            response = JSONRPCMessage(id=req1.id, result={})
            await read_send.send(response)

        # Handle unsubscribe
        req2 = await write_receive.receive()
        if req2.method == "resources/unsubscribe":
            assert req2.params["uri"] == test_uri
            assert subscribed  # Should be subscribed before unsubscribing
            subscribed = False
            response = JSONRPCMessage(id=req2.id, result={})
            await read_send.send(response)

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        # Subscribe first
        subscribe_result = await send_resources_subscribe(
            read_stream=read_receive, write_stream=write_send, uri=test_uri
        )
        assert subscribe_result is True
        assert subscribed is True

        # Then unsubscribe
        unsubscribe_result = await send_resources_unsubscribe(
            read_stream=read_receive, write_stream=write_send, uri=test_uri
        )
        assert unsubscribe_result is True
        assert subscribed is False


async def test_unsubscribe_with_special_uri():
    """Test unsubscribe with various URI formats."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Test various URI formats
    test_cases = [
        "file:///path/with spaces/doc.txt",
        "https://example.com/resource",
        "custom://protocol/resource",
        "file:///C:/Windows/path.txt",  # Windows path
    ]

    async def mock_server():
        for _ in test_cases:
            req = await write_receive.receive()
            assert req.method == "resources/unsubscribe"
            assert req.params["uri"] in test_cases

            response = JSONRPCMessage(id=req.id, result={})
            await read_send.send(response)

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        for uri in test_cases:
            result = await send_resources_unsubscribe(
                read_stream=read_receive, write_stream=write_send, uri=uri
            )
            assert result is True


async def test_unsubscribe_idempotency():
    """Test that unsubscribing multiple times is safe."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    test_uri = "file:///idempotent.txt"
    unsubscribe_count = 0

    async def mock_server():
        nonlocal unsubscribe_count

        while unsubscribe_count < 3:
            req = await write_receive.receive()
            assert req.method == "resources/unsubscribe"
            assert req.params["uri"] == test_uri
            unsubscribe_count += 1

            # Always return success, even if not subscribed
            response = JSONRPCMessage(id=req.id, result={})
            await read_send.send(response)

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        # Unsubscribe multiple times
        for _ in range(3):
            result = await send_resources_unsubscribe(
                read_stream=read_receive, write_stream=write_send, uri=test_uri
            )
            assert result is True

        assert unsubscribe_count == 3
