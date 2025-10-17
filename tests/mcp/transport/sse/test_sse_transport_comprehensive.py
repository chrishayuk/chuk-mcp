#!/usr/bin/env python3
"""
Comprehensive tests for SSE transport.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock
import pytest

from chuk_mcp.transports.sse.transport import SSETransport
from chuk_mcp.transports.sse.parameters import SSEParameters


class TestSSETransportInitialization:
    """Test SSE transport initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        assert transport.base_url == "http://localhost:3000"
        assert transport.headers == {}
        assert transport.timeout == 60.0
        assert transport.bearer_token is None
        assert transport._stream_client is None
        assert transport._send_client is None
        assert transport._message_url is None
        assert transport._session_id is None

    def test_init_with_bearer_token(self):
        """Test initialization with bearer token."""
        params = SSEParameters(
            url="http://localhost:3000", bearer_token="test_token_123"
        )
        transport = SSETransport(params)

        assert transport.bearer_token == "test_token_123"

    def test_init_with_headers(self):
        """Test initialization with custom headers."""
        headers = {"X-Custom": "value", "User-Agent": "test"}
        params = SSEParameters(url="http://localhost:3000", headers=headers)
        transport = SSETransport(params)

        assert transport.headers == headers

    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        params = SSEParameters(url="http://localhost:3000", timeout=30.0)
        transport = SSETransport(params)

        assert transport.timeout == 30.0


class TestSSETransportHeaders:
    """Test header generation."""

    def test_get_headers_no_auth(self):
        """Test getting headers without authentication."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        headers = transport._get_headers()
        assert "Authorization" not in headers

    def test_get_headers_with_bearer_token(self):
        """Test getting headers with bearer token."""
        params = SSEParameters(url="http://localhost:3000", bearer_token="test_token")
        transport = SSETransport(params)

        headers = transport._get_headers()
        assert headers["Authorization"] == "Bearer test_token"

    def test_get_headers_with_bearer_prefix(self):
        """Test getting headers with bearer token already having Bearer prefix."""
        params = SSEParameters(
            url="http://localhost:3000", bearer_token="Bearer test_token"
        )
        transport = SSETransport(params)

        headers = transport._get_headers()
        assert headers["Authorization"] == "Bearer test_token"

    def test_get_headers_existing_auth(self):
        """Test that existing authorization header is not overwritten."""
        headers = {"Authorization": "Custom auth"}
        params = SSEParameters(
            url="http://localhost:3000",
            headers=headers,
            bearer_token="test_token",
        )
        transport = SSETransport(params)

        result_headers = transport._get_headers()
        assert result_headers["Authorization"] == "Custom auth"

    def test_get_headers_custom_headers(self):
        """Test that custom headers are included."""
        headers = {"X-Custom": "value"}
        params = SSEParameters(url="http://localhost:3000", headers=headers)
        transport = SSETransport(params)

        result_headers = transport._get_headers()
        assert result_headers["X-Custom"] == "value"


class TestSSETransportStreams:
    """Test stream handling."""

    @pytest.mark.asyncio
    async def test_get_streams_not_started(self):
        """Test getting streams before starting transport."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        with pytest.raises(RuntimeError, match="Transport not started"):
            await transport.get_streams()

    @pytest.mark.asyncio
    async def test_get_streams_after_setup(self):
        """Test getting streams after setting up."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Manually set up streams
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )
        transport._outgoing_send, transport._outgoing_recv = (
            create_memory_object_stream(100)
        )

        read_stream, write_stream = await transport.get_streams()
        assert read_stream is transport._incoming_recv
        assert write_stream is transport._outgoing_send


class TestSSETransportConnection:
    """Test connection lifecycle."""

    @pytest.mark.asyncio
    async def test_aexit_cleanup(self):
        """Test cleanup during __aexit__."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Set up minimal state with mocks
        stream_client_mock = AsyncMock()
        send_client_mock = AsyncMock()
        transport._stream_client = stream_client_mock
        transport._send_client = send_client_mock

        await transport.__aexit__(None, None, None)

        # Verify clients were closed
        assert stream_client_mock.aclose.called
        assert send_client_mock.aclose.called
        # After cleanup, clients should be set to None
        assert transport._stream_client is None
        assert transport._send_client is None


class TestSSETransportCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_pending_requests(self):
        """Test cleanup cancels pending requests."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Add some pending requests
        future1 = asyncio.Future()
        future2 = asyncio.Future()
        transport._pending_requests = {"req1": future1, "req2": future2}

        await transport._cleanup()

        assert future1.cancelled()
        assert future2.cancelled()
        assert len(transport._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_cleanup_tasks(self):
        """Test cleanup cancels running tasks."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Create mock tasks
        async def dummy_coro():
            await asyncio.sleep(10)

        transport._sse_task = asyncio.create_task(dummy_coro())
        transport._outgoing_task = asyncio.create_task(dummy_coro())

        await transport._cleanup()

        assert transport._sse_task.cancelled()
        assert transport._outgoing_task.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_streams(self):
        """Test cleanup closes streams."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )
        transport._outgoing_send, transport._outgoing_recv = (
            create_memory_object_stream(100)
        )

        await transport._cleanup()

        # Streams should be closed - writing should fail
        with pytest.raises(Exception):
            await transport._incoming_send.send("test")

    @pytest.mark.asyncio
    async def test_cleanup_http_clients(self):
        """Test cleanup closes HTTP clients."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        stream_client_mock = AsyncMock()
        send_client_mock = AsyncMock()
        transport._stream_client = stream_client_mock
        transport._send_client = send_client_mock

        await transport._cleanup()

        assert stream_client_mock.aclose.called
        assert send_client_mock.aclose.called
        assert transport._stream_client is None
        assert transport._send_client is None


class TestSSETransportProtocol:
    """Test protocol version handling."""

    def test_set_protocol_version(self):
        """Test setting protocol version (no-op for SSE)."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Should not raise
        transport.set_protocol_version("2024-11-05")


class TestSSETransportEndpointHandling:
    """Test endpoint event handling."""

    @pytest.mark.asyncio
    async def test_handle_endpoint_absolute_path(self):
        """Test handling endpoint with absolute path."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        await transport._handle_endpoint_event("/messages/?session_id=abc123")

        assert (
            transport._message_url
            == "http://localhost:3000/messages/?session_id=abc123"
        )
        assert transport._session_id == "abc123"
        assert transport._connected.is_set()

    @pytest.mark.asyncio
    async def test_handle_endpoint_query_params(self):
        """Test handling endpoint with query parameters."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        await transport._handle_endpoint_event("session_id=xyz789")

        assert "session_id=xyz789" in transport._message_url
        assert transport._session_id == "xyz789"
        assert transport._connected.is_set()

    @pytest.mark.asyncio
    async def test_handle_endpoint_full_url(self):
        """Test handling endpoint with full URL."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        await transport._handle_endpoint_event(
            "http://localhost:3000/mcp?session_id=def456"
        )

        assert transport._message_url == "http://localhost:3000/mcp?session_id=def456"
        assert transport._session_id == "def456"

    @pytest.mark.asyncio
    async def test_handle_endpoint_with_empty_string(self):
        """Test handling endpoint with empty string."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Empty string gets processed as-is
        await transport._handle_endpoint_event("")

        # Empty string results in empty message URL
        assert transport._message_url == ""
        assert transport._connected.is_set()


class TestSSETransportMessageHandling:
    """Test message event handling."""

    @pytest.mark.asyncio
    async def test_handle_message_event_pending_request(self):
        """Test handling message event for pending request."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Set up streams
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        # Add a pending request
        future = asyncio.Future()
        transport._pending_requests["123"] = future

        message_data = {"jsonrpc": "2.0", "id": "123", "result": {"status": "ok"}}

        await transport._handle_message_event(json.dumps(message_data))

        # Future should be resolved
        assert future.done()
        assert future.result() == message_data

    @pytest.mark.asyncio
    async def test_handle_message_event_no_pending(self):
        """Test handling message event with no pending request."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Set up streams
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        message_data = {"jsonrpc": "2.0", "method": "test", "params": {}}

        await transport._handle_message_event(json.dumps(message_data))

        # Message should be routed to incoming stream
        received = await asyncio.wait_for(
            transport._incoming_recv.receive(), timeout=1.0
        )
        assert received.method == "test"

    @pytest.mark.asyncio
    async def test_handle_message_event_invalid_json(self):
        """Test handling invalid JSON."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        # Should not raise - just log error
        await transport._handle_message_event("not valid json")


class TestSSETransportProcessSSEStream:
    """Test SSE stream processing."""

    # Note: Detailed SSE stream processing tests are complex to mock properly
    # due to async iteration requirements. The actual processing is tested
    # through integration tests and the individual event handlers are tested above.


