# tests/mcp/test_initialize.py
import pytest
import anyio

from chuk_mcp.protocol.types.errors import VersionMismatchError
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.initialize.send_messages import (
    send_initialize,
    send_initialized_notification,
    InitializeResult,
    SUPPORTED_PROTOCOL_VERSIONS,
    get_supported_versions,
    get_current_version,
    is_version_supported,
    validate_version_format,
)

# Only apply async marker to async functions individually


@pytest.mark.asyncio
async def test_send_initialize_success_latest_version():
    """Test successful initialization with latest protocol version"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Use the latest supported version
    latest_version = get_current_version()

    # Sample server response
    server_response = {
        "protocolVersion": latest_version,
        "capabilities": {
            "logging": {},
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "tools": {"listChanged": True},
        },
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    # Define server behavior
    async def server_task():
        try:
            # Get the initialize request
            req = await write_receive.receive()

            # Verify it's an initialize method
            assert req.method == "initialize"

            # Check protocol version is the latest
            assert req.params.get("protocolVersion") == latest_version

            # Verify client capabilities structure
            assert "capabilities" in req.params
            assert "clientInfo" in req.params

            # Send success response
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            # Check for initialized notification
            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"
            assert (
                not hasattr(notification, "id")
                or getattr(notification, "id", None) is None
            )  # Notifications must not have ID

        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    # Create task group and run both client and server
    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        # Client side request
        result = await send_initialize(
            read_stream=read_receive, write_stream=write_send
        )

    # Check if initialization was successful
    assert result is not None
    assert isinstance(result, InitializeResult)
    assert result.protocolVersion == latest_version
    assert result.serverInfo.name == "TestServer"


@pytest.mark.asyncio
async def test_send_initialize_version_mismatch():
    """Test initialization with protocol version error"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Test that version mismatch errors are properly detected
    result = None
    exception_caught = None

    async def server_task():
        try:
            req = await write_receive.receive()

            # Send a protocol version error
            response = JSONRPCMessage.create_error_response(
                id=req.id, code=-32602, message="Unsupported protocol version"
            )
            await read_send.send(response)

        except Exception:
            # Server errors are expected in this test
            pass

    async def client_task():
        nonlocal result, exception_caught
        try:
            result = await send_initialize(
                read_stream=read_receive, write_stream=write_send
            )
        except VersionMismatchError as e:
            exception_caught = e
        except Exception as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # Verify that we got a version mismatch error
    assert isinstance(exception_caught, VersionMismatchError)
    assert result is None


@pytest.mark.asyncio
async def test_send_initialize_server_error():
    """Test initialization with server error"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    result = None
    exception_caught = None

    async def server_task():
        try:
            req = await write_receive.receive()

            # Send server error
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message="Internal server error during initialization",
            )
            await read_send.send(response)

        except Exception:
            # Server errors are expected
            pass

    async def client_task():
        nonlocal result, exception_caught
        try:
            result = await send_initialize(
                read_stream=read_receive, write_stream=write_send
            )
        except Exception as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # For server errors, should raise exception (not return None)
    assert result is None, "Result should be None when exception is raised"
    assert exception_caught is not None, "Exception should be raised for server errors"
    assert "Internal server error" in str(exception_caught)


@pytest.mark.asyncio
async def test_send_initialize_timeout():
    """Test initialization timeout"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    result = None
    exception_caught = None

    async def server_task():
        try:
            # Get the request but don't respond (timeout scenario)
            _req = await write_receive.receive()
            # Don't send response - let it timeout
            await anyio.sleep(1.0)  # Wait longer than test timeout
        except Exception:
            pass  # Expected to be cancelled

    async def client_task():
        nonlocal result, exception_caught
        try:
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=0.5,  # Short timeout for test
            )
        except Exception as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # Should get a timeout error
    assert isinstance(exception_caught, TimeoutError)
    assert result is None


