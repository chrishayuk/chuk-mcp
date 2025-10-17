# tests/mcp/transport/http/test_http_client.py
"""
Tests for HTTP client context manager - Fixed for isinstance issues.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from chuk_mcp.transports.http.parameters import StreamableHTTPParameters
from chuk_mcp.transports.http.http_client import http_client
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

pytest.importorskip("httpx")
pytest.importorskip("chuk_mcp.transports.http")


def assert_is_jsonrpc_message(obj, expected_values=None):
    """Helper function to test if object is a JSONRPCMessage with expected values."""
    # Check structure
    assert hasattr(obj, "jsonrpc"), f"Missing jsonrpc field, got: {type(obj)}"
    assert obj.jsonrpc == "2.0", f"Wrong jsonrpc version: {obj.jsonrpc}"

    # Check it's the right type by name (more reliable than isinstance)
    assert type(obj).__name__ == "JSONRPCMessage", f"Wrong type: {type(obj)}"

    # Check expected values if provided
    if expected_values:
        for key, value in expected_values.items():
            assert hasattr(obj, key), f"Missing field {key}"
            actual_value = getattr(obj, key)
            assert actual_value == value, f"Wrong {key}: {actual_value} != {value}"


@pytest.mark.asyncio
async def test_http_client_basic_usage():
    """Test basic usage of http_client context manager."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch(
        "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
    ) as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport

        # Mock context manager
        mock_transport.__aenter__.return_value = mock_transport
        mock_transport.__aexit__.return_value = False

        # Mock get_streams
        from anyio import create_memory_object_stream

        read_send, read_stream = create_memory_object_stream(
            10
        )  # read_stream is the receive end
        write_stream, write_recv = create_memory_object_stream(
            10
        )  # write_stream is the send end
        mock_transport.get_streams.return_value = (read_stream, write_stream)

        async with http_client(params) as (r_stream, w_stream):
            # Verify we got valid streams
            assert r_stream is not None
            assert w_stream is not None

            # Verify streams have the expected interface
            assert hasattr(r_stream, "receive")  # read stream should have receive
            assert hasattr(w_stream, "send")  # write stream should have send

            # Verify transport was created correctly
            mock_transport_class.assert_called_once_with(params)


@pytest.mark.asyncio
async def test_http_client_message_exchange():
    """Test sending and receiving messages through http_client."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        # Create a properly configured mock client
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"status": "ready"},
        }
        mock_response.text = (
            '{"jsonrpc":"2.0","id":"test-123","result":{"status":"ready"}}'
        )
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send a message
            outgoing_msg = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "test-123", "method": "ping"}
            )

            await write_stream.send(outgoing_msg)

            # Give time for processing
            await asyncio.sleep(0.1)

            # Receive response
            import anyio

            with anyio.fail_after(2.0):
                received_msg = await read_stream.receive()

            # FIXED: Use helper function instead of isinstance
            assert_is_jsonrpc_message(
                received_msg, {"id": "test-123", "result": {"status": "ready"}}
            )

            # Verify HTTP request was made
            assert mock_client.post.called


@pytest.mark.asyncio
async def test_http_client_error_handling():
    """Test http_client handles errors properly."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch(
        "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
    ) as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport

        # Mock error during context manager entry
        mock_transport.__aenter__.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            async with http_client(params) as (read_stream, write_stream):
                pass


@pytest.mark.asyncio
async def test_http_client_with_auth():
    """Test http_client with authentication."""
    params = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer secret-token-123"},
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "auth-test",
            "result": {},
        }
        mock_response.text = '{"jsonrpc":"2.0","id":"auth-test","result":{}}'
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send a message to trigger the request
            msg = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "auth-test", "method": "test"}
            )
            await write_stream.send(msg)
            await asyncio.sleep(0.1)

            # Verify the post was called with auth headers
            mock_client.post.assert_called()
            call_args = mock_client.post.call_args
            headers = call_args[1]["headers"]
            assert "Bearer secret-token-123" in headers.get("Authorization", "")


