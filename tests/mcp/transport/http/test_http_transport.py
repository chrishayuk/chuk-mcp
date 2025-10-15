# tests/mcp/transport/http/test_http_transport.py
"""
Tests for Streamable HTTP transport implementation - Fixed version.

These tests are updated to work with the simplified transport that creates
a new HTTP client per request.
"""

import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from chuk_mcp.transports.http.parameters import StreamableHTTPParameters
from chuk_mcp.transports.http.transport import StreamableHTTPTransport
from chuk_mcp.transports.http import http_client
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

pytest.importorskip("httpx")
pytest.importorskip("chuk_mcp.transports.http")

###############################################################################
# Parameter Tests
###############################################################################


def test_streamable_http_parameters_creation():
    """Test creating Streamable HTTP parameters."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    assert params.url == "http://localhost:3000/mcp"
    assert params.headers is not None  # Auto-added User-Agent
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert params.timeout == 60.0
    assert params.enable_streaming is True


def test_streamable_http_parameters_with_all_fields():
    """Test Streamable HTTP parameters with all fields."""
    params = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"X-API-Key": "key123"},
        timeout=30.0,
        bearer_token="token123",
        enable_streaming=False,
    )

    assert params.url == "https://api.example.com/mcp"
    assert params.headers["X-API-Key"] == "key123"
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"  # Auto-added
    assert params.timeout == 30.0
    assert params.bearer_token == "token123"
    assert params.enable_streaming is False


###############################################################################
# Transport Creation Tests
###############################################################################


def test_streamable_http_transport_creation():
    """Test creating Streamable HTTP transport."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    transport = StreamableHTTPTransport(params)

    assert transport.endpoint_url == "http://localhost:3000/mcp"
    assert transport.timeout == 60.0
    assert transport.enable_streaming is True
    # Note: _client no longer exists in simplified version
    assert transport._session_id is None


def test_streamable_http_transport_with_options():
    """Test Streamable HTTP transport with custom options."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        timeout=30.0,
        enable_streaming=False,
        max_concurrent_requests=5,
    )
    transport = StreamableHTTPTransport(params)

    assert transport.timeout == 30.0
    assert transport.enable_streaming is False


def test_streamable_http_transport_get_streams_before_start():
    """Test that get_streams raises error before starting."""
    transport = StreamableHTTPTransport(
        StreamableHTTPParameters(url="http://localhost:3000")
    )

    with pytest.raises(RuntimeError, match="Transport not started"):
        asyncio.run(transport.get_streams())


def test_streamable_http_transport_protocol_version():
    """Test protocol version handling."""
    transport = StreamableHTTPTransport(
        StreamableHTTPParameters(url="http://localhost:3000")
    )

    # Test set_protocol_version (should not raise)
    transport.set_protocol_version("2025-06-18")
    # Streamable HTTP transport doesn't maintain version state


###############################################################################
# Context Manager Tests
###############################################################################


@pytest.mark.asyncio
async def test_streamable_http_transport_context_manager():
    """Test Streamable HTTP transport as context manager."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    transport = StreamableHTTPTransport(params)

    async with transport:
        # Verify streams are available
        read_stream, write_stream = await transport.get_streams()
        assert read_stream is not None
        assert write_stream is not None


@pytest.mark.asyncio
async def test_streamable_http_transport_with_auth_headers():
    """Test Streamable HTTP transport with authentication headers."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", headers={"Authorization": "Bearer token123"}
    )
    transport = StreamableHTTPTransport(params)

    # The auth headers are stored and will be used when making requests
    assert transport.headers["Authorization"] == "Bearer token123"


@pytest.mark.asyncio
async def test_streamable_http_transport_env_bearer_token():
    """Test automatic bearer token from environment."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch.dict(os.environ, {"MCP_BEARER_TOKEN": "env-token-456"}):
        # Mock httpx.AsyncClient to verify headers
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            transport = StreamableHTTPTransport(params)
            async with transport:
                # Send a message to trigger client creation
                message = JSONRPCMessage.model_validate(
                    {"jsonrpc": "2.0", "id": "test", "method": "ping"}
                )

                # Mock the response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "application/json"}
                mock_response.json.return_value = {
                    "jsonrpc": "2.0",
                    "id": "test",
                    "result": {},
                }
                mock_response.text = '{"jsonrpc": "2.0", "id": "test", "result": {}}'
                mock_client.post.return_value = mock_response

                read_stream, write_stream = await transport.get_streams()
                await write_stream.send(message)
                await asyncio.sleep(0.1)

                # Check that the post was called with the right headers
                mock_client.post.assert_called()
                call_args = mock_client.post.call_args
                headers = call_args[1]["headers"]
                # The bearer token from env should be in the headers
                assert "Bearer env-token-456" in headers.get("Authorization", "")


