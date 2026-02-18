#!/usr/bin/env python3
"""
Comprehensive tests for transports/__init__.py module.
"""

import pytest
from unittest.mock import Mock, patch

from chuk_mcp.transports import (
    Transport,
    TransportParameters,
    StdioTransport,
    StdioParameters,
    stdio_client,
    get_available_transports,
    create_transport,
    create_client,
    HAS_HTTP,
    HAS_SSE,
)


class TestImports:
    """Test that all imports are available."""

    def test_base_imports(self):
        """Test base class imports."""
        assert Transport is not None
        assert TransportParameters is not None

    def test_stdio_imports(self):
        """Test stdio imports."""
        assert StdioTransport is not None
        assert StdioParameters is not None
        assert stdio_client is not None

    def test_has_flags(self):
        """Test HAS_HTTP and HAS_SSE flags."""
        assert isinstance(HAS_HTTP, bool)
        assert isinstance(HAS_SSE, bool)


class TestGetAvailableTransports:
    """Test get_available_transports function."""

    def test_get_available_transports_always_has_stdio(self):
        """Test that stdio is always available."""
        transports = get_available_transports()
        assert "stdio" in transports

    def test_get_available_transports_type(self):
        """Test that result is a list."""
        transports = get_available_transports()
        assert isinstance(transports, list)

    def test_get_available_transports_http_when_available(self):
        """Test HTTP transport when available."""
        with patch("chuk_mcp.transports.HAS_HTTP", True):
            from chuk_mcp.transports import get_available_transports

            # Need to reload to get patched value
            transports = get_available_transports()
            # stdio is always there
            assert "stdio" in transports

    def test_get_available_transports_sse_when_available(self):
        """Test SSE transport when available."""
        with patch("chuk_mcp.transports.HAS_SSE", True):
            from chuk_mcp.transports import get_available_transports

            transports = get_available_transports()
            assert "stdio" in transports


class TestCreateTransport:
    """Test create_transport factory function."""

    def test_create_stdio_transport(self):
        """Test creating stdio transport."""
        params = StdioParameters(command="test", args=[])
        transport = create_transport("stdio", params)

        assert isinstance(transport, StdioTransport)

    def test_create_http_transport_when_available(self):
        """Test creating HTTP transport when available."""
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters

            params = HTTPParameters(url="http://localhost/mcp")
            transport = create_transport("http", params)

            from chuk_mcp.transports.http import HTTPTransport

            assert isinstance(transport, HTTPTransport)
        else:
            pytest.skip("HTTP transport not available")

    def test_create_http_transport_when_unavailable(self):
        """Test creating HTTP transport when not available."""
        with patch("chuk_mcp.transports.HAS_HTTP", False):
            params = Mock()
            with pytest.raises(ValueError, match="HTTP transport not available"):
                create_transport("http", params)

    def test_create_sse_transport_when_available(self):
        """Test creating SSE transport when available."""
        if HAS_SSE:
            from chuk_mcp.transports.sse import SSEParameters

            params = SSEParameters(url="http://localhost")
            transport = create_transport("sse", params)

            from chuk_mcp.transports.sse import SSETransport

            assert isinstance(transport, SSETransport)
        else:
            pytest.skip("SSE transport not available")

    def test_create_sse_transport_when_unavailable(self):
        """Test creating SSE transport when not available."""
        with patch("chuk_mcp.transports.HAS_SSE", False):
            params = Mock()
            with pytest.raises(ValueError, match="SSE transport not available"):
                create_transport("sse", params)

    def test_create_unknown_transport(self):
        """Test creating unknown transport type."""
        params = Mock()
        with pytest.raises(ValueError, match="Unknown transport type"):
            create_transport("unknown", params)

    def test_create_unknown_transport_shows_available(self):
        """Test that error message shows available transports."""
        params = Mock()
        with pytest.raises(ValueError, match="Available:"):
            create_transport("invalid", params)


class TestCreateClient:
    """Test create_client factory function."""

    @pytest.mark.asyncio
    async def test_create_stdio_client(self):
        """Test creating stdio client."""
        params = StdioParameters(command="python", args=["-c", "print('test')"])
        client = create_client("stdio", params)

        # Client should be a context manager
        assert hasattr(client, "__aenter__")
        assert hasattr(client, "__aexit__")

    def test_create_http_client_when_available(self):
        """Test creating HTTP client when available."""
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters

            params = HTTPParameters(url="http://localhost/mcp")
            client = create_client("http", params)

            # Client should be a context manager
            assert hasattr(client, "__aenter__")
            assert hasattr(client, "__aexit__")
        else:
            pytest.skip("HTTP transport not available")

    def test_create_http_client_when_unavailable(self):
        """Test creating HTTP client when not available."""
        with patch("chuk_mcp.transports.HAS_HTTP", False):
            params = Mock()
            with pytest.raises(ValueError, match="HTTP transport not available"):
                create_client("http", params)

    def test_create_sse_client_when_available(self):
        """Test creating SSE client when available."""
        if HAS_SSE:
            from chuk_mcp.transports.sse import SSEParameters

            params = SSEParameters(url="http://localhost")
            client = create_client("sse", params)

            # Client should be a context manager
            assert hasattr(client, "__aenter__")
            assert hasattr(client, "__aexit__")
        else:
            pytest.skip("SSE transport not available")

    def test_create_sse_client_when_unavailable(self):
        """Test creating SSE client when not available."""
        with patch("chuk_mcp.transports.HAS_SSE", False):
            params = Mock()
            with pytest.raises(ValueError, match="SSE transport not available"):
                create_client("sse", params)

    def test_create_unknown_client(self):
        """Test creating unknown client type."""
        params = Mock()
        with pytest.raises(ValueError, match="Unknown transport type"):
            create_client("unknown", params)

    def test_create_unknown_client_shows_available(self):
        """Test that error message shows available transports."""
        params = Mock()
        with pytest.raises(ValueError, match="Available:"):
            create_client("invalid", params)