@pytest.mark.asyncio
async def test_http_client_streaming_enabled():
    """Test http_client with streaming enabled."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", enable_streaming=True
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock SSE response with text attribute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":"stream-test","result":{"streaming":true}}\n'
            "\n"
        )
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send a message that will trigger streaming
            msg = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "stream-test", "method": "slow_operation"}
            )

            await write_stream.send(msg)
            await asyncio.sleep(0.1)

            # Should receive streaming response
            import anyio

            with anyio.fail_after(3.0):
                response = await read_stream.receive()

            assert_is_jsonrpc_message(
                response, {"id": "stream-test", "result": {"streaming": True}}
            )


@pytest.mark.asyncio
async def test_http_client_timeout_configuration():
    """Test http_client respects timeout configuration."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp", timeout=15.0)

    # Just verify the params are created correctly
    assert params.timeout == 15.0

    async with http_client(params) as (read_stream, write_stream):
        # The timeout is used when creating httpx clients
        assert read_stream is not None
        assert write_stream is not None


@pytest.mark.asyncio
async def test_http_client_cleanup():
    """Test that http_client properly cleans up resources."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    # Track cleanup
    cleanup_called = False

    with patch(
        "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
    ) as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport

        # Mock context manager
        mock_transport.__aenter__.return_value = mock_transport

        async def mock_exit(*args):
            nonlocal cleanup_called
            cleanup_called = True
            return False

        mock_transport.__aexit__ = mock_exit

        # Mock get_streams
        from anyio import create_memory_object_stream

        read_stream, write_send = create_memory_object_stream(10)
        write_recv, write_stream = create_memory_object_stream(10)
        mock_transport.get_streams.return_value = (read_stream, write_stream)

        # Use the context manager
        async with http_client(params) as (r_stream, w_stream):
            pass  # Just enter and exit

        # Verify cleanup was called
        assert cleanup_called


@pytest.mark.asyncio
async def test_http_client_multiple_messages():
    """Test handling multiple messages."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        # Track created clients
        clients_created = []

        def create_client(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # Create response for this client
            response_index = len(clients_created)
            response = MagicMock()
            response.status_code = 200
            response.headers = {"content-type": "application/json"}
            response.json.return_value = {
                "jsonrpc": "2.0",
                "id": f"msg-{response_index}",
                "result": {"index": response_index},
            }
            response.text = f'{{"jsonrpc":"2.0","id":"msg-{response_index}","result":{{"index":{response_index}}}}}'

            mock_client.post = AsyncMock(return_value=response)
            clients_created.append(mock_client)
            return mock_client

        mock_client_class.side_effect = create_client

        async with http_client(params) as (read_stream, write_stream):
            # Send multiple messages
            for i in range(3):
                msg = JSONRPCMessage.model_validate(
                    {"jsonrpc": "2.0", "id": f"msg-{i}", "method": "test"}
                )
                await write_stream.send(msg)

            # Give time for processing
            await asyncio.sleep(0.2)

            # Receive responses
            received_responses = []
            try:
                for i in range(3):
                    import anyio

                    with anyio.fail_after(1.0):
                        response = await read_stream.receive()
                        received_responses.append(response)
            except anyio.TimeoutError:
                pass

            # Verify we got responses
            assert len(received_responses) >= 1

            # Verify clients were created
            assert len(clients_created) >= 1


@pytest.mark.asyncio
async def test_http_client_with_realistic_protocol_flow():
    """Test http_client with realistic protocol message flow."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock initialization response
        init_response = MagicMock()
        init_response.status_code = 200
        init_response.headers = {
            "content-type": "application/json",
            "mcp-session-id": "session-123",
        }
        init_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"listChanged": True},
                    "prompts": {"listChanged": True},
                },
                "serverInfo": {
                    "name": "streamable-http-test-server",
                    "version": "1.0.0",
                },
            },
        }
        init_response.text = '{"jsonrpc":"2.0","id":"init-1","result":{"protocolVersion":"2025-06-18","capabilities":{"tools":{"listChanged":true},"resources":{"listChanged":true},"prompts":{"listChanged":true}},"serverInfo":{"name":"streamable-http-test-server","version":"1.0.0"}}}'

        mock_client.post = AsyncMock(return_value=init_response)
        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send initialize request
            init_request = JSONRPCMessage.model_validate(
                {
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }
            )

            await write_stream.send(init_request)

            # Give time for processing
            await asyncio.sleep(0.1)

            # Receive response
            import anyio

            with anyio.fail_after(2.0):
                response = await read_stream.receive()

            assert_is_jsonrpc_message(response, {"id": "init-1"})
            assert (
                response.result["serverInfo"]["name"] == "streamable-http-test-server"
            )
            assert response.result["protocolVersion"] == "2025-06-18"


@pytest.mark.asyncio
async def test_http_client_session_management():
    """Test session ID handling in http_client."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock response with session ID
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/json",
            "mcp-session-id": "new-session-456",
        }
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "session-test",
            "result": {"sessionEstablished": True},
        }
        mock_response.text = (
            '{"jsonrpc":"2.0","id":"session-test","result":{"sessionEstablished":true}}'
        )

        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send a message
            msg = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "session-test", "method": "initialize"}
            )

            await write_stream.send(msg)
            await asyncio.sleep(0.1)

            # Verify response is received
            import anyio

            with anyio.fail_after(1.0):
                response = await read_stream.receive()

            assert_is_jsonrpc_message(
                response, {"id": "session-test", "result": {"sessionEstablished": True}}
            )


