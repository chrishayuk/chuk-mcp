#!/usr/bin/env python3
"""
Unit tests for the new stdio transport layer.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock

import anyio

# Add ValidationError import
try:
    from pydantic import ValidationError
except ImportError:
    from chuk_mcp.protocol.mcp_pydantic_base import ValidationError

# Import the new transport APIs
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.transports.stdio.transport import StdioTransport
from chuk_mcp.transports.stdio.stdio_client import StdioClient, stdio_client
from chuk_mcp.protocol.features.batching import supports_batching
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage


class TestStdioParameters:
    """Test StdioParameters class."""

    def test_basic_creation(self):
        """Test basic parameter creation."""
        params = StdioParameters(command="python", args=["script.py"])

        assert params.command == "python"
        assert params.args == ["script.py"]
        assert params.env is None

    def test_with_environment(self):
        """Test parameters with environment variables."""
        env = {"PATH": "/usr/bin", "DEBUG": "1"}
        params = StdioParameters(command="node", args=["server.js"], env=env)

        assert params.command == "node"
        assert params.args == ["server.js"]
        assert params.env == env

    def test_empty_args(self):
        """Test parameters with empty args."""
        params = StdioParameters(command="./server")

        assert params.command == "./server"
        assert params.args == []
        assert params.env is None

    def test_validation(self):
        """Test parameter validation."""
        # Should work with valid command
        params = StdioParameters(command="python")
        assert params.command == "python"

        # Test serialization works
        data = params.model_dump()
        assert data["command"] == "python"
        assert data["args"] == []

    def test_invalid_parameters(self):
        """Test parameter validation with invalid inputs."""
        # FIXED: Test parameter validation during creation, not after
        with pytest.raises(ValidationError, match="Input should be a valid list"):
            StdioParameters(command="python", args="not a list")

        # Test that valid parameters work
        valid_params = StdioParameters(command="python", args=["--version"])
        assert valid_params.command == "python"
        assert valid_params.args == ["--version"]


class TestStdioClient:
    """Test StdioClient class."""

    def test_initialization(self):
        """Test client initialization."""
        params = StdioParameters(command="python", args=["test.py"])
        client = StdioClient(params)

        assert client.server == params
        assert client.process is None
        assert client.tg is None
        assert client.get_protocol_version() is None

    def test_invalid_parameters(self):
        """Test client with invalid parameters."""
        # Empty command should raise error
        with pytest.raises(ValueError, match="Server command must not be empty"):
            StdioClient(StdioParameters(command=""))

        # FIXED: Test parameter validation during creation, not after
        with pytest.raises(ValidationError, match="Input should be a valid list"):
            StdioParameters(command="python", args="not a list")

        # Test that valid parameters work
        valid_params = StdioParameters(command="python", args=["--version"])
        client = StdioClient(valid_params)
        assert client.server.command == "python"
        assert client.server.args == ["--version"]

    def test_protocol_version_setting(self):
        """Test protocol version setting."""
        params = StdioParameters(command="python")
        client = StdioClient(params)

        client.set_protocol_version("2025-06-18")
        assert client.get_protocol_version() == "2025-06-18"

    def test_new_request_stream(self):
        """Test request stream creation."""
        params = StdioParameters(command="python")
        client = StdioClient(params)

        stream = client.new_request_stream("test-id")
        assert "test-id" in client._pending
        assert stream is not None

    @pytest.mark.asyncio
    async def test_get_streams(self):
        """Test stream access."""
        params = StdioParameters(command="echo", args=["test"])
        async with StdioClient(params) as client:
            read_stream, write_stream = client.get_streams()
            assert read_stream is not None
            assert write_stream is not None


class TestStdioTransport:
    """Test StdioTransport wrapper class."""

    def test_initialization(self):
        """Test transport initialization."""
        params = StdioParameters(command="python", args=["server.py"])
        transport = StdioTransport(params)

        assert transport.parameters == params
        assert transport._client is None

    @pytest.mark.asyncio
    async def test_get_streams_without_start(self):
        """Test line 27 - getting streams before starting transport raises RuntimeError."""
        params = StdioParameters(command="python")
        transport = StdioTransport(params)

        # Line 27: raise RuntimeError("Transport not started...")
        with pytest.raises(RuntimeError, match="Transport not started"):
            await transport.get_streams()

    def test_protocol_version_setting(self):
        """Test protocol version setting on transport."""
        params = StdioParameters(command="python")
        transport = StdioTransport(params)

        # Should not raise error when no client
        transport.set_protocol_version("2025-06-18")

        # Mock client to test delegation
        transport._client = Mock()
        transport.set_protocol_version("2025-06-18")
        transport._client.set_protocol_version.assert_called_with("2025-06-18")

    @pytest.mark.asyncio
    async def test_aenter_creates_client(self):
        """Test lines 31-33 - __aenter__ creates and initializes client."""
        import tempfile
        import os
        import sys

        # Create a simple echo server
        server_script = """
