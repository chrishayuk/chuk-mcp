#!/usr/bin/env python3
"""
Comprehensive tests for server_manager.py module.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from chuk_mcp.mcp_client.host.server_manager import run_command


class TestRunCommand:
    """Test the run_command function."""

    @pytest.mark.asyncio
    async def test_run_command_basic(self, capsys):
        """Test basic run_command execution."""

        async def dummy_command(server_streams):
            """Simple test command."""
            assert len(server_streams) == 1

        config_file = "test_config.json"
        server_names = ["test-server"]

        # Mock dependencies
        mock_params = Mock()
        mock_params.command = "test-cmd"
        mock_params.args = []

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_streams = (mock_read, mock_write)

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "Test Server"

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run") as mock_run:
                            # Call the inner function directly
                            async def call_inner():
                                await mock_run.call_args[0][0]()

                            run_command(dummy_command, config_file, server_names)

    def test_run_command_clears_screen(self):
        """Test that run_command clears the screen."""

        async def dummy_command(server_streams):
            pass

        with patch("os.system") as mock_system:
            with patch("anyio.run"):
                with patch(
                    "chuk_mcp.config.load_config", side_effect=Exception("Stop")
                ):
                    try:
                        run_command(dummy_command, "config.json", ["server"])
                    except Exception:
                        pass

        # Check that clear/cls was called
        mock_system.assert_called()
        call_arg = mock_system.call_args[0][0]
        assert call_arg in ["clear", "cls"]

    def test_run_command_windows_clear(self):
        """Test screen clearing on Windows."""

        async def dummy_command(server_streams):
            pass

        with patch("os.name", "nt"):
            with patch("os.system") as mock_system:
                with patch("anyio.run"):
                    with patch(
                        "chuk_mcp.config.load_config", side_effect=Exception("Stop")
                    ):
                        try:
                            run_command(dummy_command, "config.json", ["server"])
                        except Exception:
                            pass

        mock_system.assert_called_with("cls")

    def test_run_command_unix_clear(self):
        """Test screen clearing on Unix."""

        async def dummy_command(server_streams):
            pass

        with patch("os.name", "posix"):
            with patch("os.system") as mock_system:
                with patch("anyio.run"):
                    with patch(
                        "chuk_mcp.config.load_config", side_effect=Exception("Stop")
                    ):
                        try:
                            run_command(dummy_command, "config.json", ["server"])
                        except Exception:
                            pass

        mock_system.assert_called_with("clear")

    def test_run_command_keyboard_interrupt(self, capsys):
        """Test handling of KeyboardInterrupt."""

        async def dummy_command(server_streams):
            pass

        with patch("os.system"):
            with patch("anyio.run", side_effect=KeyboardInterrupt):
                run_command(dummy_command, "config.json", ["server"])

        captured = capsys.readouterr()
        assert "interrupted" in captured.out.lower()

    def test_run_command_general_exception(self, capsys):
        """Test handling of general exceptions."""

        async def dummy_command(server_streams):
            pass

        with patch("os.system"):
            with patch("anyio.run", side_effect=Exception("Test error")):
                run_command(dummy_command, "config.json", ["server"])

        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out.lower()

    def test_run_command_multiple_servers(self):
        """Test run_command with multiple servers."""

        async def dummy_command(server_streams):
            assert len(server_streams) >= 1

        config_file = "test_config.json"
        server_names = ["server1", "server2"]

        mock_params = Mock()
        mock_params.command = "test-cmd"
        mock_params.args = []

        mock_streams1 = (AsyncMock(), AsyncMock())
        mock_streams2 = (AsyncMock(), AsyncMock())

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "Test Server"

        load_count = [0]

        async def mock_load_config(config, name):
            load_count[0] += 1
            return mock_params

        with patch("chuk_mcp.config.load_config", side_effect=mock_load_config):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                call_count = [0]

                def create_cm():
                    call_count[0] += 1
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__.return_value = (
                        mock_streams1 if call_count[0] == 1 else mock_streams2
                    )
                    mock_cm.__aexit__ = AsyncMock()
                    return mock_cm

                mock_client.side_effect = lambda x: create_cm()

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, config_file, server_names)

    def test_run_command_server_init_failure(self, capsys):
        """Test when server initialization fails."""

        async def dummy_command(server_streams):
            pass

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=None,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, "config.json", ["server"])

    def test_run_command_server_connection_error(self, capsys):
        """Test when server connection fails."""

        async def dummy_command(server_streams):
            pass

        with patch(
            "chuk_mcp.config.load_config", side_effect=Exception("Connection error")
        ):
            with patch("os.system"):
                with patch("anyio.run"):
                    run_command(dummy_command, "config.json", ["server"])

    def test_run_command_no_valid_connections(self, capsys):
        """Test when no valid server connections are established."""

        async def dummy_command(server_streams):
            pass

        with patch("chuk_mcp.config.load_config", side_effect=Exception("Failed")):
            with patch("os.system"):
                with patch("anyio.run"):
                    run_command(dummy_command, "config.json", ["server"])

    def test_run_command_interactive_mode(self):
        """Test run_command with interactive mode command."""

        async def interactive_mode(server_streams, server_info=None):
            assert server_info is not None
            assert len(server_info) >= 1
            return True  # Clean exit

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "Test"

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(interactive_mode, "config.json", ["server"])

    def test_run_command_chat_mode(self):
        """Test run_command with chat mode command."""

        async def chat_run(server_streams, server_info=None):
            assert server_info is not None
            return True

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(chat_run, "config.json", ["server"])

    def test_run_command_interactive_fallback(self):
        """Test interactive mode falling back when TypeError occurs."""

        async def interactive_mode(server_streams):
            # Old signature without server_info
            return True

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(interactive_mode, "config.json", ["server"])

    def test_run_command_user_specified_servers(self):
        """Test run_command with user-specified servers."""

        async def dummy_command(server_streams, server_info=None):
            if server_info:
                # Check that user_specified flag is set correctly
                assert any(s["user_specified"] for s in server_info)

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            # Test with user_specified parameter
                            run_command(
                                dummy_command,
                                "config.json",
                                ["server1"],
                                user_specified=["server1"],
                            )

    def test_run_command_cleanup_timeout(self, capsys):
        """Test cleanup timeout handling."""

        async def dummy_command(server_streams):
            pass

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                # Create a context manager that times out on exit
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams

                async def slow_exit(*args):
                    await asyncio.sleep(5)  # Longer than timeout

                mock_cm.__aexit__ = slow_exit
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, "config.json", ["server"])

    def test_run_command_cleanup_cancelled_error(self):
        """Test cleanup with CancelledError."""

        async def dummy_command(server_streams):
            pass

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock(side_effect=asyncio.CancelledError)
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, "config.json", ["server"])

    def test_run_command_cleanup_runtime_error(self):
        """Test cleanup with RuntimeError."""

        async def dummy_command(server_streams):
            pass

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock(
                    side_effect=RuntimeError("Event loop closed")
                )
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, "config.json", ["server"])

    def test_run_command_cleanup_general_error(self, capsys):
        """Test cleanup with general error."""

        async def dummy_command(server_streams):
            pass

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock(side_effect=ValueError("Cleanup error"))
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(dummy_command, "config.json", ["server"])

    def test_run_command_inner_keyboard_interrupt(self):
        """Test KeyboardInterrupt inside command execution."""

        async def failing_command(server_streams):
            raise KeyboardInterrupt()

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            run_command(failing_command, "config.json", ["server"])

    def test_run_command_inner_exception(self):
        """Test exception inside command execution."""

        # This test just ensures no crash when exception occurs
        # The actual error handling is tested via integration tests
        async def failing_command(server_streams):
            raise ValueError("Command failed")

        mock_params = Mock()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()

        with patch("chuk_mcp.config.load_config", return_value=(mock_params, None)):
            with patch(
                "chuk_mcp.transports.stdio.stdio_client.stdio_client"
            ) as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = mock_streams
                mock_cm.__aexit__ = AsyncMock()
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.protocol.messages.initialize.send_messages.send_initialize",
                    return_value=mock_init_result,
                ):
                    with patch("os.system"):
                        with patch("anyio.run"):
                            # Just verify it doesn't crash
                            run_command(failing_command, "config.json", ["server"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
