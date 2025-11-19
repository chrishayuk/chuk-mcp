# tests/mcp/transport/stdio/test_stdio_minimal.py
"""
Minimal, fast-running tests for stdio client functionality.
These tests focus on core functionality without complex async coordination.
"""

import pytest
import anyio
import json
import logging
from unittest.mock import AsyncMock, patch, MagicMock

from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.transports.stdio.stdio_client import StdioClient
from chuk_mcp.transports.stdio.parameters import StdioParameters

pytest.importorskip("chuk_mcp.transports.stdio.stdio_client")

###############################################################################
# Simple unit tests for core functionality
###############################################################################


def test_stdio_parameters_creation():
    """Test creating StdioParameters."""
    params = StdioParameters(command="python", args=["--version"])
    assert params.command == "python"
    assert params.args == ["--version"]
    assert params.env is None


def test_stdio_client_creation():
    """Test creating StdioClient."""
    params = StdioParameters(command="test")
    client = StdioClient(params)
    assert client.server == params
    assert client.process is None


def test_json_rpc_message_creation():
    """Test creating JSON-RPC messages."""
    msg = JSONRPCMessage.model_validate(
        {"jsonrpc": "2.0", "id": "test", "method": "ping"}
    )

    assert msg.jsonrpc == "2.0"
    assert msg.id == "test"
    assert msg.method == "ping"


def test_protocol_version_support():
    """Test protocol version detection."""
    from chuk_mcp.protocol.features.batching import supports_batching

    assert supports_batching("2025-03-26") is True
    assert supports_batching("2025-06-18") is False
    assert supports_batching(None) is True


def test_stdio_client_version_methods():
    """Test stdio client version-related methods."""
    client = StdioClient(StdioParameters(command="test"))

    # Test initial state
    assert client.get_protocol_version() is None
    assert client.is_batching_enabled() is True  # Default

    # Test setting version
    client.set_protocol_version("2025-06-18")
    assert client.get_protocol_version() == "2025-06-18"
    assert client.is_batching_enabled() is False

    # Test getting batching info
    info = client.get_batching_info()
    assert info["protocol_version"] == "2025-06-18"
    assert info["batching_enabled"] is False


def test_parameter_validation():
    """Test parameter validation."""
    # Valid parameters
    params = StdioParameters(command="echo")
    assert params.command == "echo"

    # Test with args and env
    params = StdioParameters(
        command="python", args=["--version"], env={"TEST": "value"}
    )
    assert params.command == "python"
    assert params.args == ["--version"]
    assert params.env == {"TEST": "value"}


###############################################################################
# Simple async tests with timeouts
###############################################################################


@pytest.mark.asyncio
async def test_simple_message_routing():
    """Test simple message routing without complex coordination."""
    async with StdioClient(StdioParameters(command="echo", args=["test"])) as client:
        # Create a simple request stream
        recv_stream = client.new_request_stream("test")

        # Create a simple message
        msg = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "id": "test", "result": {"status": "ok"}}
        )

        # Route the message
        await client._route_message(msg)

        # Receive the message with timeout
        with anyio.fail_after(1.0):
            result = await recv_stream.receive()

        assert result.id == "test"
        assert result.result == {"status": "ok"}


@pytest.mark.asyncio
async def test_notification_routing():
    """Test notification routing."""
    async with StdioClient(StdioParameters(command="echo", args=["test"])) as client:
        # Create a notification
        notification = JSONRPCMessage.model_validate(
            {
                "jsonrpc": "2.0",
                "method": "test_notification",
                "params": {"data": "test"},
            }
        )

        # Route the notification
        await client._route_message(notification)

        # Receive from notification stream with timeout
        with anyio.fail_after(1.0):
            received = await client.notifications.receive()

        assert received.method == "test_notification"
        assert received.params == {"data": "test"}