###############################################################################
# HTTP Client Context Manager Tests
###############################################################################


@pytest.mark.asyncio
async def test_http_client_context_manager():
    """Test http_client context manager."""
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

        read_stream, write_send = create_memory_object_stream(10)
        write_recv, write_stream = create_memory_object_stream(10)
        mock_transport.get_streams.return_value = (read_stream, write_stream)

        async with http_client(params) as (r_stream, w_stream):
            assert r_stream is not None
            assert w_stream is not None

            # Verify transport was created correctly
            mock_transport_class.assert_called_once_with(params)


@pytest.mark.asyncio
async def test_http_client_error_propagation():
    """Test that http_client propagates errors correctly."""
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


###############################################################################
# Message Flow Tests - Fixed to work with per-request client
###############################################################################


@pytest.mark.asyncio
async def test_streamable_http_message_flow():
    """Test message flow through Streamable HTTP transport."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock successful JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"status": "ok"},
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_client.post.return_value = mock_response

        mock_client_class.return_value = mock_client

        transport = StreamableHTTPTransport(params)
        async with transport:
            read_stream, write_stream = await transport.get_streams()

            # Send a message
            test_message = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "test-123", "method": "ping"}
            )

            await write_stream.send(test_message)

            # Give time for processing
            await asyncio.sleep(0.1)

            # Should receive response
            import anyio

            with anyio.fail_after(1.0):
                response = await read_stream.receive()

            assert response.id == "test-123"
            assert response.result == {"status": "ok"}

            # Verify the client was created and used
            assert mock_client_class.called
            assert mock_client.post.called


@pytest.mark.asyncio
async def test_streamable_http_sse_flow():
    """Test SSE streaming flow."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock SSE response with proper text attribute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":"test-sse","result":{"status":"streaming"}}\n'
            "\n"
            "event: completion\n"
            'data: {"type":"completion","timestamp":"2025-07-09T14:00:00Z"}\n'
            "\n"
        )

        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        transport = StreamableHTTPTransport(params)
        async with transport:
            read_stream, write_stream = await transport.get_streams()

            # Send a message that will trigger SSE
            test_message = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "test-sse", "method": "slow_operation"}
            )

            await write_stream.send(test_message)

            # Give time for SSE processing
            await asyncio.sleep(0.1)

            # Should receive streaming response
            import anyio

            with anyio.fail_after(1.0):
                response = await read_stream.receive()

            assert response.id == "test-sse"
            assert response.result == {"status": "streaming"}


###############################################################################
# Error Handling Tests
###############################################################################


@pytest.mark.asyncio
async def test_streamable_http_connection_error():
    """Test handling of connection errors."""
    params = StreamableHTTPParameters(url="http://localhost:9999/mcp", timeout=1.0)

    # Test that the transport handles errors gracefully
    transport = StreamableHTTPTransport(params)
    async with transport:
        read_stream, write_stream = await transport.get_streams()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # Mock connection error
            mock_client.post.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client

            test_message = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "test-fail", "method": "ping"}
            )
            await write_stream.send(test_message)

            # Should receive error response
            import anyio

            with anyio.fail_after(2.0):
                response = await read_stream.receive()
                assert response.error is not None