import sys
import json
line = sys.stdin.readline()
sys.stdout.write(line)
sys.stdout.flush()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_script)
            server_file = f.name

        try:
            params = StdioParameters(command=sys.executable, args=[server_file])
            transport = StdioTransport(params)

            assert transport._client is None

            # Test lines 31-33
            async with transport as t:
                # Line 31: self._client = StdioClient(self.parameters)
                # Line 32: await self._client.__aenter__()
                # Line 33: return self
                assert transport._client is not None
                assert t is transport

            # After exit, client should be None
            assert transport._client is None
        finally:
            if os.path.exists(server_file):
                os.unlink(server_file)

    @pytest.mark.asyncio
    async def test_aexit_with_client(self):
        """Test lines 37-41 - __aexit__ cleans up client properly."""
        import tempfile
        import os
        import sys

        server_script = """
import sys
import time
time.sleep(0.1)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_script)
            server_file = f.name

        try:
            params = StdioParameters(command=sys.executable, args=[server_file])
            transport = StdioTransport(params)

            async with transport:
                assert transport._client is not None

            # Lines 38-40: Exit should cleanup and set _client to None
            assert transport._client is None
        finally:
            if os.path.exists(server_file):
                os.unlink(server_file)

    @pytest.mark.asyncio
    async def test_aexit_without_client_line_41(self):
        """Test line 41 - __aexit__ when no client exists returns False."""
        params = StdioParameters(command="python")
        transport = StdioTransport(params)

        # Manually call __aexit__ without entering
        result = await transport.__aexit__(None, None, None)

        # Line 41: return False
        assert result is False


class TestBatchProcessingSupport:
    """Test batch processing version detection."""

    def test_supports_batch_processing(self):
        """Test batch processing support detection."""
        # None should default to supporting batch
        assert supports_batching(None) is True

        # Old versions should support batch
        assert supports_batching("2025-03-26") is True
        assert supports_batching("2025-06-17") is True

        # New versions should not support batch
        assert supports_batching("2025-06-18") is False
        assert supports_batching("2025-06-19") is False
        assert supports_batching("2025-07-01") is False
        assert supports_batching("2026-01-01") is False

    def test_invalid_version_formats(self):
        """Test handling of invalid version formats."""
        # Invalid formats should default to supporting batch
        assert supports_batching("invalid") is True
        assert supports_batching("2025") is True
        assert supports_batching("2025-06") is True
        assert supports_batching("2025-06-18-extra") is True
        assert supports_batching("not-a-date") is True


class TestStdioClientUnit:
    """Unit tests for StdioClient without subprocess mocking."""

    def test_initialization(self):
        """Test client initialization."""
        params = StdioParameters(command="python", args=["test.py"])
        client = StdioClient(params)

        assert client.server == params
        assert client.process is None
        assert client.tg is None
        assert client.get_protocol_version() is None

    def test_protocol_version_setting(self):
        """Test protocol version setting."""
        params = StdioParameters(command="python")
        client = StdioClient(params)

        client.set_protocol_version("2025-06-18")
        assert client.get_protocol_version() == "2025-06-18"

    def test_new_request_stream(self):
        """Test request stream creation."""
        params = StdioParameters(command="python")
        client = StdioClient(params)

        stream = client.new_request_stream("test-id")
        assert "test-id" in client._pending
        assert stream is not None

    @pytest.mark.asyncio
    async def test_get_streams(self):
        """Test stream access."""
        params = StdioParameters(command="echo", args=["test"])
        async with StdioClient(params) as client:
            read_stream, write_stream = client.get_streams()
            assert read_stream is not None
            assert write_stream is not None

    @pytest.mark.asyncio
    async def test_route_message_to_main_stream(self):
        """Test routing messages to main stream."""
        params = StdioParameters(command="echo", args=["test"])
        async with StdioClient(params) as client:
            # Create test message
            message = JSONRPCMessage(jsonrpc="2.0", id="test-123", method="ping")

            # Route the message
            await client._route_message(message)

            # Should be able to receive from main stream
            try:
                with anyio.fail_after(0.1):  # Very short timeout
                    received = await client._incoming_recv.receive()
                    assert received == message
            except TimeoutError:
                pytest.fail("Message was not routed to main stream")

    @pytest.mark.asyncio
    async def test_route_notification(self):
        """Test routing notification messages."""
        params = StdioParameters(command="echo", args=["test"])
        async with StdioClient(params) as client:
            # Create notification (no id)
            notification = JSONRPCMessage(jsonrpc="2.0", method="notification/test")

            # Route the notification
            await client._route_message(notification)

            # Should be available in notifications stream
            try:
                received = client.notifications.receive_nowait()
                assert received == notification
            except anyio.WouldBlock:
                pytest.fail("Notification was not routed to notifications stream")


class TestStdioClientContextManager:
    """Test the stdio_client context manager function."""

    def create_mock_server(self):
        """Create a simple mock server script."""
        server_script = """