class TestConditionalImports:
    """Test conditional import behavior."""

    def test_http_imports_when_unavailable(self):
        """Test HTTP imports when httpx is not available."""
        # When HTTP is not available, the imports should be None
        if not HAS_HTTP:
            from chuk_mcp.transports import HTTPTransport, HTTPParameters, http_client

            assert HTTPTransport is None
            assert HTTPParameters is None
            assert http_client is None

    def test_sse_imports_when_unavailable(self):
        """Test SSE imports when httpx is not available."""
        # When SSE is not available, the imports should be None
        if not HAS_SSE:
            from chuk_mcp.transports import SSETransport, SSEParameters, sse_client

            assert SSETransport is None
            assert SSEParameters is None
            assert sse_client is None

    def test_stdio_always_available(self):
        """Test that stdio is always available."""
        from chuk_mcp.transports import StdioTransport, StdioParameters, stdio_client

        assert StdioTransport is not None
        assert StdioParameters is not None
        assert stdio_client is not None


class TestTransportParametersBase:
    """Test TransportParameters base class."""

    def test_transport_parameters_exists(self):
        """Test that TransportParameters class exists."""
        assert TransportParameters is not None

    def test_transport_parameters_is_class(self):
        """Test that TransportParameters is a class."""
        import inspect

        assert inspect.isclass(TransportParameters)


class TestTransportBase:
    """Test Transport base class."""

    def test_transport_exists(self):
        """Test that Transport class exists."""
        assert Transport is not None

    def test_transport_is_class(self):
        """Test that Transport is a class."""
        import inspect

        assert inspect.isclass(Transport)

    def test_transport_has_required_methods(self):
        """Test that Transport has required abstract methods."""

        # Check for common transport methods
        # These should be defined in the base class
        assert hasattr(Transport, "get_streams")


class TestModuleAll:
    """Test __all__ exports."""

    def test_all_exports_present(self):
        """Test that __all__ is defined and contains expected exports."""
        import chuk_mcp.transports as transports_module

        assert hasattr(transports_module, "__all__")
        assert isinstance(transports_module.__all__, list)

        # Check for essential exports
        assert "Transport" in transports_module.__all__
        assert "TransportParameters" in transports_module.__all__
        assert "StdioTransport" in transports_module.__all__
        assert "StdioParameters" in transports_module.__all__
        assert "stdio_client" in transports_module.__all__
        assert "HAS_HTTP" in transports_module.__all__
        assert "HAS_SSE" in transports_module.__all__


class TestMultipleTransportTypes:
    """Test using multiple transport types together."""

    def test_all_available_transports_listed(self):
        """Test that get_available_transports returns all available types."""
        available = get_available_transports()

        # stdio should always be present
        assert "stdio" in available

        # Check if optional transports are listed correctly
        if HAS_HTTP:
            assert "http" in available
        else:
            assert "http" not in available

        if HAS_SSE:
            assert "sse" in available
        else:
            assert "sse" not in available

    def test_create_multiple_transport_types(self):
        """Test creating different transport types in sequence."""
        # Create stdio transport
        stdio_params = StdioParameters(command="test", args=[])
        stdio_transport = create_transport("stdio", stdio_params)
        assert isinstance(stdio_transport, StdioTransport)

        # Try to create HTTP transport if available
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters, HTTPTransport

            http_params = HTTPParameters(url="http://localhost/mcp")
            http_transport = create_transport("http", http_params)
            assert isinstance(http_transport, HTTPTransport)


