"""Tests for tool types and utilities."""

import pytest
from chuk_mcp.protocol.types.tools import (
    Tool,
    ToolInputSchema,
    ToolResult,
    StructuredContent,
    CallToolRequest,
    CallToolParams,
    CallToolResult,
    create_text_tool_result,
    create_structured_tool_result,
    create_mixed_tool_result,
    create_error_tool_result,
    validate_tool_result,
    tool_result_to_dict,
    parse_tool_result,
    ToolRegistry,
    example_structured_tool,
)


class TestToolTypes:
    """Test tool type definitions."""

    def test_tool_input_schema(self):
        """Test ToolInputSchema creation."""
        schema = ToolInputSchema(
            type="object",
            properties={"name": {"type": "string"}},
            required=["name"],
        )

        assert schema.type == "object"
        assert schema.properties == {"name": {"type": "string"}}
        assert schema.required == ["name"]

    def test_tool(self):
        """Test Tool creation."""
        schema = ToolInputSchema(type="object", properties={})
        tool = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema=schema,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.inputSchema == schema

    def test_structured_content(self):
        """Test StructuredContent creation."""
        data = {"key": "value"}
        schema = {"type": "object"}
        content = StructuredContent(
            type="structured",
            data=data,
            schema_=schema,
            mimeType="application/json",
        )

        assert content.type == "structured"
        assert content.data == data
        assert content.schema_ == schema
        assert content.mimeType == "application/json"

    def test_structured_content_alias(self):
        """Test StructuredContent schema alias."""
        content = StructuredContent(
            type="structured",
            data={"test": "data"},
            schema={"type": "object"},
        )
        assert content.schema_ == {"type": "object"}

    def test_tool_result(self):
        """Test ToolResult creation."""
        from chuk_mcp.protocol.types.content import create_text_content

        content = [create_text_content("Result")]
        result = ToolResult(content=content, isError=False)

        assert result.content == content
        assert result.isError is False

    def test_tool_result_with_structured_content(self):
        """Test ToolResult with structured content."""
        structured = [StructuredContent(type="structured", data={"result": "success"})]
        result = ToolResult(structuredContent=structured, isError=False)

        assert result.structuredContent == structured
        assert result.isError is False

    def test_call_tool_request(self):
        """Test CallToolRequest creation."""
        params = CallToolParams(name="test_tool", arguments={"arg": "value"})
        request = CallToolRequest(method="tools/call", params=params)

        assert request.method == "tools/call"
        assert request.params == params

    def test_call_tool_params(self):
        """Test CallToolParams creation."""
        params = CallToolParams(name="test_tool", arguments={"key": "value"})

        assert params.name == "test_tool"
        assert params.arguments == {"key": "value"}

    def test_call_tool_result(self):
        """Test CallToolResult creation."""
        from chuk_mcp.protocol.types.content import create_text_content

        content = [create_text_content("Success")]
        result = CallToolResult(content=content, isError=False)

        assert result.content == content
        assert result.isError is False


class TestToolHelpers:
    """Test tool helper functions."""

    def test_create_text_tool_result(self):
        """Test creating text tool result."""
        result = create_text_tool_result("Success")

        assert result.content is not None
        assert len(result.content) == 1
        assert result.content[0].text == "Success"
        assert result.isError is False

    def test_create_text_tool_result_error(self):
        """Test creating text tool result with error."""
        result = create_text_tool_result("Error occurred", is_error=True)

        assert result.isError is True

    def test_create_structured_tool_result(self):
        """Test creating structured tool result."""
        data = {"status": "success", "count": 42}
        schema = {"type": "object"}

        result = create_structured_tool_result(data, schema=schema)

        assert result.structuredContent is not None
        assert len(result.structuredContent) == 1
        assert result.structuredContent[0].data == data
        assert result.structuredContent[0].schema_ == schema
        assert result.isError is False

    def test_create_structured_tool_result_custom_mime(self):
        """Test creating structured tool result with custom MIME type."""
        result = create_structured_tool_result(
            {"data": "value"}, mime_type="application/xml"
        )

        assert result.structuredContent[0].mimeType == "application/xml"

    def test_create_mixed_tool_result(self):
        """Test creating mixed tool result."""
        from chuk_mcp.protocol.types.content import create_text_content

        text_content = [create_text_content("Description")]
        structured_content = [StructuredContent(type="structured", data={"key": "val"})]

        result = create_mixed_tool_result(
            text_content=text_content, structured_content=structured_content
        )

        assert result.content == text_content
        assert result.structuredContent == structured_content
        assert result.isError is False

    def test_create_error_tool_result(self):
        """Test creating error tool result."""
        result = create_error_tool_result("Something went wrong")

        assert result.content is not None
        assert result.content[0].text == "Something went wrong"
        assert result.isError is True

    def test_create_error_tool_result_with_data(self):
        """Test creating error tool result with structured error data."""
        error_data = {"error_code": 500, "details": "Internal error"}
        result = create_error_tool_result("Error", error_data=error_data)

        assert result.structuredContent is not None
        assert result.structuredContent[0].data == error_data
        assert result.isError is True