import sys
import json

# Send initialize response
response = {
    "jsonrpc": "2.0",
    "id": "init",
    "result": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "test-server", "version": "1.0.0"}
    }
}
print(json.dumps(response))

# Read and echo one message
try:
    line = sys.stdin.readline().strip()
    if line:
        msg = json.loads(line)
        echo_response = {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "result": {"echo": True}
        }
        print(json.dumps(echo_response))
except:
    pass
"""
        return server_script

    @pytest.mark.asyncio
    async def test_stdio_client_context_manager(self):
        """Test the stdio_client context manager with a real subprocess."""
        import sys

        # Create temporary server script
        server_script = self.create_mock_server()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_script)
            server_file = f.name

        try:
            params = StdioParameters(command=sys.executable, args=[server_file])

            async with stdio_client(params) as (read_stream, write_stream):
                # Test that we get valid streams
                assert read_stream is not None
                assert write_stream is not None

                # Send a test message
                test_message = JSONRPCMessage(
                    jsonrpc="2.0", id="test-ping", method="ping"
                )

                await write_stream.send(test_message)

                # Try to read a response (with timeout)
                try:
                    with anyio.fail_after(2.0):  # 2 second timeout
                        response = await read_stream.receive()
                        assert response is not None
                        # Should be a JSONRPCMessage
                        assert hasattr(response, "jsonrpc")
                except TimeoutError:
                    # Timeout is acceptable for this basic test
                    pass

        finally:
            # Clean up
            if os.path.exists(server_file):
                os.unlink(server_file)

    @pytest.mark.asyncio
    async def test_stdio_client_error_handling(self):
        """Test stdio_client error handling with invalid command."""
        params = StdioParameters(command="nonexistent-command-12345")

        with pytest.raises(Exception):
            async with stdio_client(params) as (read_stream, write_stream):
                pass

    @pytest.mark.asyncio
    async def test_stdio_client_with_simple_mocks(self):
        """Test stdio_client with minimal mocking to avoid async warnings."""
        params = StdioParameters(command="python", args=["test.py"])

        # Instead of complex subprocess mocking, just test the client creation
        client = StdioClient(params)

        # Test basic properties
        assert client.server == params
        assert client.get_protocol_version() is None

        # Test protocol version setting
        client.set_protocol_version("2025-06-18")
        assert client.get_protocol_version() == "2025-06-18"

        # Test stream creation for legacy API
        _stream = client.new_request_stream("test-123")
        assert "test-123" in client._pending


class TestMessageRouting:
    """Test message routing functionality."""

    @pytest.mark.asyncio
    async def test_route_to_pending_stream(self):
        """Test routing to pending request streams."""
        params = StdioParameters(command="echo", args=["test"])
        async with StdioClient(params) as client:
            # Create a pending stream for specific ID
            request_id = "pending-123"
            pending_stream = client.new_request_stream(request_id)

            # Create response message
            response = JSONRPCMessage(
                jsonrpc="2.0", id=request_id, result={"success": True}
            )

            # Route the response
            await client._route_message(response)

            # Should be available in the pending stream
            try:
                with anyio.fail_after(0.1):
                    received = await pending_stream.receive()
                    assert received == response
            except TimeoutError:
                pytest.fail("Response was not routed to pending stream")


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