@pytest.mark.asyncio
async def test_send_initialize_version_negotiation():
    """Test server counter-proposes different but supported version"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Client proposes latest, server responds with older supported version
    supported_versions = get_supported_versions()
    client_proposed = supported_versions[0]  # Latest
    server_responded = (
        supported_versions[-1] if len(supported_versions) > 1 else supported_versions[0]
    )  # Oldest

    server_response = {
        "protocolVersion": server_responded,
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    async def server_task():
        try:
            req = await write_receive.receive()
            assert req.params.get("protocolVersion") == client_proposed

            # Server responds with different version
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"

        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        result = await send_initialize(
            read_stream=read_receive,
            write_stream=write_send,
            supported_versions=supported_versions,
        )

    assert result is not None
    assert result.protocolVersion == server_responded


@pytest.mark.asyncio
async def test_send_initialized_notification():
    """Test sending initialized notification independently"""
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Send notification
    await send_initialized_notification(write_send)

    # Verify notification was sent correctly
    notification = await write_receive.receive()
    assert notification.method == "notifications/initialized"
    assert (
        not hasattr(notification, "id") or getattr(notification, "id", None) is None
    )  # Notifications must not have ID
    assert notification.params == {}


# Synchronous tests - no async marker needed
def test_version_utility_functions():
    """Test version utility functions"""
    # Test get_supported_versions
    versions = get_supported_versions()
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert all(isinstance(v, str) for v in versions)

    # Test get_current_version
    current = get_current_version()
    assert isinstance(current, str)
    assert current in versions
    assert current == versions[0]  # Should be first (latest)

    # Test is_version_supported
    for version in versions:
        assert is_version_supported(version)

    assert not is_version_supported("1999-01-01")  # Unsupported version


def test_version_format_validation():
    """Test version format validation"""
    # Valid formats
    assert validate_version_format("2025-06-18")
    assert validate_version_format("2024-11-05")
    assert validate_version_format("1999-12-31")

    # Invalid formats
    assert not validate_version_format("2025-6-18")  # Single digit month
    assert not validate_version_format("25-06-18")  # Two digit year
    assert not validate_version_format("2025/06/18")  # Wrong separator
    assert not validate_version_format("2025-06-18T00")  # Extra content
    assert not validate_version_format("invalid")  # Not a date
    assert not validate_version_format("")  # Empty string


@pytest.mark.asyncio
@pytest.mark.parametrize("version", SUPPORTED_PROTOCOL_VERSIONS)
async def test_initialize_with_each_supported_version(version):
    """Parametrized test to ensure all supported versions work"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    server_response = {
        "protocolVersion": version,
        "capabilities": {"logging": {}},
        "serverInfo": {"name": f"Server-{version}", "version": "1.0.0"},
    }

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"

        except Exception as e:
            pytest.fail(f"Server task failed for version {version}: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        result = await send_initialize(
            read_stream=read_receive, write_stream=write_send, preferred_version=version
        )

    assert result is not None
    assert result.protocolVersion == version


@pytest.mark.asyncio
async def test_send_initialize_unsupported_server_version():
    """Test initialization when server responds with unsupported version"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Server responds with totally unsupported version
    server_response = {
        "protocolVersion": "1999-01-01",  # Unsupported version
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    result = None
    exception_caught = None

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        nonlocal result, exception_caught
        try:
            result = await send_initialize(
                read_stream=read_receive, write_stream=write_send
            )
        except VersionMismatchError as e:
            exception_caught = e
        except Exception as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # Should raise VersionMismatchError - covers lines 139-143
    assert isinstance(exception_caught, VersionMismatchError)
    assert result is None


@pytest.mark.asyncio
async def test_send_initialize_timeout_error_reraise():
    """Test that TimeoutError is re-raised correctly"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    exception_caught = None

    async def server_task():
        try:
            _req = await write_receive.receive()
            await anyio.sleep(10)  # Don't respond
        except Exception:
            pass

    async def client_task():
        nonlocal exception_caught
        try:
            await send_initialize(
                read_stream=read_receive, write_stream=write_send, timeout=0.1
            )
        except TimeoutError as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # Covers line 154 - TimeoutError re-raise
    assert isinstance(exception_caught, TimeoutError)


