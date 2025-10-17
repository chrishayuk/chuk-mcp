#!/usr/bin/env python3
"""
Comprehensive tests for stdio client to improve coverage.
"""

import json
import pytest
import anyio
import warnings
from unittest.mock import AsyncMock, MagicMock, Mock

from chuk_mcp.transports.stdio.stdio_client import (
    StdioClient,
    _supports_batch_processing,
)
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage


class TestStdioClientValidation:
    """Test input validation."""

    def test_empty_command(self):
        """Test that empty command raises ValueError."""
        with pytest.raises(ValueError, match="command must not be empty"):
            params = StdioParameters(command="")
            StdioClient(params)

    def test_invalid_args_type(self):
        """Test that invalid args type raises ValueError."""
        # Create a mock object that bypasses pydantic but fails our validation
        mock_params = Mock(spec=StdioParameters)
        mock_params.command = "test"
        mock_params.args = "not a list"  # Invalid type
        mock_params.env = None

        with pytest.raises(ValueError, match="arguments must be a list or tuple"):
            StdioClient(mock_params)


class TestMessageRouting:
    """Test message routing error scenarios."""

    @pytest.mark.asyncio
    async def test_route_message_broken_incoming(self):
        """Test routing when incoming stream is broken."""
        client = StdioClient(StdioParameters(command="test"))

        # Close the incoming receive stream (which causes BrokenResourceError on send)
        await client._incoming_recv.aclose()

        msg = JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": "test"})

        # Should not raise - just returns
        await client._route_message(msg)

    @pytest.mark.asyncio
    async def test_route_notification_would_block(self):
        """Test notification routing when stream would block."""
        client = StdioClient(StdioParameters(command="test"))

        # Fill up the notification stream
        for _ in range(100):
            try:
                client._notify_send.send_nowait(
                    JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": "fill"})
                )
            except anyio.WouldBlock:
                break

        # Now send another notification - should not block
        notification = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "method": "test_notification"}
        )
        await client._route_message(notification)

    @pytest.mark.asyncio
    async def test_route_notification_broken_stream(self):
        """Test notification routing when notification stream is broken."""
        client = StdioClient(StdioParameters(command="test"))

        # Close notification receive stream (causes BrokenResourceError)
        await client.notifications.aclose()

        notification = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "method": "test_notification"}
        )

        # Should not raise
        await client._route_message(notification)

    @pytest.mark.asyncio
    async def test_route_response_broken_legacy_stream(self):
        """Test routing response when legacy stream is broken."""
        client = StdioClient(StdioParameters(command="test"))

        # Create and close legacy stream (close receiver to cause BrokenResourceError)
        recv_stream = client.new_request_stream("test123")
        await recv_stream.aclose()

        response = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "id": "test123", "result": {"status": "ok"}}
        )

        # Should not raise
        await client._route_message(response)

    @pytest.mark.asyncio
    async def test_route_unknown_id(self):
        """Test routing message with unknown ID."""
        client = StdioClient(StdioParameters(command="test"))

        response = JSONRPCMessage.model_validate(
            {"jsonrpc": "2.0", "id": "unknown_id", "result": {}}
        )

        # Should log warning but not raise
        await client._route_message(response)