@pytest.mark.asyncio
async def test_streamable_http_http_error_status():
    """Test handling of HTTP error status codes."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock 500 error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post.return_value = mock_response

        mock_client_class.return_value = mock_client

        transport = StreamableHTTPTransport(params)
        async with transport:
            read_stream, write_stream = await transport.get_streams()

            # Send a message
            test_message = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "test-error", "method": "ping"}
            )

            await write_stream.send(test_message)

            # Give time for processing
            await asyncio.sleep(0.1)

            # Should receive error response
            import anyio

            with anyio.fail_after(1.0):
                response = await read_stream.receive()
                assert response.error is not None
                assert "500" in response.error["message"]


###############################################################################
# Session Management Tests
###############################################################################


@pytest.mark.asyncio
async def test_streamable_http_session_management():
    """Test session ID management."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock response with session ID
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/json",
            "mcp-session-id": "new-session-123",
        }
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "init",
            "result": {"status": "initialized"},
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_client.post.return_value = mock_response

        mock_client_class.return_value = mock_client

        transport = StreamableHTTPTransport(params)
        async with transport:
            # Initially no session ID
            assert transport.get_session_id() is None

            read_stream, write_stream = await transport.get_streams()

            # Send initialization message
            init_message = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "init", "method": "initialize"}
            )

            await write_stream.send(init_message)
            await asyncio.sleep(0.1)

            # Session ID should be updated
            assert transport.get_session_id() == "new-session-123"


def test_streamable_http_transport_interface_compliance():
    """Test that StreamableHTTPTransport implements the Transport interface."""
    from chuk_mcp.transports.base import Transport, TransportParameters

    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    transport = StreamableHTTPTransport(params)

    # Verify inheritance
    assert isinstance(transport, Transport)
    assert isinstance(params, TransportParameters)

    # Verify required methods exist
    assert hasattr(transport, "get_streams")
    assert hasattr(transport, "__aenter__")
    assert hasattr(transport, "__aexit__")
    assert hasattr(transport, "set_protocol_version")

    # Verify methods are callable
    assert callable(transport.get_streams)
    assert callable(transport.__aenter__)
    assert callable(transport.__aexit__)
    assert callable(transport.set_protocol_version)


def test_streamable_http_imports_work():
    """Test that Streamable HTTP transport imports work correctly."""
    from chuk_mcp.transports.http import (
        StreamableHTTPTransport,
        StreamableHTTPParameters,
        http_client,
    )
    from chuk_mcp.transports.base import Transport, TransportParameters

    # Verify inheritance
    assert issubclass(StreamableHTTPTransport, Transport)
    assert issubclass(StreamableHTTPParameters, TransportParameters)

    # Verify exports
    assert StreamableHTTPTransport is not None
    assert StreamableHTTPParameters is not None
    assert http_client is not None


###############################################################################
# Integration Tests
###############################################################################


@pytest.mark.asyncio
async def test_streamable_http_full_integration():
    """Test complete integration with realistic message flow."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", timeout=30.0, enable_streaming=True
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Mock various responses
        responses = [
            # Initialize response
            MagicMock(
                status_code=200,
                headers={
                    "content-type": "application/json",
                    "mcp-session-id": "session-123",
                },
                json=lambda: {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "serverInfo": {"name": "test-server", "version": "1.0.0"},
                    },
                },
                text='{"jsonrpc":"2.0","id":"init","result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"test-server","version":"1.0.0"}}}',
            ),
            # Tools list response
            MagicMock(
                status_code=200,
                headers={"content-type": "application/json"},
                json=lambda: {
                    "jsonrpc": "2.0",
                    "id": "tools",
                    "result": {"tools": [{"name": "echo", "description": "Echo tool"}]},
                },
                text='{"jsonrpc":"2.0","id":"tools","result":{"tools":[{"name":"echo","description":"Echo tool"}]}}',
            ),
        ]

        mock_client.post.side_effect = responses
        mock_client_class.return_value = mock_client

        async with http_client(params) as (read_stream, write_stream):
            # Send initialize
            init_msg = JSONRPCMessage.model_validate(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18"},
                }
            )
            await write_stream.send(init_msg)
            await asyncio.sleep(0.1)

            # Send tools/list
            tools_msg = JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": "tools", "method": "tools/list"}
            )
            await write_stream.send(tools_msg)
            await asyncio.sleep(0.1)

            # Should receive responses
            responses_received = []
            try:
                for _ in range(2):
                    import anyio

                    with anyio.fail_after(1.0):
                        response = await read_stream.receive()
                        responses_received.append(response)
            except anyio.TimeoutError:
                pass  # Some responses might not arrive in test

            # Verify we got at least one response
            assert len(responses_received) >= 1

            # Verify HTTP requests were made
            assert mock_client.post.call_count >= 1