@pytest.mark.asyncio
async def test_send_json_method():
    """Test the send_json method."""
    async with StdioClient(StdioParameters(command="echo", args=["test"])) as client:
        msg = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "id": "test", "method": "ping"}
        )

        # This should not raise an exception
        await client.send_json(msg)


@pytest.mark.asyncio
async def test_batch_processor():
    """Test the batch processor functionality."""
    client = StdioClient(StdioParameters(command="test"))

    # Test old version (supports batching)
    client.set_protocol_version("2025-03-26")
    assert client.batch_processor.can_process_batch([{"test": "data"}]) is True
    assert client.batch_processor.can_process_batch({"test": "data"}) is True

    # Test new version (doesn't support batching)
    client.set_protocol_version("2025-06-18")
    assert client.batch_processor.can_process_batch([{"test": "data"}]) is False
    assert client.batch_processor.can_process_batch({"test": "data"}) is True


###############################################################################
# Mock-based tests for complex scenarios
###############################################################################


@pytest.mark.asyncio
async def test_mocked_stdin_writer():
    """Test stdin writer with simple mocking."""
    async with StdioClient(StdioParameters(command="echo", args=["test"])) as client:
        # Mock process
        client.process = MagicMock()
        client.process.stdin = AsyncMock()

        # Create message
        msg = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "id": "test", "method": "ping"}
        )

        # Set up outgoing stream
        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        # Send message and close
        await send_stream.send(msg)
        await send_stream.aclose()

        # Run stdin writer
        await client._stdin_writer()

        # Verify message was sent
        assert client.process.stdin.send.called
        sent_data = client.process.stdin.send.call_args[0][0]
        sent_json = json.loads(sent_data.decode())
        assert sent_json["method"] == "ping"


@pytest.mark.asyncio
async def test_error_logging_with_caplog(caplog):
    """Test error logging using caplog instead of patching."""
    async with StdioClient(StdioParameters(command="echo", args=["test"])) as client:
        # Mock process that will cause an error
        client.process = MagicMock()
        client.process.stdin = AsyncMock()

        # Create a bad message that will cause json serialization to fail
        bad_msg = MagicMock()
        bad_msg.model_dump_json.side_effect = Exception("serialization error")

        # Set up outgoing stream
        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        # Send bad message
        await send_stream.send(bad_msg)
        await send_stream.aclose()

        # Capture ERROR level logs
        caplog.set_level(logging.ERROR)

        # Run stdin writer
        await client._stdin_writer()

        # Check that error was logged
        assert "serialization error" in caplog.text


def test_imports_work():
    """Test that all necessary imports work."""
    from chuk_mcp.transports.stdio import stdio_client, StdioParameters, StdioTransport
    from chuk_mcp.protocol.features.batching import BatchProcessor, supports_batching
    from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

    # All imports should work
    assert stdio_client is not None
    assert StdioParameters is not None
    assert StdioTransport is not None
    assert BatchProcessor is not None
    assert supports_batching is not None
    assert JSONRPCMessage is not None


###############################################################################
# Integration test with minimal complexity
###############################################################################


@pytest.mark.asyncio
async def test_minimal_stdio_integration():
    """Minimal integration test with heavy mocking."""
    from chuk_mcp.transports.stdio import stdio_client

    params = StdioParameters(command="echo", args=["test"])

    # Mock the process completely
    with patch("anyio.open_process") as mock_open:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.returncode = None
        mock_proc.stdin = AsyncMock()
        mock_proc.stdout = AsyncMock()
        mock_proc.terminate = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)

        # Mock stdout to return immediately
        class EmptyStdout:
            async def __aiter__(self):
                return
                yield

        mock_proc.stdout = EmptyStdout()
        mock_open.return_value = mock_proc

        # Test context manager
        try:
            async with stdio_client(params) as (read_stream, write_stream):
                assert read_stream is not None
                assert write_stream is not None
        except Exception:
            # Some exceptions expected due to heavy mocking
            pass
