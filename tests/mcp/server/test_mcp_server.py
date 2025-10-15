#!/usr/bin/env python3
"""
Fixed unit tests for the MCP server implementation.
"""

import pytest

# Import the server components
from chuk_mcp.server.server import MCPServer
from chuk_mcp.protocol.types.capabilities import ServerCapabilities
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage


class TestMCPServer:
    """Test the high-level MCP server."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = MCPServer("test-server", "1.0.0")

        assert server.server_info.name == "test-server"
        assert server.server_info.version == "1.0.0"
        assert isinstance(server.capabilities, ServerCapabilities)
        assert server.protocol_handler is not None
        assert len(server._tools) == 0
        assert len(server._resources) == 0

    def test_server_with_custom_capabilities(self):
        """Test server initialization with custom capabilities."""
        capabilities = ServerCapabilities(
            tools={"listChanged": True}, resources={"listChanged": True}
        )

        server = MCPServer("custom-server", "2.0.0", capabilities)

        assert server.capabilities == capabilities
        assert server.server_info.name == "custom-server"
        assert server.server_info.version == "2.0.0"

    def test_tool_registration(self):
        """Test tool registration."""
        server = MCPServer("test-server")

        async def test_tool(message: str) -> str:
            return f"Hello, {message}!"

        schema = {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        }

        server.register_tool("greet", test_tool, schema, "Greeting tool")

        assert "greet" in server._tools
        assert server._tools["greet"]["handler"] == test_tool
        assert server._tools["greet"]["schema"] == schema
        assert server._tools["greet"]["description"] == "Greeting tool"

    def test_resource_registration(self):
        """Test resource registration."""
        server = MCPServer("test-server")

        async def test_resource() -> str:
            return "Resource content"

        server.register_resource(
            "test://resource",
            test_resource,
            "Test Resource",
            "A test resource",
            "text/plain",
        )

        assert "test://resource" in server._resources
        assert server._resources["test://resource"]["handler"] == test_resource
        assert server._resources["test://resource"]["name"] == "Test Resource"
        assert server._resources["test://resource"]["description"] == "A test resource"
        assert server._resources["test://resource"]["mime_type"] == "text/plain"

    def test_resource_registration_with_defaults(self):
        """Test resource registration with default values."""
        server = MCPServer("test-server")

        async def test_resource() -> str:
            return "Content"

        server.register_resource("file://test.txt", test_resource)

        resource = server._resources["file://test.txt"]
        assert resource["name"] == "test.txt"  # Extracted from URI
        assert resource["description"] == ""
        assert resource["mime_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_handle_tools_list(self):
        """Test tools/list handler."""
        server = MCPServer("test-server")

        # Register some tools
        async def tool1() -> str:
            return "result1"

        async def tool2() -> str:
            return "result2"

        server.register_tool("tool1", tool1, {"type": "object"}, "First tool")
        server.register_tool("tool2", tool2, {"type": "object"}, "Second tool")

        # Create mock message
        message = JSONRPCMessage(jsonrpc="2.0", id="test-123", method="tools/list")

        response, session_id = await server._handle_tools_list(message, None)

        assert response is not None
        assert session_id is None
        assert response.id == "test-123"

        # Parse the result
        result = response.result
        assert "tools" in result
        tools = result["tools"]

        assert len(tools) == 2
        tool_names = [tool["name"] for tool in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

        # Check tool structure
        tool1_info = next(tool for tool in tools if tool["name"] == "tool1")
        assert tool1_info["description"] == "First tool"
        assert tool1_info["inputSchema"] == {"type": "object"}

    @pytest.mark.asyncio
    async def test_handle_tools_call_success(self):
        """Test successful tool call."""
        server = MCPServer("test-server")

        async def greet_tool(name: str) -> str:
            return f"Hello, {name}!"

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        server.register_tool("greet", greet_tool, schema)

        # Create tool call message
        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="call-123",
            method="tools/call",
            params={"name": "greet", "arguments": {"name": "World"}},
        )

        response, session_id = await server._handle_tools_call(message, None)

        assert response is not None
        assert session_id is None
        assert response.id == "call-123"

        result = response.result
        assert "content" in result
        content = result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_handle_tools_call_unknown_tool(self):
        """Test tool call with unknown tool."""
        server = MCPServer("test-server")

        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="call-456",
            method="tools/call",
            params={"name": "unknown_tool", "arguments": {}},
        )

        response, session_id = await server._handle_tools_call(message, None)

        assert response is not None
        assert session_id is None
        assert response.id == "call-456"
        assert hasattr(response, "error")
        # Fix: Access error as dictionary
        assert response.error["code"] == -32602
        assert "Unknown tool: unknown_tool" in response.error["message"]

    @pytest.mark.asyncio
    async def test_handle_tools_call_execution_error(self):
        """Test tool call with execution error."""
        server = MCPServer("test-server")

        async def failing_tool() -> str:
            raise ValueError("Tool execution failed")

        server.register_tool("failing", failing_tool, {"type": "object"})

        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="call-789",
            method="tools/call",
            params={"name": "failing", "arguments": {}},
        )

        response, session_id = await server._handle_tools_call(message, None)

        assert response is not None
        assert hasattr(response, "error")
        # Fix: Access error as dictionary
        assert response.error["code"] == -32603
        assert "Tool execution error" in response.error["message"]

    @pytest.mark.asyncio
    async def test_handle_resources_list(self):
        """Test resources/list handler."""
        server = MCPServer("test-server")

        # Register some resources
        async def resource1() -> str:
            return "content1"

        async def resource2() -> str:
            return "content2"

        server.register_resource(
            "file://test1.txt", resource1, "Test 1", "First resource"
        )
        server.register_resource(
            "file://test2.txt",
            resource2,
            "Test 2",
            "Second resource",
            "application/json",
        )

        message = JSONRPCMessage(jsonrpc="2.0", id="res-123", method="resources/list")

        response, session_id = await server._handle_resources_list(message, None)

        assert response is not None
        assert session_id is None

        result = response.result
        assert "resources" in result
        resources = result["resources"]

        assert len(resources) == 2

        # Check resource structure
        uris = [res["uri"] for res in resources]
        assert "file://test1.txt" in uris
        assert "file://test2.txt" in uris

        res1 = next(res for res in resources if res["uri"] == "file://test1.txt")
        assert res1["name"] == "Test 1"
        assert res1["description"] == "First resource"
        assert res1["mimeType"] == "text/plain"  # default

        res2 = next(res for res in resources if res["uri"] == "file://test2.txt")
        assert res2["mimeType"] == "application/json"

    @pytest.mark.asyncio
    async def test_handle_resources_read_success(self):
        """Test successful resource read."""
        server = MCPServer("test-server")

        async def test_resource() -> str:
            return "This is test content"

        server.register_resource("test://content", test_resource, "Test Content")

        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="read-123",
            method="resources/read",
            params={"uri": "test://content"},
        )

        response, session_id = await server._handle_resources_read(message, None)

        assert response is not None
        assert session_id is None

        result = response.result
        assert "contents" in result
        contents = result["contents"]
        assert len(contents) == 1

        content = contents[0]
        assert content["uri"] == "test://content"
        assert content["mimeType"] == "text/plain"
        assert content["text"] == "This is test content"

    @pytest.mark.asyncio
    async def test_handle_resources_read_unknown_resource(self):
        """Test resource read with unknown resource."""
        server = MCPServer("test-server")

        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="read-456",
            method="resources/read",
            params={"uri": "unknown://resource"},
        )

        response, session_id = await server._handle_resources_read(message, None)

        assert response is not None
        assert hasattr(response, "error")
        # Fix: Access error as dictionary
        assert response.error["code"] == -32602
        assert "Unknown resource: unknown://resource" in response.error["message"]

    @pytest.mark.asyncio
    async def test_handle_resources_read_execution_error(self):
        """Test resource read with execution error."""
        server = MCPServer("test-server")

        async def failing_resource() -> str:
            raise IOError("Resource read failed")

        server.register_resource("test://failing", failing_resource)

        message = JSONRPCMessage(
            jsonrpc="2.0",
            id="read-789",
            method="resources/read",
            params={"uri": "test://failing"},
        )

        response, session_id = await server._handle_resources_read(message, None)

        assert response is not None
        assert hasattr(response, "error")
        # Fix: Access error as dictionary
        assert response.error["code"] == -32603
        assert "Resource read error" in response.error["message"]

    def test_format_content_string(self):
        """Test content formatting for strings."""
        server = MCPServer("test-server")

        result = server._format_content("Hello, World!")

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Hello, World!"

    def test_format_content_dict(self):
        """Test content formatting for dictionaries."""
        server = MCPServer("test-server")

        data = {"key": "value", "number": 42}
        result = server._format_content(data)

        assert len(result) == 1
        assert result[0]["type"] == "text"
        # Should be JSON formatted
        text = result[0]["text"]
        assert "key" in text
        assert "value" in text
        assert "42" in text

    def test_format_content_list(self):
        """Test content formatting for lists."""
        server = MCPServer("test-server")

        data = ["item1", {"key": "value"}, 123]
        result = server._format_content(data)

        # Each item should be formatted separately
        assert len(result) == 3
        assert all(item["type"] == "text" for item in result)
        assert result[0]["text"] == "item1"
        assert "key" in result[1]["text"]  # JSON formatted dict
        assert result[2]["text"] == "123"

    def test_format_content_other_types(self):
        """Test content formatting for other types."""
        server = MCPServer("test-server")

        # Test with number
        result = server._format_content(42)
        assert result[0]["text"] == "42"

        # Test with boolean
        result = server._format_content(True)
        assert result[0]["text"] == "True"

        # Test with None
        result = server._format_content(None)
        assert result[0]["text"] == "None"


class TestMCPServerIntegration:
    """Integration tests for MCP server with protocol handler."""

    @pytest.mark.asyncio
    async def test_server_with_protocol_handler(self):
        """Test server integration with protocol handler."""
        capabilities = ServerCapabilities(tools={"listChanged": True})
        server = MCPServer("integration-test", "1.0.0", capabilities)

        # Register a tool
        async def test_tool(message: str) -> str:
            return f"Processed: {message}"

        server.register_tool(
            "process",
            test_tool,
            {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            "Process a message",
        )

        # Test initialization through protocol handler
        init_message = JSONRPCMessage(
            jsonrpc="2.0",
            id="init-1",
            method="initialize",
            params={
                "protocolVersion": "2025-06-18",
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        response, session_id = await server.protocol_handler.handle_message(
            init_message
        )

        assert response is not None
        assert session_id is not None
        assert response.result["protocolVersion"] == "2025-06-18"
        assert response.result["serverInfo"]["name"] == "integration-test"
        assert response.result["capabilities"]["tools"] == {"listChanged": True}

        # Test tool list through protocol handler
        tools_message = JSONRPCMessage(jsonrpc="2.0", id="tools-1", method="tools/list")

        response, _ = await server.protocol_handler.handle_message(
            tools_message, session_id
        )

        assert response is not None
        tools = response.result["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "process"
        assert tools[0]["description"] == "Process a message"

        # Test tool call through protocol handler
        call_message = JSONRPCMessage(
            jsonrpc="2.0",
            id="call-1",
            method="tools/call",
            params={"name": "process", "arguments": {"message": "Hello World"}},
        )

        response, _ = await server.protocol_handler.handle_message(
            call_message, session_id
        )

        assert response is not None
        content = response.result["content"]
        assert len(content) == 1
        assert content[0]["text"] == "Processed: Hello World"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