class TestStdoutReader:
    """Test stdout reader error scenarios."""

    @pytest.mark.asyncio
    async def test_stdout_reader_bytes_chunk(self):
        """Test stdout reader with bytes chunks."""
        client = StdioClient(StdioParameters(command="test"))

        # Mock process with bytes stdout
        mock_proc = MagicMock()
        message = {"jsonrpc": "2.0", "method": "test"}

        async def byte_generator():
            yield json.dumps(message).encode("utf-8") + b"\n"

        mock_proc.stdout = byte_generator()
        client.process = mock_proc

        # Start reader briefly in a task group
        async with anyio.create_task_group() as tg:
            tg.start_soon(client._stdout_reader)
            await anyio.sleep(0.1)
            tg.cancel_scope.cancel()

    @pytest.mark.asyncio
    async def test_stdout_reader_string_chunk(self):
        """Test stdout reader with string chunks."""
        client = StdioClient(StdioParameters(command="test"))

        # Mock process with string stdout
        mock_proc = MagicMock()
        message = {"jsonrpc": "2.0", "method": "test"}

        async def string_generator():
            yield json.dumps(message) + "\n"

        mock_proc.stdout = string_generator()
        client.process = mock_proc

        # Start reader briefly in a task group
        async with anyio.create_task_group() as tg:
            tg.start_soon(client._stdout_reader)
            await anyio.sleep(0.1)
            tg.cancel_scope.cancel()

    @pytest.mark.asyncio
    async def test_stdout_reader_empty_lines(self):
        """Test stdout reader skips empty lines."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()

        async def generator_with_empty():
            yield "\n\n  \n"
            yield json.dumps({"jsonrpc": "2.0", "method": "test"}) + "\n"

        mock_proc.stdout = generator_with_empty()
        client.process = mock_proc

        async with anyio.create_task_group() as tg:
            tg.start_soon(client._stdout_reader)
            await anyio.sleep(0.1)
            tg.cancel_scope.cancel()

    @pytest.mark.asyncio
    async def test_stdout_reader_json_decode_error(self):
        """Test stdout reader handles JSON decode errors."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()

        async def bad_json_generator():
            yield "not valid json\n"
            yield json.dumps({"jsonrpc": "2.0", "method": "test"}) + "\n"

        mock_proc.stdout = bad_json_generator()
        client.process = mock_proc

        async with anyio.create_task_group() as tg:
            tg.start_soon(client._stdout_reader)
            await anyio.sleep(0.1)
            tg.cancel_scope.cancel()

    @pytest.mark.asyncio
    async def test_stdout_reader_processing_error(self):
        """Test stdout reader handles message processing errors."""
        client = StdioClient(StdioParameters(command="test"))

        # Mock _process_message_data to raise error
        async def error_processor(data):
            raise Exception("Processing error")

        client._process_message_data = error_processor  # type: ignore[method-assign]

        mock_proc = MagicMock()

        async def generator():
            yield json.dumps({"jsonrpc": "2.0", "method": "test"}) + "\n"

        mock_proc.stdout = generator()
        client.process = mock_proc

        async with anyio.create_task_group() as tg:
            tg.start_soon(client._stdout_reader)
            await anyio.sleep(0.1)
            tg.cancel_scope.cancel()

    @pytest.mark.asyncio
    async def test_stdout_reader_general_error(self):
        """Test stdout reader handles general errors."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()

        async def error_generator():
            yield json.dumps({"jsonrpc": "2.0", "method": "test"}) + "\n"
            raise Exception("stdout error")

        mock_proc.stdout = error_generator()
        client.process = mock_proc

        # Should not raise
        await client._stdout_reader()


class TestBatchProcessing:
    """Test batch processing scenarios."""

    @pytest.mark.asyncio
    async def test_process_batch_rejection(self):
        """Test batch message rejection in non-batching version."""
        client = StdioClient(StdioParameters(command="test"))

        # Set to version that doesn't support batching
        client.set_protocol_version("2025-06-18")

        # Mock error response sending
        client._send_error_response = AsyncMock()

        # Try to process a batch (should be rejected)
        batch_data = [
            {"jsonrpc": "2.0", "method": "test1"},
            {"jsonrpc": "2.0", "method": "test2"},
        ]

        await client._process_message_data(batch_data)

        # Verify error response was sent
        assert client._send_error_response.called

    @pytest.mark.asyncio
    async def test_process_batch_enabled(self):
        """Test batch processing when enabled."""
        client = StdioClient(StdioParameters(command="test"))

        # Set to version that supports batching
        client.set_protocol_version("2025-03-26")

        batch_data = [
            {"jsonrpc": "2.0", "method": "test1", "id": "1"},
            {"jsonrpc": "2.0", "method": "test2", "id": "2"},
        ]

        await client._process_message_data(batch_data)

        # Messages should be routed

    @pytest.mark.asyncio
    async def test_process_batch_item_error(self):
        """Test batch processing with invalid items."""
        client = StdioClient(StdioParameters(command="test"))

        # Enable batching
        client.set_protocol_version("2025-03-26")

        batch_data = [
            {"jsonrpc": "2.0", "method": "test1"},
            {"invalid": "message"},  # Invalid message
        ]

        # Should not raise - errors are logged
        await client._process_message_data(batch_data)

    @pytest.mark.asyncio
    async def test_process_single_message(self):
        """Test processing single message."""
        client = StdioClient(StdioParameters(command="test"))

        message_data = {"jsonrpc": "2.0", "method": "test", "id": "123"}

        await client._process_message_data(message_data)

    @pytest.mark.asyncio
    async def test_process_single_message_error(self):
        """Test processing single message with error."""
        client = StdioClient(StdioParameters(command="test"))

        # Invalid message data
        message_data = {"invalid": "message"}

        # Should not raise - error is logged
        await client._process_message_data(message_data)


class TestSendErrorResponse:
    """Test sending error responses."""

    @pytest.mark.asyncio
    async def test_send_error_response_success(self):
        """Test successfully sending error response."""
        client = StdioClient(StdioParameters(command="test"))

        # Mock process
        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request"},
        }

        await client._send_error_response(error_response)

        assert mock_proc.stdin.send.called

    @pytest.mark.asyncio
    async def test_send_error_response_no_process(self):
        """Test sending error response when process is None."""
        client = StdioClient(StdioParameters(command="test"))

        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
        }

        # Should not raise
        await client._send_error_response(error_response)

    @pytest.mark.asyncio
    async def test_send_error_response_send_failure(self):
        """Test handling failure when sending error response."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        mock_proc.stdin.send.side_effect = Exception("Send failed")
        client.process = mock_proc

        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
        }

        # Should not raise
        await client._send_error_response(error_response)


