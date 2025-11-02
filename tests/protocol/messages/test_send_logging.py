#!/usr/bin/env python3
"""
Comprehensive tests for logging message functions.
"""

import pytest
from unittest.mock import AsyncMock, patch
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.protocol.messages.logging.send_messages import (
    send_logging_set_level,
    LogLevel,
)
from chuk_mcp.protocol.messages.message_method import MessageMethod


class TestSendLoggingSetLevel:
    """Test the send_logging_set_level function."""

    @pytest.mark.asyncio
    async def test_send_logging_set_level_debug(self):
        """Test setting logging level to debug."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        expected_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=expected_response,
        ) as mock_send:
            response = await send_logging_set_level(mock_read, mock_write, "debug")

            assert response == expected_response
            mock_send.assert_called_once_with(
                read_stream=mock_read,
                write_stream=mock_write,
                method=MessageMethod.LOGGING_SET_LEVEL,
                params={"level": "debug"},
                timeout=60.0,
            )

    @pytest.mark.asyncio
    async def test_send_logging_set_level_info(self):
        """Test setting logging level to info."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        expected_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=expected_response,
        ) as mock_send:
            response = await send_logging_set_level(mock_read, mock_write, "info")

            assert response == expected_response
            assert mock_send.call_args[1]["params"]["level"] == "info"

    @pytest.mark.asyncio
    async def test_send_logging_set_level_warning(self):
        """Test setting logging level to warning."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        expected_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=expected_response,
        ):
            response = await send_logging_set_level(mock_read, mock_write, "warning")
            assert response == expected_response

    @pytest.mark.asyncio
    async def test_send_logging_set_level_error(self):
        """Test setting logging level to error."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        expected_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=expected_response,
        ):
            response = await send_logging_set_level(mock_read, mock_write, "error")
            assert response == expected_response

    @pytest.mark.asyncio
    async def test_send_logging_set_level_critical(self):
        """Test setting logging level to critical."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        expected_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=expected_response,
        ):
            response = await send_logging_set_level(mock_read, mock_write, "critical")
            assert response == expected_response

    @pytest.mark.asyncio
    async def test_send_logging_set_level_all_levels(self):
        """Test all valid log levels."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        levels: list[LogLevel] = [
            "debug",
            "info",
            "notice",
            "warning",
            "error",
            "critical",
            "alert",
            "emergency",
        ]

        for level in levels:
            with patch(
                "chuk_mcp.protocol.messages.logging.send_messages.send_message",
                return_value={"result": {}},
            ) as mock_send:
                await send_logging_set_level(mock_read, mock_write, level)
                assert mock_send.call_args[1]["params"]["level"] == level

    @pytest.mark.asyncio
    async def test_send_logging_set_level_custom_timeout(self):
        """Test setting logging level with custom timeout."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value={"result": {}},
        ) as mock_send:
            await send_logging_set_level(mock_read, mock_write, "debug", timeout=30.0)

            assert mock_send.call_args[1]["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_send_logging_set_level_error_response(self):
        """Test handling error response from server."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid level"},
        }

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            return_value=error_response,
        ):
            response = await send_logging_set_level(mock_read, mock_write, "debug")
            assert "error" in response

    @pytest.mark.asyncio
    async def test_send_logging_set_level_exception(self):
        """Test handling exception during send."""
        mock_read = AsyncMock(spec=MemoryObjectReceiveStream)
        mock_write = AsyncMock(spec=MemoryObjectSendStream)

        with patch(
            "chuk_mcp.protocol.messages.logging.send_messages.send_message",
            side_effect=Exception("Network error"),
        ):
            with pytest.raises(Exception, match="Network error"):
                await send_logging_set_level(mock_read, mock_write, "debug")


class TestModuleExports:
    """Test module exports."""

    def test_module_exports(self):
        """Test that __all__ contains expected exports."""
        from chuk_mcp.protocol.messages.logging.send_messages import __all__

        assert "send_logging_set_level" in __all__
        assert "LogLevel" in __all__

    def test_log_level_type(self):
        """Test LogLevel type is available."""
        from chuk_mcp.protocol.messages.logging.send_messages import LogLevel

        # LogLevel is a type alias, just verify it's importable
        assert LogLevel is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
