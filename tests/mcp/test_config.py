#!/usr/bin/env python3
"""
Comprehensive tests for config.py module.
"""

import pytest
import json
import logging
from unittest.mock import mock_open, patch

from chuk_mcp.config import load_config
from chuk_mcp.transports.stdio.parameters import StdioParameters


class TestLoadConfig:
    """Test the load_config function."""

    @pytest.mark.asyncio
    async def test_load_config_success(self):
        """Test successfully loading a valid configuration."""
        config_data = {
            "mcpServers": {
                "sqlite": {
                    "command": "uvx",
                    "args": ["mcp-server-sqlite", "--db", "test.db"],
                    "env": {"DEBUG": "1"},
                }
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "sqlite")

        assert isinstance(result, StdioParameters)
        assert result.command == "uvx"
        assert result.args == ["mcp-server-sqlite", "--db", "test.db"]
        assert result.env == {"DEBUG": "1"}

    @pytest.mark.asyncio
    async def test_load_config_no_env(self):
        """Test loading config without env variable."""
        config_data = {
            "mcpServers": {
                "postgres": {"command": "pg-mcp", "args": ["--host", "localhost"]}
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "postgres")

        assert isinstance(result, StdioParameters)
        assert result.command == "pg-mcp"
        assert result.args == ["--host", "localhost"]
        assert result.env is None

    @pytest.mark.asyncio
    async def test_load_config_no_args(self):
        """Test loading config without args."""
        config_data = {"mcpServers": {"simple": {"command": "simple-server"}}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "simple")

        assert isinstance(result, StdioParameters)
        assert result.command == "simple-server"
        assert result.args == []
        assert result.env is None

    @pytest.mark.asyncio
    async def test_load_config_server_not_found(self):
        """Test loading config when server name doesn't exist."""
        config_data = {"mcpServers": {"sqlite": {"command": "sqlite-mcp", "args": []}}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            with pytest.raises(ValueError, match="Server 'nonexistent' not found"):
                await load_config("config.json", "nonexistent")

    @pytest.mark.asyncio
    async def test_load_config_empty_servers(self):
        """Test loading config when mcpServers is empty."""
        config_data = {"mcpServers": {}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            with pytest.raises(ValueError, match="Server 'sqlite' not found"):
                await load_config("config.json", "sqlite")

    @pytest.mark.asyncio
    async def test_load_config_missing_mcpservers_key(self):
        """Test loading config when mcpServers key is missing."""
        config_data = {"otherKey": {}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            with pytest.raises(ValueError, match="Server 'sqlite' not found"):
                await load_config("config.json", "sqlite")

    @pytest.mark.asyncio
    async def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError, match="Configuration file not found"):
                await load_config("nonexistent.json", "sqlite")

    @pytest.mark.asyncio
    async def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        m = mock_open(read_data="invalid json {")
        with patch("builtins.open", m):
            with pytest.raises(json.JSONDecodeError):
                await load_config("config.json", "sqlite")

    @pytest.mark.asyncio
    async def test_load_config_missing_command(self):
        """Test loading config with missing command field."""
        config_data = {"mcpServers": {"broken": {"args": ["--test"]}}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            with pytest.raises(KeyError):
                await load_config("config.json", "broken")

    @pytest.mark.asyncio
    async def test_load_config_debug_logging(self, caplog):
        """Test that debug logging works correctly."""
        config_data = {
            "mcpServers": {
                "test": {
                    "command": "test-cmd",
                    "args": ["arg1"],
                    "env": {"VAR": "value"},
                }
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with caplog.at_level(logging.DEBUG):
            with patch("builtins.open", m):
                result = await load_config("config.json", "test")

        # Check that debug messages were logged
        assert any("Loading config from" in record.message for record in caplog.records)
        assert any("Loaded config" in record.message for record in caplog.records)
        assert result.command == "test-cmd"

    @pytest.mark.asyncio
    async def test_load_config_error_logging(self, caplog):
        """Test that error logging works when server not found."""
        config_data = {"mcpServers": {}}

        m = mock_open(read_data=json.dumps(config_data))
        with caplog.at_level(logging.ERROR):
            with patch("builtins.open", m):
                with pytest.raises(ValueError):
                    await load_config("config.json", "missing")

        # Check that error was logged
        assert any(
            "Server 'missing' not found" in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_load_config_file_not_found_logging(self, caplog):
        """Test logging when file is not found."""
        with caplog.at_level(logging.ERROR):
            with patch("builtins.open", side_effect=FileNotFoundError):
                with pytest.raises(FileNotFoundError):
                    await load_config("missing.json", "test")

        # Check that error was logged
        assert any(
            "Configuration file not found" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_load_config_json_decode_error_logging(self, caplog):
        """Test logging when JSON is invalid."""
        m = mock_open(read_data="bad {json")
        with caplog.at_level(logging.ERROR):
            with patch("builtins.open", m):
                with pytest.raises(json.JSONDecodeError):
                    await load_config("bad.json", "test")

        # Check that error was logged
        assert any("Invalid JSON" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_load_config_complex_env(self):
        """Test loading config with complex environment variables."""
        config_data = {
            "mcpServers": {
                "complex": {
                    "command": "node",
                    "args": ["server.js"],
                    "env": {
                        "NODE_ENV": "production",
                        "PORT": "3000",
                        "DATABASE_URL": "postgresql://localhost/db",
                        "FEATURE_FLAG": "true",
                    },
                }
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "complex")

        assert result.env["NODE_ENV"] == "production"
        assert result.env["PORT"] == "3000"
        assert result.env["DATABASE_URL"] == "postgresql://localhost/db"
        assert result.env["FEATURE_FLAG"] == "true"

    @pytest.mark.asyncio
    async def test_load_config_empty_args_list(self):
        """Test loading config with explicitly empty args list."""
        config_data = {"mcpServers": {"simple": {"command": "simple-cmd", "args": []}}}

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "simple")

        assert result.args == []

    @pytest.mark.asyncio
    async def test_load_config_multiple_servers(self):
        """Test loading config with multiple servers, selecting one."""
        config_data = {
            "mcpServers": {
                "sqlite": {"command": "sqlite-mcp", "args": ["--db", "sqlite.db"]},
                "postgres": {"command": "pg-mcp", "args": ["--host", "localhost"]},
                "redis": {"command": "redis-mcp", "args": []},
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "postgres")

        assert result.command == "pg-mcp"
        assert result.args == ["--host", "localhost"]

    @pytest.mark.asyncio
    async def test_load_config_special_characters_in_args(self):
        """Test loading config with special characters in arguments."""
        config_data = {
            "mcpServers": {
                "special": {
                    "command": "server",
                    "args": [
                        "--path",
                        "/usr/local/bin",
                        "--name",
                        "my-server",
                        "--flag=value",
                    ],
                }
            }
        }

        m = mock_open(read_data=json.dumps(config_data))
        with patch("builtins.open", m):
            result = await load_config("config.json", "special")

        assert "--path" in result.args
        assert "/usr/local/bin" in result.args
        assert "--flag=value" in result.args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