class TestSSETransportSendMessage:
    """Test sending messages via HTTP."""

    @pytest.mark.asyncio
    async def test_send_message_no_client(self):
        """Test sending message without client."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        message = {"jsonrpc": "2.0", "method": "test"}

        # Should not raise, just log error
        await transport._send_message_via_http(message)

    @pytest.mark.asyncio
    async def test_send_message_notification(self):
        """Test sending notification (no ID)."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._send_client = AsyncMock()
        transport._message_url = "http://localhost:3000/mcp"

        mock_response = Mock()
        mock_response.status_code = 200
        transport._send_client.post = AsyncMock(return_value=mock_response)

        message = {"jsonrpc": "2.0", "method": "test"}

        await transport._send_message_via_http(message)

        assert transport._send_client.post.called

    @pytest.mark.asyncio
    async def test_send_message_immediate_response(self):
        """Test sending request with immediate 200 response."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._send_client = AsyncMock()
        transport._message_url = "http://localhost:3000/mcp"
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        response_data = {"jsonrpc": "2.0", "id": "123", "result": {"status": "ok"}}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=response_data)
        transport._send_client.post = AsyncMock(return_value=mock_response)

        message = {"jsonrpc": "2.0", "id": "123", "method": "test"}

        await transport._send_message_via_http(message)

        # Response should be routed to incoming stream
        received = await asyncio.wait_for(
            transport._incoming_recv.receive(), timeout=1.0
        )
        assert received.id == "123"

    @pytest.mark.asyncio
    async def test_send_message_async_202_response(self):
        """Test sending request with async 202 response."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000", timeout=2.0)
        transport = SSETransport(params)

        transport._send_client = AsyncMock()
        transport._message_url = "http://localhost:3000/mcp"
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        mock_response = Mock()
        mock_response.status_code = 202
        transport._send_client.post = AsyncMock(return_value=mock_response)

        message = {"jsonrpc": "2.0", "id": "456", "method": "test"}

        # Simulate SSE response arriving
        async def simulate_sse_response():
            await asyncio.sleep(0.1)
            if "456" in transport._pending_requests:
                future = transport._pending_requests["456"]
                response_data = {
                    "jsonrpc": "2.0",
                    "id": "456",
                    "result": {"status": "ok"},
                }
                future.set_result(response_data)

        asyncio.create_task(simulate_sse_response())

        await transport._send_message_via_http(message)

        # Response should be routed to incoming stream
        received = await asyncio.wait_for(
            transport._incoming_recv.receive(), timeout=2.0
        )
        assert received.id == "456"

    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Test sending request with timeout."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000", timeout=0.5)
        transport = SSETransport(params)

        transport._send_client = AsyncMock()
        transport._message_url = "http://localhost:3000/mcp"
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        mock_response = Mock()
        mock_response.status_code = 202
        transport._send_client.post = AsyncMock(return_value=mock_response)

        message = {"jsonrpc": "2.0", "id": "789", "method": "test"}

        await transport._send_message_via_http(message)

        # Timeout error should be routed to incoming stream
        received = await asyncio.wait_for(
            transport._incoming_recv.receive(), timeout=2.0
        )
        assert "error" in received.model_dump()

    @pytest.mark.asyncio
    async def test_send_message_unexpected_status(self):
        """Test sending request with unexpected status code."""
        from anyio import create_memory_object_stream

        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._send_client = AsyncMock()
        transport._message_url = "http://localhost:3000/mcp"
        transport._incoming_send, transport._incoming_recv = (
            create_memory_object_stream(100)
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json = Mock(side_effect=Exception("Not JSON"))
        transport._send_client.post = AsyncMock(return_value=mock_response)

        message = {"jsonrpc": "2.0", "id": "error123", "method": "test"}

        await transport._send_message_via_http(message)

        # Error response should be routed to incoming stream
        received = await asyncio.wait_for(
            transport._incoming_recv.receive(), timeout=1.0
        )
        assert "error" in received.model_dump()


class TestSSETransportStatus:
    """Test connection status."""

    def test_is_connected_false(self):
        """Test is_connected when not connected."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        assert transport.is_connected() is False

    def test_is_connected_true(self):
        """Test is_connected when connected."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._connected.set()
        transport._message_url = "http://localhost:3000/mcp"

        assert transport.is_connected() is True

    def test_repr_disconnected(self):
        """Test string representation when disconnected."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        repr_str = repr(transport)
        assert "SSETransport" in repr_str
        assert "disconnected" in repr_str
        assert "http://localhost:3000" in repr_str

    def test_repr_connected(self):
        """Test string representation when connected."""
        params = SSEParameters(url="http://localhost:3000")
        transport = SSETransport(params)

        transport._connected.set()
        transport._message_url = "http://localhost:3000/mcp"
        transport._session_id = "test123"

        repr_str = repr(transport)
        assert "SSETransport" in repr_str
        assert "connected" in repr_str
        assert "test123" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