class TestStdinWriter:
    """Test stdin writer scenarios."""

    @pytest.mark.asyncio
    async def test_stdin_writer_raw_string(self):
        """Test stdin writer with raw string message."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        # Send raw JSON string
        json_str = json.dumps({"jsonrpc": "2.0", "method": "test"})
        await send_stream.send(json_str)
        await send_stream.aclose()

        await client._stdin_writer()

        assert mock_proc.stdin.send.called

    @pytest.mark.asyncio
    async def test_stdin_writer_pydantic_with_dump(self):
        """Test stdin writer with pydantic model (model_dump only)."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        # Mock message with only model_dump
        mock_msg = MagicMock()
        del mock_msg.model_dump_json  # Remove model_dump_json
        mock_msg.model_dump.return_value = {"jsonrpc": "2.0", "method": "test"}
        mock_msg.method = "test"
        mock_msg.id = "123"

        await send_stream.send(mock_msg)
        await send_stream.aclose()

        await client._stdin_writer()

        assert mock_proc.stdin.send.called

    @pytest.mark.asyncio
    async def test_stdin_writer_plain_dict(self):
        """Test stdin writer with plain dict."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        await send_stream.send({"jsonrpc": "2.0", "method": "test"})
        await send_stream.aclose()

        await client._stdin_writer()

        assert mock_proc.stdin.send.called

    @pytest.mark.asyncio
    async def test_stdin_writer_other_object(self):
        """Test stdin writer with other object type."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        # Send a simple object
        class SimpleObj:
            pass

        # This will fail serialization but should be handled
        await send_stream.send(SimpleObj())
        await send_stream.aclose()

        # Should not raise
        await client._stdin_writer()

    @pytest.mark.asyncio
    async def test_stdin_writer_dict_with_method(self):
        """Test logging for dict with method field."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        await send_stream.send({"jsonrpc": "2.0", "method": "test", "id": "123"})
        await send_stream.aclose()

        await client._stdin_writer()

        assert mock_proc.stdin.send.called

    @pytest.mark.asyncio
    async def test_stdin_writer_general_error(self):
        """Test stdin writer handles general errors."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        mock_proc.stdin.send.side_effect = Exception("General error")
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        await send_stream.send({"jsonrpc": "2.0", "method": "test"})
        await send_stream.aclose()

        # Should not raise
        await client._stdin_writer()

    @pytest.mark.asyncio
    async def test_stdin_writer_closes_stdin(self):
        """Test that stdin writer closes stdin at end."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.stdin = AsyncMock()
        client.process = mock_proc

        send_stream, receive_stream = anyio.create_memory_object_stream(1)
        client._outgoing_recv = receive_stream

        await send_stream.aclose()

        await client._stdin_writer()

        assert mock_proc.stdin.aclose.called


class TestSendJson:
    """Test send_json method."""

    @pytest.mark.asyncio
    async def test_send_json_broken_stream(self):
        """Test send_json when outgoing stream is closed."""
        client = StdioClient(StdioParameters(command="test"))

        # Close outgoing receive stream to cause BrokenResourceError
        await client._outgoing_recv.aclose()

        msg = JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": "test"})

        # Should not raise - logs warning
        await client.send_json(msg)


class TestProcessTermination:
    """Test process termination scenarios."""

    @pytest.mark.asyncio
    async def test_terminate_process_no_process(self):
        """Test termination when process is None."""
        client = StdioClient(StdioParameters(command="test"))

        # Should not raise
        await client._terminate_process()

    @pytest.mark.asyncio
    async def test_terminate_process_graceful(self):
        """Test graceful process termination."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)
        client.process = mock_proc

        await client._terminate_process()

        assert mock_proc.terminate.called
        assert mock_proc.wait.called

    @pytest.mark.asyncio
    async def test_terminate_process_timeout_then_kill(self):
        """Test process termination with timeout then kill."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate = MagicMock()
        mock_proc.kill = MagicMock()

        # First wait times out, second wait succeeds
        wait_count = [0]

        async def wait_with_timeout():
            wait_count[0] += 1
            if wait_count[0] == 1:
                # First wait (after terminate) - timeout
                await anyio.sleep(2.0)
            else:
                # Second wait (after kill) - success
                return 0

        mock_proc.wait = wait_with_timeout
        client.process = mock_proc

        await client._terminate_process()

        assert mock_proc.terminate.called
        assert mock_proc.kill.called

    @pytest.mark.asyncio
    async def test_terminate_process_kill_timeout(self):
        """Test process termination when even kill times out."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate = MagicMock()
        mock_proc.kill = MagicMock()

        async def always_timeout():
            await anyio.sleep(2.0)

        mock_proc.wait = always_timeout
        client.process = mock_proc

        # Should not raise
        await client._terminate_process()

        assert mock_proc.terminate.called
        assert mock_proc.kill.called

    @pytest.mark.asyncio
    async def test_terminate_process_error(self):
        """Test error during process termination."""
        client = StdioClient(StdioParameters(command="test"))

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate.side_effect = Exception("Termination error")
        client.process = mock_proc

        # Should not raise
        await client._terminate_process()


class TestDeprecatedFunction:
    """Test deprecated function."""

    def test_supports_batch_processing_warning(self):
        """Test that deprecated function issues warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            result = _supports_batch_processing("2025-03-26")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert result is True

    def test_supports_batch_processing_none(self):
        """Test deprecated function with None."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            result = _supports_batch_processing(None)
            assert result is True


class TestClientInit:
    """Test client initialization details."""

    def test_client_init_with_empty_command_in_params(self):
        """Test client init validates empty command."""
        # This should be caught during StdioParameters creation
        with pytest.raises(ValueError):
            params = StdioParameters(command="")
            StdioClient(params)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
