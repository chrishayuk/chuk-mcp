#!/usr/bin/env python3
"""
Unit tests for the new high-level MCP client.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

import anyio

# Import the new client APIs
from chuk_mcp.client.client import MCPClient
from chuk_mcp.client.connection import connect_to_server
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.transports.stdio.transport import StdioTransport
from chuk_mcp.transports.base import Transport


class MockTransport(Transport):
    """Mock transport for testing."""
    
    def __init__(self):
        super().__init__(None)
        self.streams = None
        self.protocol_version = None
        self.started = False
    
    async def get_streams(self):
        # For testing, allow getting streams even when not started
        # The real client will handle transport lifecycle
        return self.streams or (AsyncMock(), AsyncMock())
    
    async def __aenter__(self):
        self.started = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.started = False
        return False
    
    def set_protocol_version(self, version: str):
        self.protocol_version = version


class TestMCPClient:
    """Test the high-level MCP client."""
    
    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        return MockTransport()
    
    @pytest.fixture
    def mock_streams(self):
        """Create mock read/write streams."""
        read_stream = AsyncMock()
        write_stream = AsyncMock()
        return read_stream, write_stream
    
    def test_client_initialization(self, mock_transport):
        """Test client initialization."""
        client = MCPClient(mock_transport)
        
        assert client.transport == mock_transport
        assert client.initialized is False
        assert client.server_info is None
        assert client.capabilities is None
        assert client._streams is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_transport, mock_streams):
        """Test successful client initialization."""
        client = MCPClient(mock_transport)
        
        # Mock the transport streams
        mock_transport.streams = mock_streams
        
        # Mock the initialize response
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "test-server"
        mock_init_result.capabilities = {"tools": {}}
        mock_init_result.protocolVersion = "2025-06-18"
        
        with patch('chuk_mcp.client.client.send_initialize', return_value=mock_init_result) as mock_send:
            result = await client.initialize()
            
            assert client.initialized is True
            assert client.server_info == mock_init_result.serverInfo
            assert client.capabilities == mock_init_result.capabilities
            assert client._streams == mock_streams
            assert mock_transport.protocol_version == "2025-06-18"
            
            # Verify send_initialize was called
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, mock_transport):
        """Test initializing an already initialized client."""
        client = MCPClient(mock_transport)
        
        # Pre-set initialization state
        client.initialized = True
        client.server_info = Mock()
        client.server_info.name = "existing-server"
        client.capabilities = {"existing": True}
        
        result = await client.initialize()
        
        # Should return existing info without re-initializing
        assert result["server_info"] == client.server_info
        assert result["capabilities"] == client.capabilities
    
    @pytest.mark.asyncio
    async def test_list_tools(self, mock_transport, mock_streams):
        """Test listing tools."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_tools_response = {
            "tools": [
                {"name": "hello", "description": "Say hello"},
                {"name": "echo", "description": "Echo message"}
            ]
        }
        
        with patch('chuk_mcp.client.client.send_tools_list', return_value=mock_tools_response) as mock_send:
            tools = await client.list_tools()
            
            assert len(tools) == 2
            assert tools[0]["name"] == "hello"
            assert tools[1]["name"] == "echo"
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool(self, mock_transport, mock_streams):
        """Test calling a tool."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_tool_response = {
            "content": [{"type": "text", "text": "Hello, World!"}]
        }
        
        with patch('chuk_mcp.client.client.send_tools_call', return_value=mock_tool_response) as mock_send:
            result = await client.call_tool("hello", {"name": "World"})
            
            assert result == mock_tool_response
            mock_send.assert_called_once_with(
                mock_streams[0], mock_streams[1], "hello", {"name": "World"}
            )
    
    @pytest.mark.asyncio
    async def test_call_tool_no_arguments(self, mock_transport, mock_streams):
        """Test calling a tool without arguments."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_tool_response = {"content": [{"type": "text", "text": "Result"}]}
        
        with patch('chuk_mcp.client.client.send_tools_call', return_value=mock_tool_response) as mock_send:
            result = await client.call_tool("ping")
            
            assert result == mock_tool_response
            mock_send.assert_called_once_with(
                mock_streams[0], mock_streams[1], "ping", {}
            )
    
    @pytest.mark.asyncio
    async def test_list_resources(self, mock_transport, mock_streams):
        """Test listing resources."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_resources_response = {
            "resources": [
                {"uri": "file://test.txt", "name": "Test File"},
                {"uri": "db://users", "name": "Users Table"}
            ]
        }
        
        with patch('chuk_mcp.client.client.send_resources_list', return_value=mock_resources_response) as mock_send:
            resources = await client.list_resources()
            
            assert len(resources) == 2
            assert resources[0]["uri"] == "file://test.txt"
            assert resources[1]["uri"] == "db://users"
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_resource(self, mock_transport, mock_streams):
        """Test reading a resource."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_resource_response = {
            "contents": [{"uri": "file://test.txt", "mimeType": "text/plain", "text": "Hello"}]
        }
        
        with patch('chuk_mcp.client.client.send_resources_read', return_value=mock_resource_response) as mock_send:
            result = await client.read_resource("file://test.txt")
            
            assert result == mock_resource_response
            mock_send.assert_called_once_with(
                mock_streams[0], mock_streams[1], "file://test.txt"
            )
    
    @pytest.mark.asyncio
    async def test_list_prompts(self, mock_transport, mock_streams):
        """Test listing prompts."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_prompts_response = {
            "prompts": [
                {"name": "summarize", "description": "Summarize text"},
                {"name": "translate", "description": "Translate text"}
            ]
        }
        
        with patch('chuk_mcp.client.client.send_prompts_list', return_value=mock_prompts_response) as mock_send:
            prompts = await client.list_prompts()
            
            assert len(prompts) == 2
            assert prompts[0]["name"] == "summarize"
            assert prompts[1]["name"] == "translate"
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_prompt(self, mock_transport, mock_streams):
        """Test getting a prompt."""
        client = MCPClient(mock_transport)
        await self._setup_initialized_client(client, mock_transport, mock_streams)
        
        mock_prompt_response = {
            "description": "Summary prompt",
            "messages": [{"role": "user", "content": {"type": "text", "text": "Summarize this"}}]
        }
        
        with patch('chuk_mcp.client.client.send_prompts_get', return_value=mock_prompt_response) as mock_send:
            result = await client.get_prompt("summarize", {"text": "Long text here"})
            
            assert result == mock_prompt_response
            mock_send.assert_called_once_with(
                mock_streams[0], mock_streams[1], "summarize", {"text": "Long text here"}
            )
    
    @pytest.mark.asyncio
    async def test_auto_initialize_on_operations(self, mock_transport, mock_streams):
        """Test that operations auto-initialize if not already initialized."""
        client = MCPClient(mock_transport)
        
        # Mock transport streams
        mock_transport.streams = mock_streams
        
        # Mock initialization
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "test-server"
        mock_init_result.capabilities = {"tools": {}}
        mock_init_result.protocolVersion = "2025-06-18"
        
        # Mock tools response
        mock_tools_response = {"tools": []}
        
        with patch('chuk_mcp.client.client.send_initialize', return_value=mock_init_result):
            with patch('chuk_mcp.client.client.send_tools_list', return_value=mock_tools_response):
                # Client starts uninitialized
                assert client.initialized is False
                
                # Calling list_tools should auto-initialize
                await client.list_tools()
                
                # Should now be initialized
                assert client.initialized is True
    
    async def _setup_initialized_client(self, client, mock_transport, mock_streams):
        """Helper to set up an initialized client."""
        mock_transport.streams = mock_streams
        client.initialized = True
        client._streams = mock_streams
        client.server_info = Mock()
        client.server_info.name = "test-server"
        client.capabilities = {"tools": {}}


class TestConnectToServer:
    """Test the connect_to_server context manager."""
    
    @pytest.mark.asyncio
    async def test_connect_with_transport_instance(self):
        """Test connecting with a transport instance."""
        mock_transport = MockTransport()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_transport.streams = mock_streams
        
        # Mock initialization
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "test-server"
        mock_init_result.capabilities = {"tools": {}}
        mock_init_result.protocolVersion = "2025-06-18"
        
        # Patch the send_initialize in the client module, not connection
        with patch('chuk_mcp.client.client.send_initialize', return_value=mock_init_result):
            async with connect_to_server(mock_transport) as client:
                assert isinstance(client, MCPClient)
                assert client.transport == mock_transport
                assert client.initialized is True
    
    @pytest.mark.asyncio
    async def test_connect_with_stdio_parameters(self):
        """Test connecting with StdioParameters."""
        params = StdioParameters(command="python", args=["server.py"])
        
        # Mock the StdioTransport creation and behavior
        with patch('chuk_mcp.client.connection.StdioTransport') as MockStdioTransport:
            mock_transport = MockTransport()
            mock_streams = (AsyncMock(), AsyncMock())
            mock_transport.streams = mock_streams
            MockStdioTransport.return_value = mock_transport
            
            # Mock initialization
            mock_init_result = Mock()
            mock_init_result.serverInfo = Mock()
            mock_init_result.serverInfo.name = "test-server"
            mock_init_result.capabilities = {"tools": {}}
            mock_init_result.protocolVersion = "2025-06-18"
            
            # Patch the send_initialize in the client module
            with patch('chuk_mcp.client.client.send_initialize', return_value=mock_init_result):
                async with connect_to_server(params) as client:
                    assert isinstance(client, MCPClient)
                    assert client.initialized is True
                    
                    # Verify StdioTransport was created with correct params
                    MockStdioTransport.assert_called_once_with(params)
    
    @pytest.mark.asyncio
    async def test_connect_error_handling(self):
        """Test error handling in connect_to_server."""
        mock_transport = MockTransport()
        
        # Make initialization fail
        with patch('chuk_mcp.client.client.send_initialize', side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                async with connect_to_server(mock_transport) as client:
                    pass


class TestClientIntegration:
    """Integration tests combining client and transport."""
    
    @pytest.mark.asyncio
    async def test_client_with_mock_transport(self):
        """Test client with a simple mock transport (no subprocess mocking)."""
        # Use our simple MockTransport instead of complex subprocess mocking
        mock_transport = MockTransport()
        mock_streams = (AsyncMock(), AsyncMock())
        mock_transport.streams = mock_streams
        
        client = MCPClient(mock_transport)
        
        # Mock protocol responses
        mock_init_result = Mock()
        mock_init_result.serverInfo = Mock()
        mock_init_result.serverInfo.name = "mock-test-server"
        mock_init_result.capabilities = {"tools": {}}
        mock_init_result.protocolVersion = "2025-06-18"
        
        with patch('chuk_mcp.client.client.send_initialize', return_value=mock_init_result):
            await client.initialize()
            
            assert client.initialized is True
            assert client.server_info.name == "mock-test-server"
            assert mock_transport.protocol_version == "2025-06-18"
            
            # Test a tool operation
            mock_tools_response = {"tools": [{"name": "test", "description": "A test tool"}]}
            with patch('chuk_mcp.client.client.send_tools_list', return_value=mock_tools_response):
                tools = await client.list_tools()
                assert len(tools) == 1
                assert tools[0]["name"] == "test"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])