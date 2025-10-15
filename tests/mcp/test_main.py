#!/usr/bin/env python3
"""
Comprehensive tests for __main__.py CLI module.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, mock_open

from chuk_mcp.__main__ import (
    setup_logging,
    find_default_config,
    list_servers,
    test_server as server_test_func,
    main,
)


class TestSetupLogging:
    """Test logging setup."""

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose mode."""
        with patch("logging.basicConfig") as mock_basic:
            setup_logging(verbose=True)
            mock_basic.assert_called_once()
            args = mock_basic.call_args
            assert args[1]["level"] == 10  # logging.DEBUG

    def test_setup_logging_non_verbose(self):
        """Test logging setup without verbose mode."""
        with patch("logging.basicConfig") as mock_basic:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                setup_logging(verbose=False)

                mock_basic.assert_called_once()
                args = mock_basic.call_args
                assert args[1]["level"] == 20  # logging.INFO

                # Check that anyio logging was reduced
                mock_get_logger.assert_called_with("anyio")
                mock_logger.setLevel.assert_called_with(30)  # logging.WARNING


class TestFindDefaultConfig:
    """Test finding default configuration files."""

    def test_find_default_config_found(self):
        """Test finding a config file that exists."""
        with patch("pathlib.Path.exists") as mock_exists:
            # First path exists
            mock_exists.side_effect = [True, False, False, False, False]
            result = find_default_config()
            assert result == "server_config.json"

    def test_find_default_config_second_location(self):
        """Test finding config in second location."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Second path exists
            mock_exists.side_effect = [False, True, False, False, False]
            result = find_default_config()
            assert result == "mcp_config.json"

    def test_find_default_config_not_found(self):
        """Test when no config file is found."""
        with patch("pathlib.Path.exists", return_value=False):
            result = find_default_config()
            assert result is None


class TestListServers:
    """Test listing servers from configuration."""

    def test_list_servers_success(self, capsys):
        """Test successfully listing servers."""
        config_data = {
            "mcpServers": {
                "sqlite": {"command": "sqlite-mcp", "args": ["--db", "test.db"]},
                "postgres": {"command": "pg-mcp", "args": []},
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            list_servers("test_config.json")

        captured = capsys.readouterr()
        assert "sqlite" in captured.out
        assert "sqlite-mcp" in captured.out
        assert "postgres" in captured.out
        assert "pg-mcp" in captured.out

    def test_list_servers_empty(self, capsys):
        """Test listing when no servers configured."""
        config_data = {"mcpServers": {}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            list_servers("test_config.json")

        captured = capsys.readouterr()
        assert "No servers found" in captured.out

    def test_list_servers_file_not_found(self, capsys):
        """Test listing when config file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit):
                list_servers("nonexistent.json")

        captured = capsys.readouterr()
        assert "Configuration file not found" in captured.out

    def test_list_servers_invalid_json(self, capsys):
        """Test listing with invalid JSON."""
        m = mock_open(read_data="invalid json{")
        with patch("builtins.open", m):
            with pytest.raises(SystemExit):
                list_servers("test_config.json")

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out

    def test_list_servers_general_error(self, capsys):
        """Test listing with general error."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(SystemExit):
                list_servers("test_config.json")

        captured = capsys.readouterr()
        assert "Error reading configuration" in captured.out


class TestTestServer:
    """Test the test_server async function."""

    @pytest.mark.asyncio
    async def test_test_server_success(self, capsys):
        """Test successful server test."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        # Mock server parameters
        mock_params = StdioParameters(command="test-server", args=["--test"])

        # Mock initialization result
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = "Test instructions"
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        # Mock streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                # Setup context manager
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        result = await server_test_func(
                            "config.json", "test-server", verbose=False
                        )

        assert result is True
        captured = capsys.readouterr()
        assert "Connected to TestServer" in captured.out
        assert "Ping successful" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_verbose(self, capsys):
        """Test server test with verbose output."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = "Detailed instructions"
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        result = await server_test_func(
                            "config.json", "test-server", verbose=True
                        )

        assert result is True
        captured = capsys.readouterr()
        assert "Instructions: Detailed instructions" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_init_failed(self, capsys):
        """Test when server initialization fails."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])
        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch("chuk_mcp.__main__.send_initialize", return_value=None):
                    result = await server_test_func("config.json", "test-server")

        assert result is False
        captured = capsys.readouterr()
        assert "initialization failed" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_ping_failed(self, capsys):
        """Test when ping fails."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=False):
                        result = await server_test_func("config.json", "test-server")

        assert result is True  # Still succeeds, just shows ping failed
        captured = capsys.readouterr()
        assert "Ping failed" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_tools(self, capsys):
        """Test server with tools capability."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = {"enabled": True}
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        mock_tools_response = {
            "tools": [
                {"name": "echo", "description": "Echo a message"},
                {"name": "calc", "description": "Calculate"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_tools_list",
                            return_value=mock_tools_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Tools available: 2" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_tools_verbose(self, capsys):
        """Test server with tools and verbose output."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = {"enabled": True}
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        mock_tools_response = {
            "tools": [
                {"name": "echo", "description": "Echo a message"},
                {"name": "calc", "description": "Calculate"},
                {"name": "search", "description": "Search"},
                {"name": "translate", "description": "Translate"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_tools_list",
                            return_value=mock_tools_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server", verbose=True
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "echo: Echo a message" in captured.out
        assert "and 1 more" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_tools_error(self, capsys):
        """Test when tools listing fails."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = {"enabled": True}
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = None

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_tools_list",
                            side_effect=Exception("Tools error"),
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Tools feature available but listing failed" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_resources(self, capsys):
        """Test server with resources capability."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = {"subscribe": True}
        mock_init_result.capabilities.prompts = None

        mock_resources_response = {
            "resources": [
                {"name": "file1", "description": "File 1"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_resources_list",
                            return_value=mock_resources_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Resources available: 1" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_resources_verbose(self, capsys):
        """Test server with resources and verbose output."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = {"subscribe": True}
        mock_init_result.capabilities.prompts = None

        mock_resources_response = {
            "resources": [
                {"name": "file1", "description": "File 1"},
                {"name": "file2", "description": "File 2"},
                {"name": "file3", "description": "File 3"},
                {"name": "file4", "description": "File 4"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_resources_list",
                            return_value=mock_resources_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server", verbose=True
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "file1: File 1" in captured.out
        assert "and 1 more" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_resources_error(self, capsys):
        """Test when resources listing fails."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = {"subscribe": True}
        mock_init_result.capabilities.prompts = None

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_resources_list",
                            side_effect=Exception("Resources error"),
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Resources feature available but listing failed" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_prompts(self, capsys):
        """Test server with prompts capability."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = {"listChanged": True}

        mock_prompts_response = {
            "prompts": [
                {"name": "summarize", "description": "Summarize text"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_prompts_list",
                            return_value=mock_prompts_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Prompts available: 1" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_with_prompts_verbose(self, capsys):
        """Test server with prompts and verbose output."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = {"listChanged": True}

        mock_prompts_response = {
            "prompts": [
                {"name": "summarize", "description": "Summarize text"},
                {"name": "analyze", "description": "Analyze"},
                {"name": "translate", "description": "Translate"},
                {"name": "review", "description": "Review"},
            ]
        }

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_prompts_list",
                            return_value=mock_prompts_response,
                        ):
                            result = await server_test_func(
                                "config.json", "test-server", verbose=True
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "summarize: Summarize text" in captured.out
        assert "and 1 more" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_prompts_error(self, capsys):
        """Test when prompts listing fails."""
        from chuk_mcp.transports.stdio.parameters import StdioParameters

        mock_params = StdioParameters(command="test-server", args=[])

        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "TestServer"
        mock_init_result.serverInfo.version = "1.0.0"
        mock_init_result.protocolVersion = "2025-06-18"
        mock_init_result.instructions = None
        mock_init_result.capabilities = Mock()
        mock_init_result.capabilities.tools = None
        mock_init_result.capabilities.resources = None
        mock_init_result.capabilities.prompts = {"listChanged": True}

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("chuk_mcp.__main__.load_config", return_value=mock_params):
            with patch("chuk_mcp.__main__.stdio_client") as mock_client:
                mock_cm = AsyncMock()
                mock_cm.__aenter__.return_value = (mock_read, mock_write)
                mock_cm.__aexit__.return_value = None
                mock_client.return_value = mock_cm

                with patch(
                    "chuk_mcp.__main__.send_initialize", return_value=mock_init_result
                ):
                    with patch("chuk_mcp.__main__.send_ping", return_value=True):
                        with patch(
                            "chuk_mcp.__main__.send_prompts_list",
                            side_effect=Exception("Prompts error"),
                        ):
                            result = await server_test_func(
                                "config.json", "test-server"
                            )

        assert result is True
        captured = capsys.readouterr()
        assert "Prompts feature available but listing failed" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_file_not_found(self, capsys):
        """Test when config file is not found."""
        with patch(
            "chuk_mcp.__main__.load_config", side_effect=FileNotFoundError("Not found")
        ):
            result = await server_test_func("nonexistent.json", "test-server")

        assert result is False
        captured = capsys.readouterr()
        assert "Configuration file not found" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_value_error(self, capsys):
        """Test when there's a configuration error."""
        with patch(
            "chuk_mcp.__main__.load_config", side_effect=ValueError("Bad config")
        ):
            result = await server_test_func("config.json", "test-server")

        assert result is False
        captured = capsys.readouterr()
        assert "Configuration error" in captured.out

    @pytest.mark.asyncio
    async def test_test_server_unexpected_error(self, capsys):
        """Test unexpected error handling."""
        with patch(
            "chuk_mcp.__main__.load_config", side_effect=RuntimeError("Unexpected")
        ):
            result = await server_test_func("config.json", "test-server")

        assert result is False
        captured = capsys.readouterr()
        assert "Connection failed" in captured.out


class TestMain:
    """Test the main CLI function."""

    def test_main_list_servers(self):
        """Test --list-servers flag."""
        config_data = {"mcpServers": {"sqlite": {"command": "sqlite-mcp", "args": []}}}

        test_args = ["prog", "--list-servers", "--config", "test.json"]

        m = mock_open(read_data=json.dumps(config_data))
        with patch("sys.argv", test_args):
            with patch("builtins.open", m):
                main()

    def test_main_no_config_found(self, capsys):
        """Test when no config file is found."""
        test_args = ["prog"]

        with patch("sys.argv", test_args):
            with patch("chuk_mcp.__main__.find_default_config", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No configuration file found" in captured.out

    def test_main_test_server_success(self):
        """Test successful server test."""
        test_args = ["prog", "--config", "test.json", "--server", "sqlite"]

        with patch("sys.argv", test_args):
            with patch(
                "chuk_mcp.__main__.find_default_config", return_value="test.json"
            ):
                with patch("anyio.run", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_main_test_server_failure(self):
        """Test failed server test."""
        test_args = ["prog", "--config", "test.json", "--server", "sqlite"]

        with patch("sys.argv", test_args):
            with patch(
                "chuk_mcp.__main__.find_default_config", return_value="test.json"
            ):
                with patch("anyio.run", return_value=False):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1

    def test_main_keyboard_interrupt(self, capsys):
        """Test keyboard interrupt handling."""
        test_args = ["prog", "--config", "test.json"]

        with patch("sys.argv", test_args):
            with patch(
                "chuk_mcp.__main__.find_default_config", return_value="test.json"
            ):
                with patch("anyio.run", side_effect=KeyboardInterrupt):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Interrupted by user" in captured.out

    def test_main_with_verbose(self):
        """Test main with verbose flag."""
        test_args = ["prog", "--verbose", "--config", "test.json"]

        with patch("sys.argv", test_args):
            with patch("chuk_mcp.__main__.setup_logging") as mock_setup:
                with patch(
                    "chuk_mcp.__main__.find_default_config", return_value="test.json"
                ):
                    with patch("anyio.run", return_value=True):
                        with pytest.raises(SystemExit):
                            main()

        mock_setup.assert_called_once_with(True)

    def test_main_default_server(self):
        """Test using default server name."""
        test_args = ["prog", "--config", "test.json"]

        with patch("sys.argv", test_args):
            with patch("anyio.run") as mock_run:
                with pytest.raises(SystemExit):
                    main()

        # Check that test_server was called with default "sqlite" server
        call_args = mock_run.call_args[0]
        assert call_args[2] == "sqlite"  # server name argument


class TestRunEntryPoint:
    """Test the run() entry point function."""

    def test_run_function_exists(self):
        """Test that run function is defined for console script."""
        from chuk_mcp.__main__ import main, run

        # The run function should be defined for the console script entry point
        # It's typically just an alias to main()
        assert callable(main)
        assert callable(run)

    def test_run_calls_main(self):
        """Test that run() calls main()."""
        from chuk_mcp.__main__ import run

        test_args = ["prog", "--config", "test.json"]

        with patch("sys.argv", test_args):
            with patch(
                "chuk_mcp.__main__.find_default_config", return_value="test.json"
            ):
                with patch("anyio.run", return_value=True):
                    with pytest.raises(SystemExit):
                        run()

    def test_main_block_execution(self):
        """Test the if __name__ == '__main__' block."""
        test_args = ["prog", "--config", "test.json"]

        # Simulate running the module directly
        with patch("sys.argv", test_args):
            with patch(
                "chuk_mcp.__main__.find_default_config", return_value="test.json"
            ):
                with patch("anyio.run", return_value=True):
                    with pytest.raises(SystemExit):
                        # Import and execute the module's __main__ block
                        import runpy

                        runpy.run_module("chuk_mcp.__main__", run_name="__main__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