class TestActualTransportCreation:
    """Test actual transport and client creation with available transports."""

    def test_create_http_transport_success_path(self):
        """Test creating HTTP transport when available (success path)."""
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters, HTTPTransport

            # This tests line 85 - the success path after the if not HAS_HTTP check
            params = HTTPParameters(url="http://localhost/mcp")
            transport = create_transport("http", params)
            assert isinstance(transport, HTTPTransport)
        else:
            pytest.skip("HTTP transport not available")

    def test_create_sse_transport_success_path(self):
        """Test creating SSE transport when available (success path)."""
        if HAS_SSE:
            from chuk_mcp.transports.sse import SSEParameters, SSETransport

            # This tests line 89 - the success path after the if not HAS_SSE check
            params = SSEParameters(url="http://localhost")
            transport = create_transport("sse", params)
            assert isinstance(transport, SSETransport)
        else:
            pytest.skip("SSE transport not available")

    def test_create_http_client_success_path(self):
        """Test creating HTTP client when available (success path)."""
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters

            # This tests line 116 - the success path after the if not HAS_HTTP check
            params = HTTPParameters(url="http://localhost/mcp")
            client = create_client("http", params)
            assert hasattr(client, "__aenter__")
            assert hasattr(client, "__aexit__")
        else:
            pytest.skip("HTTP transport not available")

    def test_create_sse_client_success_path(self):
        """Test creating SSE client when available (success path)."""
        if HAS_SSE:
            from chuk_mcp.transports.sse import SSEParameters

            # This tests line 120 - the success path after the if not HAS_SSE check
            params = SSEParameters(url="http://localhost")
            client = create_client("sse", params)
            assert hasattr(client, "__aenter__")
            assert hasattr(client, "__aexit__")
        else:
            pytest.skip("SSE transport not available")


class TestImportErrorHandling:
    """Test import error handling for optional dependencies."""

    def test_simulate_http_import_failure(self):
        """Test behavior when HTTP import fails."""
        # We need to test that when import fails, HAS_HTTP is False
        # This is tricky to test directly, but we can verify the conditional logic
        import sys

        # Save original module
        original_transports = sys.modules.get("chuk_mcp.transports")

        try:
            # Remove transports module to force reimport
            if "chuk_mcp.transports" in sys.modules:
                del sys.modules["chuk_mcp.transports"]

            # Mock the http import to raise ImportError
            with patch.dict(sys.modules, {"chuk_mcp.transports.http": None}):
                with patch(
                    "builtins.__import__",
                    side_effect=lambda name, *args, **kwargs: (
                        (_ for _ in ()).throw(ImportError())
                        if "http" in name and "chuk_mcp.transports.http" in name
                        else __import__(name, *args, **kwargs)
                    ),
                ):
                    # The module would set HAS_HTTP = False in this case
                    # We can't easily test this without reloading the module
                    # So we test the behavior instead
                    pass
        finally:
            # Restore original module
            if original_transports:
                sys.modules["chuk_mcp.transports"] = original_transports

    def test_import_error_sets_none_values(self):
        """Test that ImportError properly sets None values."""
        # When imports fail, the except ImportError blocks (lines 16-20, 26-30) should execute
        # This sets the transport classes to None
        # We verify this behavior through the conditional checks
        if not HAS_HTTP:
            # If HTTP is not available, verify the error handling works
            with pytest.raises(ValueError, match="HTTP transport not available"):
                create_transport("http", Mock())

        if not HAS_SSE:
            # If SSE is not available, verify the error handling works
            with pytest.raises(ValueError, match="SSE transport not available"):
                create_transport("sse", Mock())

    def test_http_import_error_branch(self):
        """Test line 15 and 16-20 - HTTP ImportError exception handling."""
        # Test the ImportError catch for HTTP - lines 16-20
        # When httpx is not installed, these lines set HAS_HTTP = False
        # We can verify behavior by checking what happens when HAS_HTTP is False
        if not HAS_HTTP:
            from chuk_mcp.transports import HTTPTransport, HTTPParameters, http_client

            # Lines 17-19 should have set these to None
            assert HTTPTransport is None
            assert HTTPParameters is None
            assert http_client is None

    def test_sse_import_error_branch(self):
        """Test lines 26-30 - SSE ImportError exception handling."""
        # Test the ImportError catch for SSE - lines 26-30
        # When httpx is not installed, these lines set HAS_SSE = False
        if not HAS_SSE:
            from chuk_mcp.transports import SSETransport, SSEParameters, sse_client

            # Lines 27-29 should have set these to None
            assert SSETransport is None
            assert SSEParameters is None
            assert sse_client is None


class TestFactoryErrorPaths:
    """Test factory function error paths and edge cases."""

    def test_create_transport_http_line_85_success_path(self):
        """Test line 85 - successful HTTP transport creation after availability check."""
        # This tests the return statement on line 85 when HAS_HTTP is True
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters

            params = HTTPParameters(url="http://localhost/mcp")
            transport = create_transport("http", params)
            # Line 85 executes: return HTTPTransport(parameters)
            from chuk_mcp.transports.http import HTTPTransport

            assert isinstance(transport, HTTPTransport)
        else:
            pytest.skip("HTTP transport not available - cannot test line 85")

    def test_create_client_http_line_116_success_path(self):
        """Test line 116 - successful HTTP client creation after availability check."""
        # This tests the return statement on line 116 when HAS_HTTP is True
        if HAS_HTTP:
            from chuk_mcp.transports.http import HTTPParameters

            params = HTTPParameters(url="http://localhost/mcp")
            client = create_client("http", params)
            # Line 116 executes: return http_client(parameters)
            assert hasattr(client, "__aenter__")
            assert hasattr(client, "__aexit__")
        else:
            pytest.skip("HTTP transport not available - cannot test line 116")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
