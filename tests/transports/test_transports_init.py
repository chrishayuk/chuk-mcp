"""Tests for transports/__init__.py module."""

import pytest
from unittest.mock import patch, MagicMock
from chuk_mcp.transports import (
    Transport,
    TransportParameters,
    StdioTransport,
    StdioParameters,
    stdio_client,
    HAS_HTTP,
    HAS_SSE,
    get_available_transports,
    create_transport,
    create_client,
)


class TestTransportImports:
    """Test that all transports are importable."""

    def test_base_imports(self):
        """Test base classes are imported."""
        assert Transport is not None
        assert TransportParameters is not None

    def test_stdio_imports(self):
        """Test stdio transport is always available."""
        assert StdioTransport is not None
        assert StdioParameters is not None
        assert stdio_client is not None

    def test_http_availability(self):
        """Test HTTP availability flag."""
        assert isinstance(HAS_HTTP, bool)

    def test_sse_availability(self):
        """Test SSE availability flag."""
        assert isinstance(HAS_SSE, bool)


class TestGetAvailableTransports:
    """Test get_available_transports function."""

    def test_stdio_always_available(self):
        """Test stdio is always in available transports."""
        available = get_available_transports()
        assert "stdio" in available

    def test_includes_http_when_available(self):
        """Test HTTP is included when available."""
        if HAS_HTTP:
            available = get_available_transports()
            assert "http" in available

    def test_includes_sse_when_available(self):
        """Test SSE is included when available."""
        if HAS_SSE:
            available = get_available_transports()
            assert "sse" in available


class TestCreateTransport:
    """Test create_transport factory function."""

    def test_create_stdio_transport(self):
        """Test creating stdio transport."""
        params = StdioParameters(command="test", args=["arg1"])
        transport = create_transport("stdio", params)
        assert isinstance(transport, StdioTransport)

    @pytest.mark.skipif(not HAS_HTTP, reason="HTTP transport not available")
    def test_create_http_transport(self):
        """Test creating HTTP transport."""
        from chuk_mcp.transports import HTTPTransport, HTTPParameters

        params = HTTPParameters(url="http://localhost:3000")
        transport = create_transport("http", params)
        assert isinstance(transport, HTTPTransport)

    @pytest.mark.skipif(not HAS_SSE, reason="SSE transport not available")
    def test_create_sse_transport(self):
        """Test creating SSE transport."""
        from chuk_mcp.transports import SSETransport, SSEParameters

        params = SSEParameters(url="http://localhost:3000")
        transport = create_transport("sse", params)
        assert isinstance(transport, SSETransport)

    def test_create_unknown_transport(self):
        """Test creating unknown transport raises ValueError."""
        params = StdioParameters(command="test", args=[])
        with pytest.raises(ValueError, match="Unknown transport type"):
            create_transport("unknown", params)

    @patch("chuk_mcp.transports.HAS_HTTP", False)
    def test_create_http_when_not_available(self):
        """Test creating HTTP transport when not available raises error."""
        params = MagicMock()
        with pytest.raises(ValueError, match="HTTP transport not available"):
            create_transport("http", params)

    @patch("chuk_mcp.transports.HAS_SSE", False)
    def test_create_sse_when_not_available(self):
        """Test creating SSE transport when not available raises error."""
        params = MagicMock()
        with pytest.raises(ValueError, match="SSE transport not available"):
            create_transport("sse", params)


class TestCreateClient:
    """Test create_client factory function."""

    @pytest.mark.asyncio
    async def test_create_stdio_client(self):
        """Test creating stdio client."""
        params = StdioParameters(command="python", args=["-c", "pass"])
        client_cm = create_client("stdio", params)
        assert client_cm is not None

    @pytest.mark.skipif(not HAS_HTTP, reason="HTTP transport not available")
    def test_create_http_client(self):
        """Test creating HTTP client."""
        from chuk_mcp.transports import HTTPParameters

        params = HTTPParameters(url="http://localhost:3000")
        client_cm = create_client("http", params)
        assert client_cm is not None

    @pytest.mark.skipif(not HAS_SSE, reason="SSE transport not available")
    def test_create_sse_client(self):
        """Test creating SSE client."""
        from chuk_mcp.transports import SSEParameters

        params = SSEParameters(url="http://localhost:3000")
        client_cm = create_client("sse", params)
        assert client_cm is not None

    def test_create_client_unknown_transport(self):
        """Test creating client with unknown transport raises ValueError."""
        params = StdioParameters(command="test", args=[])
        with pytest.raises(ValueError, match="Unknown transport type"):
            create_client("unknown", params)

    @patch("chuk_mcp.transports.HAS_HTTP", False)
    def test_create_http_client_when_not_available(self):
        """Test creating HTTP client when not available raises error."""
        params = MagicMock()
        with pytest.raises(ValueError, match="HTTP transport not available"):
            create_client("http", params)

    @patch("chuk_mcp.transports.HAS_SSE", False)
    def test_create_sse_client_when_not_available(self):
        """Test creating SSE client when not available raises error."""
        params = MagicMock()
        with pytest.raises(ValueError, match="SSE transport not available"):
            create_client("sse", params)


class TestImportErrorHandling:
    """Test import error handling for optional transports."""

    def test_http_availability_flag_exists(self):
        """Test that HAS_HTTP flag exists."""
        # Just verify the flag exists and is a boolean
        assert isinstance(HAS_HTTP, bool)
        # The actual value depends on whether httpx is installed

    def test_sse_availability_flag_exists(self):
        """Test that HAS_SSE flag exists."""
        # Just verify the flag exists and is a boolean
        assert isinstance(HAS_SSE, bool)
        # The actual value depends on whether httpx is installed
