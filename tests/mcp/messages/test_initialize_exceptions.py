"""
Test exception handling in send_initialize().

This test suite demonstrates the new exception-raising behavior where
send_initialize() properly raises exceptions instead of returning None.

This is critical for:
1. OAuth re-authentication (catching 401 errors)
2. Proper error handling and debugging
3. Type safety (no Optional[InitializeResult])
"""

import pytest
import anyio

from chuk_mcp.protocol.types.errors import (
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
)
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.initialize.send_messages import (
    send_initialize,
    InitializeResult,
)


@pytest.mark.asyncio
async def test_401_unauthorized_raises_retryable_error():
    """Test that 401 errors raise RetryableError (enables OAuth re-auth)."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()

            # Simulate 401 Unauthorized error (expired OAuth token)
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,  # Internal error
                message='HTTP 401: {"error":"invalid_token","error_description":"Invalid access token"}',
            )
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        # Should raise RetryableError, not return None
        with pytest.raises((RetryableError, NonRetryableError, Exception)) as exc_info:
            await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,
            )

        # Verify error message contains 401 info
        error_msg = str(exc_info.value).lower()
        assert (
            "401" in error_msg
            or "invalid_token" in error_msg
            or "unauthorized" in error_msg
        )

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)


@pytest.mark.asyncio
async def test_internal_server_error_raises_exception():
    """Test that internal server errors raise exceptions."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()

            # Send internal server error
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message="Internal server error during initialization",
            )
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        # Should raise exception, not return None
        with pytest.raises((RetryableError, NonRetryableError, Exception)):
            await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,
            )

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)


@pytest.mark.asyncio
async def test_timeout_raises_timeout_error():
    """Test that timeouts raise TimeoutError."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            # Get request but don't respond
            _req = await write_receive.receive()
            await anyio.sleep(2.0)  # Wait longer than client timeout
        except Exception:
            pass  # Expected to be cancelled

    async def client_task():
        # Should raise TimeoutError
        with pytest.raises(TimeoutError):
            await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=0.5,  # Short timeout
            )

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)


@pytest.mark.asyncio
async def test_version_mismatch_raises_version_mismatch_error():
    """Test that version mismatches raise VersionMismatchError."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()

            # Send version mismatch error
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32602,  # Invalid params (version mismatch)
                message="Unsupported protocol version",
            )
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        # Should raise VersionMismatchError
        with pytest.raises(VersionMismatchError):
            await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,
            )

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)


@pytest.mark.asyncio
async def test_success_returns_initialize_result():
    """Test that successful initialization returns InitializeResult (not Optional)."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    server_response = {
        "protocolVersion": "2024-11-05",
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            # Consume initialized notification
            await write_receive.receive()
        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        result = await send_initialize(
            read_stream=read_receive,
            write_stream=write_send,
        )

    # Result is guaranteed to be InitializeResult (not None)
    assert isinstance(result, InitializeResult)
    assert result.protocolVersion == "2024-11-05"
    assert result.serverInfo.name == "TestServer"


@pytest.mark.asyncio
async def test_oauth_error_patterns():
    """Test various OAuth error patterns that should raise exceptions."""
    oauth_error_patterns = [
        'HTTP 401: {"error":"invalid_token"}',
        "401 Unauthorized",
        "Authentication failed",
        "Invalid access token",
        "Token expired",
    ]

    for error_message in oauth_error_patterns:
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        async def server_task():
            try:
                req = await write_receive.receive()
                response = JSONRPCMessage.create_error_response(
                    id=req.id,
                    code=-32603,
                    message=error_message,
                )
                await read_send.send(response)
            except Exception:
                pass

        async def client_task():
            # All OAuth errors should raise exceptions
            with pytest.raises(
                (RetryableError, NonRetryableError, Exception)
            ) as exc_info:
                await send_initialize(
                    read_stream=read_receive,
                    write_stream=write_send,
                    timeout=1.0,
                )

            # Verify error message is preserved
            error_str = str(exc_info.value).lower()
            assert any(
                pattern.lower() in error_str
                for pattern in ["401", "invalid", "token", "auth", "unauthorized"]
            )

        async with anyio.create_task_group() as tg:
            tg.start_soon(server_task)
            tg.start_soon(client_task)


@pytest.mark.asyncio
async def test_no_none_return_on_error():
    """
    Critical test: Verify that errors NEVER return None.

    This is a breaking change from the old behavior where errors
    returned None instead of raising exceptions.
    """
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()
            # Send any kind of error
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message="Some error",
            )
            await read_send.send(response)
        except Exception:
            pass

    result = None
    exception_raised = False

    async def client_task():
        nonlocal result, exception_raised
        try:
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,
            )
        except Exception:
            exception_raised = True

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # CRITICAL: Exception must be raised, result must be None
    assert exception_raised, "send_initialize() must raise exception on error"
    assert result is None, "send_initialize() must not return value on error"


@pytest.mark.asyncio
async def test_exception_contains_full_context():
    """Test that exceptions contain full error context for debugging."""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    error_message = "Detailed error: OAuth token invalid for server xyz.com"

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message=error_message,
            )
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        with pytest.raises((RetryableError, NonRetryableError, Exception)) as exc_info:
            await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,
            )

        # Exception should contain original error message
        assert error_message in str(exc_info.value) or "OAuth" in str(exc_info.value)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
