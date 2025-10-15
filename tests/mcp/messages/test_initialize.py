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

    # For server errors, should return None (no exception raised)
    assert result is None
    assert exception_caught is None


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
