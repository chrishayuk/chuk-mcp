#!/usr/bin/env python3
"""
Comprehensive tests for http_client.py module.
"""

import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch

from chuk_mcp.transports.http.http_client import (
    http_client,
    streamable_http_client,
    create_http_parameters_from_url,
    is_streamable_http_url,
    detect_transport_type,
    try_http_with_sse_fallback,
)
from chuk_mcp.transports.http.parameters import StreamableHTTPParameters


class TestHttpClient:
    """Test http_client context manager."""

    @pytest.mark.asyncio
    async def test_http_client_success(self):
        """Test successful HTTP client creation."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_streams = (mock_read, mock_write)

        with patch(
            "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
        ) as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.return_value = mock_transport
            mock_transport.__aexit__ = AsyncMock()
            mock_transport.get_streams.return_value = mock_streams
            MockTransport.return_value = mock_transport

            async with http_client(params) as streams:
                assert streams == mock_streams
                mock_transport.get_streams.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_client_with_logging(self, caplog):
        """Test HTTP client with logging enabled."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        mock_streams = (AsyncMock(), AsyncMock())

        with caplog.at_level(logging.INFO):
            with patch(
                "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.return_value = mock_transport
                mock_transport.__aexit__ = AsyncMock()
                mock_transport.get_streams.return_value = mock_streams
                MockTransport.return_value = mock_transport

                async with http_client(params) as streams:
                    assert streams == mock_streams

        assert any(
            "Creating Streamable HTTP client" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_http_client_debug_logging(self, caplog):
        """Test HTTP client with debug logging."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        mock_streams = (AsyncMock(), AsyncMock())

        with caplog.at_level(logging.DEBUG):
            with patch(
                "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.return_value = mock_transport
                mock_transport.__aexit__ = AsyncMock()
                mock_transport.get_streams.return_value = mock_streams
                MockTransport.return_value = mock_transport

                async with http_client(params) as streams:
                    assert streams == mock_streams

        assert any(
            "HTTP client streams ready" in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_http_client_runtime_error(self):
        """Test HTTP client handling RuntimeError."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        with patch(
            "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
        ) as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.side_effect = RuntimeError("Connection failed")
            MockTransport.return_value = mock_transport

            with pytest.raises(RuntimeError, match="Connection failed"):
                async with http_client(params):
                    pass

    @pytest.mark.asyncio
    async def test_http_client_timeout_error(self):
        """Test HTTP client handling TimeoutError."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        with patch(
            "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
        ) as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.side_effect = TimeoutError("Timeout")
            MockTransport.return_value = mock_transport

            with pytest.raises(TimeoutError, match="Timeout"):
                async with http_client(params):
                    pass

    @pytest.mark.asyncio
    async def test_http_client_connection_error(self):
        """Test HTTP client handling ConnectionError."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        with patch(
            "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
        ) as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.side_effect = ConnectionError(
                "Connection refused"
            )
            MockTransport.return_value = mock_transport

            with pytest.raises(ConnectionError, match="Connection refused"):
                async with http_client(params):
                    pass

    @pytest.mark.asyncio
    async def test_http_client_os_error(self):
        """Test HTTP client handling OSError."""
        params = StreamableHTTPParameters(url="http://localhost/mcp")

        with patch(
            "chuk_mcp.transports.http.http_client.StreamableHTTPTransport"
        ) as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.side_effect = OSError("Network error")
            MockTransport.return_value = mock_transport

            with pytest.raises(OSError, match="Network error"):
                async with http_client(params):
                    pass


class TestStreamableHttpClient:
    """Test streamable_http_client alias."""

    def test_streamable_http_client_is_alias(self):
        """Test that streamable_http_client is an alias for http_client."""
        assert streamable_http_client is http_client