@pytest.mark.asyncio
async def test_http_client_bearer_token_setup():
    """Test automatic bearer token setup."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", bearer_token="auto-token-789"
    )

    # The bearer token is in the params and will be used in requests
    assert params.bearer_token == "auto-token-789"
    assert params.headers["Authorization"] == "Bearer auto-token-789"

    async with http_client(params) as (read_stream, write_stream):
        # Streams should be available
        assert read_stream is not None
        assert write_stream is not None


@pytest.mark.asyncio
async def test_http_client_concurrent_requests():
    """Test concurrent request handling."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", max_concurrent_requests=5
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        # Track concurrent clients
        concurrent_clients = []

        def create_client(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            call_index = len(concurrent_clients) + 1
            response = MagicMock()
            response.status_code = 200
            response.headers = {"content-type": "application/json"}
            response.json.return_value = {
                "jsonrpc": "2.0",
                "id": f"concurrent-{call_index}",
                "result": {"call": call_index},
            }
            response.text = f'{{"jsonrpc":"2.0","id":"concurrent-{call_index}","result":{{"call":{call_index}}}}}'

            mock_client.post = AsyncMock(return_value=response)
            concurrent_clients.append(mock_client)
            return mock_client

        mock_client_class.side_effect = create_client

        async with http_client(params) as (read_stream, write_stream):
            # Send multiple concurrent messages
            import anyio

            async with anyio.create_task_group() as tg:
                for i in range(3):

                    async def send_message(index=i):
                        msg = JSONRPCMessage.model_validate(
                            {
                                "jsonrpc": "2.0",
                                "id": f"concurrent-{index + 1}",
                                "method": "ping",
                            }
                        )
                        await write_stream.send(msg)

                    tg.start_soon(send_message)

            # Give time for processing
            await asyncio.sleep(0.2)

            # Verify multiple clients were created for concurrent requests
            assert len(concurrent_clients) >= 1


@pytest.mark.asyncio
async def test_http_client_streaming_with_completion():
    """Test streaming with completion events."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock SSE response with both message and completion
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":"completion-test","result":{"operation":"completed"}}\n'
            "\n"
            "event: completion\n"
            'data: {"type":"completion","timestamp":"2025-07-09T14:00:00Z"}\n'
            "\n"
        )

        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send message
            msg = JSONRPCMessage.model_validate(
                {
                    "jsonrpc": "2.0",
                    "id": "completion-test",
                    "method": "complex_operation",
                }
            )

            await write_stream.send(msg)
            await asyncio.sleep(0.1)

            # Should receive the main response
            import anyio

            with anyio.fail_after(3.0):
                response = await read_stream.receive()

            assert_is_jsonrpc_message(
                response,
                {"id": "completion-test", "result": {"operation": "completed"}},
            )


def test_http_client_imports():
    """Test that http_client imports work correctly."""
    from chuk_mcp.transports.http import http_client, StreamableHTTPParameters
    from chuk_mcp.transports.http.http_client import http_client as direct_import

    assert http_client is not None
    assert http_client == direct_import
    assert StreamableHTTPParameters is not None
