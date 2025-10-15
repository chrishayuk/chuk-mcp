#!/usr/bin/env python3
"""
Comprehensive tests for sse_client.py module.
"""

import pytest
import logging
from unittest.mock import AsyncMock, patch

from chuk_mcp.transports.sse.sse_client import (
    sse_client,
    create_sse_parameters_from_url,
    is_sse_url,
    try_sse_with_fallback,
)
from chuk_mcp.transports.sse.parameters import SSEParameters


class TestSseClient:
    """Test sse_client context manager."""

    @pytest.mark.asyncio
    async def test_sse_client_success(self):
        """Test successful SSE client creation."""
        params = SSEParameters(url="http://localhost/sse")

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_streams = (mock_read, mock_write)

        with patch("chuk_mcp.transports.sse.sse_client.SSETransport") as MockTransport:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.return_value = mock_transport
            mock_transport.__aexit__ = AsyncMock()
            mock_transport.get_streams.return_value = mock_streams
            MockTransport.return_value = mock_transport

            async with sse_client(params) as streams:
                assert streams == mock_streams
                mock_transport.get_streams.assert_called_once()

    @pytest.mark.asyncio
    async def test_sse_client_with_logging(self, caplog):
        """Test SSE client with logging enabled."""
        params = SSEParameters(url="http://localhost/sse")

        mock_streams = (AsyncMock(), AsyncMock())

        with caplog.at_level(logging.INFO):
            with patch(
                "chuk_mcp.transports.sse.sse_client.SSETransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.return_value = mock_transport
                mock_transport.__aexit__ = AsyncMock()
                mock_transport.get_streams.return_value = mock_streams
                MockTransport.return_value = mock_transport

                async with sse_client(params) as streams:
                    assert streams == mock_streams

        assert any("Creating SSE client" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_sse_client_debug_logging(self, caplog):
        """Test SSE client with debug logging."""
        params = SSEParameters(url="http://localhost/sse")

        mock_streams = (AsyncMock(), AsyncMock())

        with caplog.at_level(logging.DEBUG):
            with patch(
                "chuk_mcp.transports.sse.sse_client.SSETransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.return_value = mock_transport
                mock_transport.__aexit__ = AsyncMock()
                mock_transport.get_streams.return_value = mock_streams
                MockTransport.return_value = mock_transport

                async with sse_client(params) as streams:
                    assert streams == mock_streams

        assert any(
            "SSE client streams ready" in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_sse_client_runtime_error(self, caplog):
        """Test SSE client handling RuntimeError."""
        params = SSEParameters(url="http://localhost/sse")

        with caplog.at_level(logging.ERROR):
            with patch(
                "chuk_mcp.transports.sse.sse_client.SSETransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.side_effect = RuntimeError(
                    "Connection failed"
                )
                MockTransport.return_value = mock_transport

                with pytest.raises(RuntimeError, match="Connection failed"):
                    async with sse_client(params):
                        pass

        assert any("SSE client error" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_sse_client_timeout_error(self, caplog):
        """Test SSE client handling TimeoutError."""
        params = SSEParameters(url="http://localhost/sse")

        with caplog.at_level(logging.ERROR):
            with patch(
                "chuk_mcp.transports.sse.sse_client.SSETransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.side_effect = TimeoutError("Timeout")
                MockTransport.return_value = mock_transport

                with pytest.raises(TimeoutError, match="Timeout"):
                    async with sse_client(params):
                        pass

        assert any("SSE client error" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_sse_client_general_exception(self, caplog):
        """Test SSE client handling general exception."""
        params = SSEParameters(url="http://localhost/sse")

        with caplog.at_level(logging.ERROR):
            with patch(
                "chuk_mcp.transports.sse.sse_client.SSETransport"
            ) as MockTransport:
                mock_transport = AsyncMock()
                mock_transport.__aenter__.side_effect = ValueError("Invalid config")
                MockTransport.return_value = mock_transport

                with pytest.raises(ValueError, match="Invalid config"):
                    async with sse_client(params):
                        pass

        assert any("SSE client error" in record.message for record in caplog.records)


class TestCreateSseParametersFromUrl:
    """Test create_sse_parameters_from_url helper."""

    def test_create_sse_parameters_basic(self):
        """Test creating parameters with just URL."""
        params = create_sse_parameters_from_url("http://localhost/sse")

        assert params.url == "http://localhost/sse"
        assert params.bearer_token is None
        assert params.timeout == 60.0

    def test_create_sse_parameters_with_token(self):
        """Test creating parameters with bearer token."""
        params = create_sse_parameters_from_url(
            "http://localhost/sse", bearer_token="test-token"
        )

        assert params.url == "http://localhost/sse"
        assert params.bearer_token == "test-token"

    def test_create_sse_parameters_with_timeout(self):
        """Test creating parameters with custom timeout."""
        params = create_sse_parameters_from_url("http://localhost/sse", timeout=30.0)

        assert params.timeout == 30.0

    def test_create_sse_parameters_with_kwargs(self):
        """Test creating parameters with additional kwargs."""
        params = create_sse_parameters_from_url(
            "http://localhost/sse", bearer_token="token", timeout=45.0
        )

        assert params.url == "http://localhost/sse"
        assert params.bearer_token == "token"
        assert params.timeout == 45.0


class TestIsSseUrl:
    """Test is_sse_url function."""

    def test_is_sse_url_with_sse_path(self):
        """Test URL with /sse path."""
        assert is_sse_url("http://localhost/sse") is True

    def test_is_sse_url_with_events(self):
        """Test URL with events in path."""
        assert is_sse_url("http://localhost/events") is True

    def test_is_sse_url_with_stream(self):
        """Test URL with stream in path."""
        assert is_sse_url("http://localhost/stream") is True

    def test_is_sse_url_with_port_8080(self):
        """Test URL with port 8080."""
        assert is_sse_url("http://localhost:8080/api") is True

    def test_is_sse_url_with_port_3000(self):
        """Test URL with port 3000."""
        assert is_sse_url("http://localhost:3000/api") is True

    def test_is_sse_url_empty_string(self):
        """Test with empty string."""
        assert is_sse_url("") is False

    def test_is_sse_url_none(self):
        """Test with None."""
        assert is_sse_url(None) is False

    def test_is_sse_url_no_indicators(self):
        """Test URL without SSE indicators."""
        assert is_sse_url("http://localhost:80/api") is False

    def test_is_sse_url_case_insensitive(self):
        """Test that URL checking is case insensitive."""
        assert is_sse_url("http://localhost/SSE") is True
        assert is_sse_url("http://localhost/EVENTS") is True
        assert is_sse_url("http://localhost/STREAM") is True

    def test_is_sse_url_mixed_indicators(self):
        """Test URL with multiple indicators."""
        assert is_sse_url("http://localhost:8080/sse/events") is True

    def test_is_sse_url_substring_match(self):
        """Test that indicators match as substrings."""
        assert is_sse_url("http://localhost/mysse") is False  # "/sse" != "mysse"
        assert is_sse_url("http://localhost/eventsapi") is True  # contains "events"


class TestTrySseWithFallback:
    """Test try_sse_with_fallback function."""

    @pytest.mark.asyncio
    async def test_try_sse_success(self):
        """Test successful SSE connection."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            await try_sse_with_fallback("http://localhost/sse")
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_sse_404_error(self):
        """Test SSE fallback with 404 error."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("Not found - 404")

            with pytest.raises(Exception, match="SSE endpoint not found"):
                await try_sse_with_fallback("http://localhost/sse")

    @pytest.mark.asyncio
    async def test_try_sse_not_found_error(self):
        """Test SSE fallback with 'not found' error."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("Endpoint not found")

            with pytest.raises(Exception, match="migrated to Streamable HTTP"):
                await try_sse_with_fallback("http://localhost/sse")

    @pytest.mark.asyncio
    async def test_try_sse_405_error(self):
        """Test SSE fallback with 405 error."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("Method not allowed - 405")

            with pytest.raises(Exception, match="SSE transport not supported"):
                await try_sse_with_fallback("http://localhost/sse")

    @pytest.mark.asyncio
    async def test_try_sse_method_not_allowed_error(self):
        """Test SSE fallback with 'method not allowed' error."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("Method not allowed")

            with pytest.raises(Exception, match="only support Streamable HTTP"):
                await try_sse_with_fallback("http://localhost/sse")

    @pytest.mark.asyncio
    async def test_try_sse_general_error(self):
        """Test SSE fallback with general error."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = ValueError("Some other error")

            with pytest.raises(ValueError, match="Some other error"):
                await try_sse_with_fallback("http://localhost/sse")

    @pytest.mark.asyncio
    async def test_try_sse_with_bearer_token(self):
        """Test with bearer token parameter."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            await try_sse_with_fallback(
                "http://localhost/sse", bearer_token="test-token"
            )

            # Verify parameters were passed correctly
            call_args = mock_client.call_args[0][0]
            assert call_args.bearer_token == "test-token"

    @pytest.mark.asyncio
    async def test_try_sse_with_custom_timeout(self):
        """Test with custom timeout."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            await try_sse_with_fallback("http://localhost/sse", timeout=120.0)

            # Verify timeout was passed
            call_args = mock_client.call_args[0][0]
            assert call_args.timeout == 120.0

    @pytest.mark.asyncio
    async def test_try_sse_with_all_params(self):
        """Test with all parameters."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            await try_sse_with_fallback(
                "http://localhost/sse", bearer_token="my-token", timeout=90.0
            )

            call_args = mock_client.call_args[0][0]
            assert call_args.url == "http://localhost/sse"
            assert call_args.bearer_token == "my-token"
            assert call_args.timeout == 90.0

    @pytest.mark.asyncio
    async def test_try_sse_error_chain(self):
        """Test that original error is chained."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            original_error = Exception("404 Not Found")
            mock_client.side_effect = original_error

            try:
                await try_sse_with_fallback("http://localhost/sse")
            except Exception as e:
                assert e.__cause__ is original_error

    @pytest.mark.asyncio
    async def test_try_sse_migration_guidance_404(self):
        """Test migration guidance for 404 errors."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("404")

            with pytest.raises(Exception) as exc_info:
                await try_sse_with_fallback("http://localhost/sse")

            error_msg = str(exc_info.value)
            assert "migrated to Streamable HTTP" in error_msg
            assert "Try using the Streamable HTTP transport" in error_msg

    @pytest.mark.asyncio
    async def test_try_sse_migration_guidance_405(self):
        """Test migration guidance for 405 errors."""
        with patch("chuk_mcp.transports.sse.sse_client.sse_client") as mock_client:
            mock_client.side_effect = Exception("405")

            with pytest.raises(Exception) as exc_info:
                await try_sse_with_fallback("http://localhost/sse")

            error_msg = str(exc_info.value)
            assert "SSE transport not supported" in error_msg
            assert "only support Streamable HTTP" in error_msg
            assert "updating your client" in error_msg


class TestSseClientDeprecation:
    """Test SSE client deprecation notices."""

    @pytest.mark.asyncio
    async def test_sse_client_deprecation_notice_in_docstring(self):
        """Test that deprecation notice is in docstring."""
        docstring = sse_client.__doc__
        assert "DEPRECATION NOTICE" in docstring
        assert "2025-03-26" in docstring
        assert "backwards compatibility" in docstring

    def test_create_sse_parameters_callable(self):
        """Test that create_sse_parameters_from_url is callable."""
        assert callable(create_sse_parameters_from_url)

    def test_is_sse_url_callable(self):
        """Test that is_sse_url is callable."""
        assert callable(is_sse_url)

    def test_try_sse_with_fallback_callable(self):
        """Test that try_sse_with_fallback is callable."""
        assert callable(try_sse_with_fallback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