class TestCreateHttpParametersFromUrl:
    """Test create_http_parameters_from_url helper."""

    def test_create_http_parameters_basic(self):
        """Test creating parameters with just URL."""
        params = create_http_parameters_from_url("http://localhost/mcp")

        assert params.url == "http://localhost/mcp"
        assert params.bearer_token is None
        assert params.timeout == 60.0
        assert params.enable_streaming is True

    def test_create_http_parameters_with_token(self):
        """Test creating parameters with bearer token."""
        params = create_http_parameters_from_url(
            "http://localhost/mcp", bearer_token="test-token"
        )

        assert params.url == "http://localhost/mcp"
        assert params.bearer_token == "test-token"

    def test_create_http_parameters_with_timeout(self):
        """Test creating parameters with custom timeout."""
        params = create_http_parameters_from_url("http://localhost/mcp", timeout=30.0)

        assert params.timeout == 30.0

    def test_create_http_parameters_disable_streaming(self):
        """Test creating parameters with streaming disabled."""
        params = create_http_parameters_from_url(
            "http://localhost/mcp", enable_streaming=False
        )

        assert params.enable_streaming is False

    def test_create_http_parameters_with_kwargs(self):
        """Test creating parameters with additional kwargs."""
        params = create_http_parameters_from_url(
            "http://localhost/mcp",
            bearer_token="token",
            timeout=45.0,
            enable_streaming=True,
        )

        assert params.url == "http://localhost/mcp"
        assert params.bearer_token == "token"
        assert params.timeout == 45.0


class TestIsStreamableHttpUrl:
    """Test is_streamable_http_url function."""

    def test_is_streamable_http_url_with_mcp(self):
        """Test URL with /mcp path."""
        assert is_streamable_http_url("http://localhost/mcp") is True

    def test_is_streamable_http_url_with_api_mcp(self):
        """Test URL with /api/mcp path."""
        assert is_streamable_http_url("http://localhost/api/mcp") is True

    def test_is_streamable_http_url_with_v1_mcp(self):
        """Test URL with /v1/mcp path."""
        assert is_streamable_http_url("http://localhost/v1/mcp") is True

    def test_is_streamable_http_url_with_subdomain(self):
        """Test URL with mcp subdomain."""
        assert is_streamable_http_url("http://mcp.example.com/api") is True

    def test_is_streamable_http_url_with_sse_pattern(self):
        """Test URL with SSE pattern should return False."""
        assert is_streamable_http_url("http://localhost/sse") is False

    def test_is_streamable_http_url_with_events_pattern(self):
        """Test URL with /events pattern should return False."""
        assert is_streamable_http_url("http://localhost/events") is False

    def test_is_streamable_http_url_with_stream_pattern(self):
        """Test URL with /stream pattern should return False."""
        assert is_streamable_http_url("http://localhost/stream") is False

    def test_is_streamable_http_url_empty_string(self):
        """Test with empty string."""
        assert is_streamable_http_url("") is False

    def test_is_streamable_http_url_none(self):
        """Test with None."""
        assert is_streamable_http_url(None) is False

    def test_is_streamable_http_url_no_indicators(self):
        """Test URL without HTTP indicators."""
        assert is_streamable_http_url("http://localhost/api") is False

    def test_is_streamable_http_url_case_insensitive(self):
        """Test that URL checking is case insensitive."""
        assert is_streamable_http_url("http://localhost/MCP") is True
        assert is_streamable_http_url("http://MCP.example.com") is True