@pytest.mark.asyncio
async def test_send_initialize_generic_exception():
    """Test that generic exceptions are re-raised"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    exception_caught = None

    async def server_task():
        try:
            req = await write_receive.receive()
            # Send invalid response that will cause parsing error
            response = JSONRPCMessage(id=req.id, result="invalid_string_not_dict")
            await read_send.send(response)
        except Exception:
            pass

    async def client_task():
        nonlocal exception_caught
        try:
            await send_initialize(read_stream=read_receive, write_stream=write_send)
        except Exception as e:
            exception_caught = e

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(client_task)

    # Covers lines 174-180 - generic exception handling
    assert exception_caught is not None


@pytest.mark.asyncio
async def test_send_initialized_notification_error():
    """Test error handling in send_initialized_notification"""
    from unittest.mock import AsyncMock

    # Create a mock that raises an error
    write_stream = AsyncMock()
    write_stream.send.side_effect = Exception("Write failed")

    exception_caught = None
    try:
        await send_initialized_notification(write_stream)
    except Exception as e:
        exception_caught = e

    # Covers lines 205-207 - error handling in notification
    assert exception_caught is not None
    assert "Write failed" in str(exception_caught)


@pytest.mark.asyncio
async def test_send_initialize_with_client_tracking():
    """Test send_initialize_with_client_tracking sets protocol version"""
    from chuk_mcp.protocol.messages.initialize.send_messages import (
        send_initialize_with_client_tracking,
    )

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    latest_version = get_current_version()

    server_response = {
        "protocolVersion": latest_version,
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    # Create a mock client with set_protocol_version method
    class MockClient:
        def __init__(self):
            self.protocol_version = None

        def set_protocol_version(self, version):
            self.protocol_version = version

    client = MockClient()

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"
        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        result = await send_initialize_with_client_tracking(
            read_stream=read_receive, write_stream=write_send, client=client
        )

    # Verify client's protocol version was set
    assert result is not None
    assert client.protocol_version == latest_version


@pytest.mark.asyncio
async def test_send_initialize_with_client_tracking_no_client():
    """Test send_initialize_with_client_tracking without client"""
    from chuk_mcp.protocol.messages.initialize.send_messages import (
        send_initialize_with_client_tracking,
    )

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    latest_version = get_current_version()

    server_response = {
        "protocolVersion": latest_version,
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"
        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        # Call without client parameter
        result = await send_initialize_with_client_tracking(
            read_stream=read_receive, write_stream=write_send, client=None
        )

    assert result is not None
    assert result.protocolVersion == latest_version


@pytest.mark.asyncio
async def test_send_initialize_with_client_tracking_no_method():
    """Test send_initialize_with_client_tracking with client without set_protocol_version"""
    from chuk_mcp.protocol.messages.initialize.send_messages import (
        send_initialize_with_client_tracking,
    )

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    latest_version = get_current_version()

    server_response = {
        "protocolVersion": latest_version,
        "capabilities": {"logging": {}},
        "serverInfo": {"name": "TestServer", "version": "1.0.0"},
    }

    # Client without set_protocol_version method
    class MockClientNoMethod:
        pass

    client = MockClientNoMethod()

    async def server_task():
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage(id=req.id, result=server_response)
            await read_send.send(response)

            notification = await write_receive.receive()
            assert notification.method == "notifications/initialized"
        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)

        # Should not fail even without the method
        result = await send_initialize_with_client_tracking(
            read_stream=read_receive, write_stream=write_send, client=client
        )

    assert result is not None
    assert result.protocolVersion == latest_version