class TestToolValidation:
    """Test tool validation functions."""

    def test_validate_tool_result_with_content(self):
        """Test validating tool result with text content."""
        result = create_text_tool_result("Success")
        assert validate_tool_result(result) is True

    def test_validate_tool_result_with_structured_content(self):
        """Test validating tool result with structured content."""
        result = create_structured_tool_result({"data": "value"})
        assert validate_tool_result(result) is True

    def test_validate_tool_result_with_mixed_content(self):
        """Test validating tool result with both content types."""
        from chuk_mcp.protocol.types.content import create_text_content

        result = create_mixed_tool_result(
            text_content=[create_text_content("Text")],
            structured_content=[
                StructuredContent(type="structured", data={"key": "value"})
            ],
        )
        assert validate_tool_result(result) is True

    def test_validate_tool_result_empty(self):
        """Test validating empty tool result."""
        result = ToolResult(content=None, structuredContent=None)
        assert validate_tool_result(result) is False

    def test_validate_tool_result_empty_lists(self):
        """Test validating tool result with empty lists."""
        result = ToolResult(content=[], structuredContent=[])
        assert validate_tool_result(result) is False

    def test_validate_tool_result_none(self):
        """Test validating None as tool result."""
        assert validate_tool_result(None) is False  # This covers line 212

    def test_tool_result_to_dict(self):
        """Test converting tool result to dictionary."""
        result = create_text_tool_result("Success")
        result_dict = tool_result_to_dict(result)

        assert isinstance(result_dict, dict)
        assert "content" in result_dict
        assert result_dict["isError"] is False

    def test_tool_result_to_dict_with_dict_input(self):
        """Test converting dictionary tool result."""
        result_dict = {"content": [], "isError": False}
        output = tool_result_to_dict(result_dict)
        assert output == result_dict

    def test_tool_result_to_dict_invalid(self):
        """Test converting invalid tool result."""
        with pytest.raises(ValueError, match="Invalid tool result type"):
            tool_result_to_dict("invalid")

    def test_parse_tool_result(self):
        """Test parsing dictionary to ToolResult."""
        data = {
            "content": [{"type": "text", "text": "Success"}],
            "isError": False,
        }
        result = parse_tool_result(data)

        assert isinstance(result, ToolResult)
        assert result.isError is False


class TestToolRegistry:
    """Test ToolRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert registry.tools == {}
        assert registry.handlers == {}

    def test_registry_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="test_tool", inputSchema=schema)

        async def handler(args):
            return "result"

        registry.register_tool(tool, handler)

        assert "test_tool" in registry.tools
        assert "test_tool" in registry.handlers
        assert registry.tools["test_tool"] == tool

    @pytest.mark.asyncio
    async def test_registry_call_tool_not_found(self):
        """Test calling non-existent tool."""
        registry = ToolRegistry()
        result = await registry.call_tool("nonexistent", {})

        assert result.isError is True
        assert "not found" in result.content[0].text

    @pytest.mark.asyncio
    async def test_registry_call_tool_returns_tool_result(self):
        """Test calling tool that returns ToolResult."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="test_tool", inputSchema=schema)

        async def handler(args):
            return create_text_tool_result("Direct result")

        registry.register_tool(tool, handler)
        result = await registry.call_tool("test_tool", {})

        assert isinstance(result, ToolResult)
        assert result.content[0].text == "Direct result"

    @pytest.mark.asyncio
    async def test_registry_call_tool_returns_dict(self):
        """Test calling tool that returns dict."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="data_tool", inputSchema=schema)

        async def handler(args):
            return {"status": "success", "data": [1, 2, 3]}

        registry.register_tool(tool, handler)
        result = await registry.call_tool("data_tool", {})

        assert result.structuredContent is not None
        assert result.structuredContent[0].data == {
            "status": "success",
            "data": [1, 2, 3],
        }

    @pytest.mark.asyncio
    async def test_registry_call_tool_returns_string(self):
        """Test calling tool that returns string."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="text_tool", inputSchema=schema)

        async def handler(args):
            return "Simple text result"

        registry.register_tool(tool, handler)
        result = await registry.call_tool("text_tool", {})

        assert result.content[0].text == "Simple text result"

    @pytest.mark.asyncio
    async def test_registry_call_tool_returns_other(self):
        """Test calling tool that returns other type."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="number_tool", inputSchema=schema)

        async def handler(args):
            return 42

        registry.register_tool(tool, handler)
        result = await registry.call_tool("number_tool", {})

        assert result.structuredContent is not None
        assert result.structuredContent[0].data == {"result": 42}

    @pytest.mark.asyncio
    async def test_registry_call_tool_exception(self):
        """Test calling tool that raises exception."""
        registry = ToolRegistry()
        schema = ToolInputSchema(type="object")
        tool = Tool(name="error_tool", inputSchema=schema)

        async def handler(args):
            raise ValueError("Something went wrong")

        registry.register_tool(tool, handler)
        result = await registry.call_tool("error_tool", {})

        assert result.isError is True
        assert "Something went wrong" in result.content[0].text
        assert result.structuredContent is not None
        assert result.structuredContent[0].data["exception_type"] == "ValueError"


class TestExampleFunctions:
    """Test example functions."""

    @pytest.mark.asyncio
    async def test_example_structured_tool(self):
        """Test example structured tool."""
        result = await example_structured_tool({"query": "hello world"})

        assert isinstance(result, ToolResult)
        assert result.content is not None
        assert result.structuredContent is not None

        # Check text content
        assert "hello world" in result.content[0].text

        # Check structured content
        data = result.structuredContent[0].data
        assert data["query"] == "hello world"
        assert data["word_count"] == 2
        assert data["character_count"] == 11
        assert "sentiment" in data
        assert "keywords" in data

    @pytest.mark.asyncio
    async def test_example_structured_tool_empty_query(self):
        """Test example structured tool with empty query."""
        result = await example_structured_tool({})

        assert isinstance(result, ToolResult)
        data = result.structuredContent[0].data
        assert data["query"] == ""
        assert data["word_count"] == 0  # Empty string has 0 words