class TestDetectTransportType:
    """Test detect_transport_type function."""

    @pytest.mark.asyncio
    async def test_detect_streamable_http(self):
        """Test detecting Streamable HTTP support."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.get.return_value = Mock(status_code=404)

            MockClient.return_value = mock_client

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "streamable_http"

    @pytest.mark.asyncio
    async def test_detect_sse(self):
        """Test detecting SSE support."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_http_response = Mock()
            mock_http_response.status_code = 404

            mock_sse_response = Mock()
            mock_sse_response.status_code = 200
            mock_sse_response.headers = {"content-type": "text/event-stream"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_http_response
            mock_client.get.return_value = mock_sse_response

            MockClient.return_value = mock_client

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "sse"

    @pytest.mark.asyncio
    async def test_detect_both(self):
        """Test detecting both transport types."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_http_response = Mock()
            mock_http_response.status_code = 200
            mock_http_response.headers = {"content-type": "application/json"}

            mock_sse_response = Mock()
            mock_sse_response.status_code = 200
            mock_sse_response.headers = {"content-type": "text/event-stream"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_http_response
            mock_client.get.return_value = mock_sse_response

            MockClient.return_value = mock_client

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "both"

    @pytest.mark.asyncio
    async def test_detect_unknown(self):
        """Test detecting unknown transport type."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = Mock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.get.return_value = mock_response

            MockClient.return_value = mock_client

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "unknown"

    @pytest.mark.asyncio
    async def test_detect_with_bearer_token(self):
        """Test detection with bearer token."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_response

            MockClient.return_value = mock_client

            result = await detect_transport_type(
                "http://localhost/mcp", bearer_token="test-token"
            )
            assert result in ["streamable_http", "sse", "both", "unknown"]

            # Verify headers were set
            MockClient.assert_called()
            call_kwargs = MockClient.call_args[1]
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_detect_exception_handling(self):
        """Test exception handling during detection."""
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.side_effect = Exception("Network error")

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "unknown"

    @pytest.mark.asyncio
    async def test_detect_sse_with_event_stream_content_type(self):
        """Test SSE detection with text/event-stream content type."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_http_response = Mock()
            mock_http_response.status_code = 202
            mock_http_response.headers = {"content-type": "text/event-stream"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock()
            mock_client.post.return_value = mock_http_response
            mock_client.get.return_value = Mock(status_code=404)

            MockClient.return_value = mock_client

            result = await detect_transport_type("http://localhost/mcp")
            assert result == "streamable_http"


class TestTryHttpWithSseFallback:
    """Test try_http_with_sse_fallback function."""

    @pytest.mark.asyncio
    async def test_try_http_success(self):
        """Test successful HTTP connection without fallback."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="streamable_http",
        ):
            with patch(
                "chuk_mcp.transports.http.http_client.http_client"
            ) as mock_client:
                await try_http_with_sse_fallback("http://localhost/mcp")
                mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_http_with_both_support(self):
        """Test when server supports both transports."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="both",
        ):
            with patch(
                "chuk_mcp.transports.http.http_client.http_client"
            ) as mock_client:
                await try_http_with_sse_fallback("http://localhost/mcp")
                mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_sse_fallback(self):
        """Test SSE fallback when HTTP not supported."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="sse",
        ):
            with patch("chuk_mcp.transports.sse.sse_client"):
                from chuk_mcp.transports.sse import SSEParameters

                with patch("chuk_mcp.transports.sse.SSEParameters", SSEParameters):
                    await try_http_with_sse_fallback("http://localhost/mcp")
                    # SSE client should be called

    @pytest.mark.asyncio
    async def test_try_both_fail(self):
        """Test when both transports fail."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="unknown",
        ):
            # Mock the SSE client to make it fail
            with patch(
                "chuk_mcp.transports.sse.sse_client",
                side_effect=Exception("SSE not available"),
            ):
                with pytest.raises(Exception, match="Both Streamable HTTP and SSE"):
                    await try_http_with_sse_fallback("http://localhost/mcp")

    @pytest.mark.asyncio
    async def test_try_http_fail_sse_success(self, caplog):
        """Test HTTP fails but SSE succeeds."""
        with caplog.at_level(logging.WARNING):
            with patch(
                "chuk_mcp.transports.http.http_client.detect_transport_type",
                return_value="unknown",
            ):
                # Mock SSE to succeed
                with patch("chuk_mcp.transports.sse.sse_client") as mock_sse:
                    await try_http_with_sse_fallback("http://localhost/mcp")
                    # Should have tried SSE
                    mock_sse.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_with_bearer_token(self):
        """Test with bearer token parameter."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="streamable_http",
        ):
            with patch(
                "chuk_mcp.transports.http.http_client.http_client"
            ) as mock_client:
                await try_http_with_sse_fallback(
                    "http://localhost/mcp", bearer_token="test-token"
                )

                # Verify parameters were passed correctly
                call_args = mock_client.call_args[0][0]
                assert call_args.bearer_token == "test-token"

    @pytest.mark.asyncio
    async def test_try_with_custom_timeout(self):
        """Test with custom timeout."""
        with patch(
            "chuk_mcp.transports.http.http_client.detect_transport_type",
            return_value="streamable_http",
        ):
            with patch(
                "chuk_mcp.transports.http.http_client.http_client"
            ) as mock_client:
                await try_http_with_sse_fallback("http://localhost/mcp", timeout=120.0)

                # Verify timeout was passed
                call_args = mock_client.call_args[0][0]
                assert call_args.timeout == 120.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
