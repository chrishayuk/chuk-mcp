# tests/mcp/protocol/types/test_tools.py
"""
Tests for tool-related types and utilities.

Tests both legacy content and new structured content features from 2025-06-18.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

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
from chuk_mcp.protocol.types.content import create_text_content, create_image_content


###############################################################################
# Core Type Tests
###############################################################################

def test_tool_input_schema_creation():
    """Test creating tool input schemas."""
    schema = ToolInputSchema(
        type="object",
        properties={
            "name": {"type": "string", "description": "User's name"},
            "age": {"type": "integer", "minimum": 0}
        },
        required=["name"]
    )
    
    assert schema.type == "object"
    assert "name" in schema.properties
    assert "age" in schema.properties
    assert schema.required == ["name"]


def test_tool_input_schema_defaults():
    """Test tool input schema with defaults."""
    schema = ToolInputSchema()
    
    assert schema.type == "object"
    assert schema.properties is None
    assert schema.required is None


def test_tool_creation():
    """Test creating tool definitions."""
    schema = ToolInputSchema(
        type="object",
        properties={"query": {"type": "string"}},
        required=["query"]
    )
    
    tool = Tool(
        name="search",
        description="Search for information",
        inputSchema=schema
    )
    
    assert tool.name == "search"
    assert tool.description == "Search for information"
    assert tool.inputSchema.properties["query"]["type"] == "string"


def test_tool_minimal():
    """Test tool with minimal required fields."""
    schema = ToolInputSchema()
    tool = Tool(name="ping", inputSchema=schema)
    
    assert tool.name == "ping"
    assert tool.description is None
    assert tool.inputSchema.type == "object"


def test_structured_content_creation():
    """Test creating structured content (2025-06-18 feature)."""
    data = {
        "temperature": 72.5,
        "humidity": 45,
        "pressure": 1013.25,
        "timestamp": "2025-07-09T12:00:00Z"
    }
    
    content = StructuredContent(
        type="structured",
        data=data,
        schema={
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "humidity": {"type": "integer"},
                "pressure": {"type": "number"},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        },
        mimeType="application/json"
    )
    
    assert content.type == "structured"
    assert content.data["temperature"] == 72.5
    # Access schema via schema_ attribute (internal) or model_dump() for JSON representation
    assert content.schema_["properties"]["temperature"]["type"] == "number"
    assert content.mimeType == "application/json"


def test_structured_content_minimal():
    """Test structured content with minimal fields."""
    content = StructuredContent(
        type="structured",
        data={"message": "hello"}
    )
    
    assert content.type == "structured"
    assert content.data == {"message": "hello"}
    assert content.schema_ is None
    assert content.mimeType is None


def test_tool_result_text_only():
    """Test tool result with text content only."""
    result = ToolResult(
        content=[create_text_content("Hello, world!")],
        isError=False
    )
    
    assert len(result.content) == 1
    assert result.content[0].text == "Hello, world!"
    assert result.structuredContent is None
    assert result.isError is False


def test_tool_result_structured_only():
    """Test tool result with structured content only."""
    structured = StructuredContent(
        type="structured",
        data={"result": "success", "value": 42}
    )
    
    result = ToolResult(
        structuredContent=[structured],
        isError=False
    )
    
    assert result.content is None
    assert len(result.structuredContent) == 1
    assert result.structuredContent[0].data["value"] == 42
    assert result.isError is False


def test_tool_result_mixed_content():
    """Test tool result with both text and structured content."""
    text_content = [create_text_content("Analysis complete")]
    structured_content = [StructuredContent(
        type="structured",
        data={"score": 0.95, "confidence": "high"}
    )]
    
    result = ToolResult(
        content=text_content,
        structuredContent=structured_content,
        isError=False
    )
    
    assert len(result.content) == 1
    assert len(result.structuredContent) == 1
    assert result.content[0].text == "Analysis complete"
    assert result.structuredContent[0].data["score"] == 0.95


def test_call_tool_params():
    """Test call tool parameters."""
    params = CallToolParams(
        name="calculator",
        arguments={"operation": "add", "a": 5, "b": 3}
    )
    
    assert params.name == "calculator"
    assert params.arguments["operation"] == "add"
    assert params.arguments["a"] == 5


def test_call_tool_params_no_args():
    """Test call tool parameters without arguments."""
    params = CallToolParams(name="ping")
    
    assert params.name == "ping"
    assert params.arguments is None


def test_call_tool_request():
    """Test call tool request structure."""
    request = CallToolRequest(
        method="tools/call",
        params=CallToolParams(name="test", arguments={"key": "value"})
    )
    
    assert request.method == "tools/call"
    assert request.params.name == "test"
    assert request.params.arguments["key"] == "value"


def test_call_tool_result():
    """Test call tool result structure."""
    result = CallToolResult(
        content=[create_text_content("Success")],
        isError=False
    )
    
    assert len(result.content) == 1
    assert result.content[0].text == "Success"
    assert result.isError is False


###############################################################################
# Helper Function Tests
###############################################################################

def test_create_text_tool_result():
    """Test creating simple text tool results."""
    result = create_text_tool_result("Hello, world!")
    
    assert len(result.content) == 1
    assert result.content[0].text == "Hello, world!"
    assert result.structuredContent is None
    assert result.isError is False


def test_create_text_tool_result_error():
    """Test creating error text tool result."""
    result = create_text_tool_result("Something went wrong", is_error=True)
    
    assert result.content[0].text == "Something went wrong"
    assert result.isError is True


def test_create_structured_tool_result():
    """Test creating structured tool results."""
    data = {"temperature": 25.5, "unit": "celsius"}
    schema = {
        "type": "object",
        "properties": {
            "temperature": {"type": "number"},
            "unit": {"type": "string"}
        }
    }
    
    result = create_structured_tool_result(data, schema=schema)
    
    assert result.content is None
    assert len(result.structuredContent) == 1
    assert result.structuredContent[0].data["temperature"] == 25.5
    # Check the schema via the internal field
    assert result.structuredContent[0].schema_ == schema
    assert result.structuredContent[0].mimeType == "application/json"
    assert result.isError is False


def test_create_structured_tool_result_minimal():
    """Test creating structured tool result with minimal parameters."""
    data = {"status": "ok"}
    
    result = create_structured_tool_result(data)
    
    assert result.structuredContent[0].data == data
    assert result.structuredContent[0].schema_ is None
    assert result.structuredContent[0].mimeType == "application/json"


def test_create_mixed_tool_result():
    """Test creating mixed content tool result."""
    text_content = [create_text_content("Process completed")]
    structured_content = [StructuredContent(
        type="structured",
        data={"duration": 1.5, "items_processed": 100}
    )]
    
    result = create_mixed_tool_result(
        text_content=text_content,
        structured_content=structured_content
    )
    
    assert len(result.content) == 1
    assert len(result.structuredContent) == 1
    assert result.content[0].text == "Process completed"
    assert result.structuredContent[0].data["duration"] == 1.5


def test_create_error_tool_result():
    """Test creating error tool results."""
    error_data = {
        "error_code": "INVALID_INPUT",
        "details": "Missing required field 'name'"
    }
    
    result = create_error_tool_result(
        "Validation failed",
        error_data=error_data
    )
    
    assert result.isError is True
    assert result.content[0].text == "Validation failed"
    assert len(result.structuredContent) == 1
    assert result.structuredContent[0].data["error_code"] == "INVALID_INPUT"


def test_create_error_tool_result_text_only():
    """Test creating error tool result with text only."""
    result = create_error_tool_result("Simple error")
    
    assert result.isError is True
    assert result.content[0].text == "Simple error"
    assert result.structuredContent is None


def test_validate_tool_result():
    """Test tool result validation."""
    # Valid - has text content
    result1 = ToolResult(content=[create_text_content("test")])
    assert validate_tool_result(result1) is True
    
    # Valid - has structured content
    result2 = ToolResult(structuredContent=[StructuredContent(
        type="structured", data={"test": True}
    )])
    assert validate_tool_result(result2) is True
    
    # Valid - has both
    result3 = ToolResult(
        content=[create_text_content("test")],
        structuredContent=[StructuredContent(type="structured", data={})]
    )
    assert validate_tool_result(result3) is True
    
    # Invalid - has neither
    result4 = ToolResult()
    assert validate_tool_result(result4) is False
    
    # Invalid - empty lists
    result5 = ToolResult(content=[], structuredContent=[])
    assert validate_tool_result(result5) is False


def test_tool_result_to_dict():
    """Test converting tool result to dictionary."""
    result = create_text_tool_result("test")
    data = tool_result_to_dict(result)
    
    assert isinstance(data, dict)
    assert "content" in data
    assert data["content"][0]["text"] == "test"
    assert data["isError"] is False


def test_tool_result_to_dict_from_dict():
    """Test converting dict to dict (passthrough)."""
    original_dict = {"content": [], "isError": False}
    result_dict = tool_result_to_dict(original_dict)
    
    assert result_dict == original_dict


def test_parse_tool_result():
    """Test parsing dictionary to tool result."""
    data = {
        "content": [{"type": "text", "text": "Hello"}],
        "isError": False
    }
    
    result = parse_tool_result(data)
    
    assert isinstance(result, ToolResult)
    assert result.content[0].text == "Hello"
    assert result.isError is False


###############################################################################
# Tool Registry Tests
###############################################################################

def test_tool_registry_creation():
    """Test creating a tool registry."""
    registry = ToolRegistry()
    
    assert len(registry.tools) == 0
    assert len(registry.handlers) == 0


def test_tool_registry_register_tool():
    """Test registering tools in registry."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema(
        properties={"name": {"type": "string"}},
        required=["name"]
    )
    tool = Tool(name="greet", description="Greet someone", inputSchema=schema)
    
    async def greet_handler(args):
        name = args.get("name", "World")
        return f"Hello, {name}!"
    
    registry.register_tool(tool, greet_handler)
    
    assert "greet" in registry.tools
    assert "greet" in registry.handlers
    assert registry.tools["greet"].description == "Greet someone"


@pytest.mark.asyncio
async def test_tool_registry_call_tool_string_result():
    """Test calling tool that returns string."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema()
    tool = Tool(name="ping", inputSchema=schema)
    
    async def ping_handler(args):
        return "pong"
    
    registry.register_tool(tool, ping_handler)
    
    result = await registry.call_tool("ping", {})
    
    assert isinstance(result, ToolResult)
    assert result.content[0].text == "pong"
    assert result.isError is False


@pytest.mark.asyncio
async def test_tool_registry_call_tool_dict_result():
    """Test calling tool that returns dictionary."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema()
    tool = Tool(name="status", inputSchema=schema)
    
    async def status_handler(args):
        return {"status": "healthy", "timestamp": "2025-07-09T12:00:00Z"}
    
    registry.register_tool(tool, status_handler)
    
    result = await registry.call_tool("status", {})
    
    assert isinstance(result, ToolResult)
    assert result.structuredContent[0].data["status"] == "healthy"
    assert result.isError is False


@pytest.mark.asyncio
async def test_tool_registry_call_tool_result_object():
    """Test calling tool that returns ToolResult object."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema()
    tool = Tool(name="analyze", inputSchema=schema)
    
    async def analyze_handler(args):
        return create_mixed_tool_result(
            text_content=[create_text_content("Analysis complete")],
            structured_content=[StructuredContent(
                type="structured",
                data={"score": 0.85}
            )]
        )
    
    registry.register_tool(tool, analyze_handler)
    
    result = await registry.call_tool("analyze", {})
    
    assert isinstance(result, ToolResult)
    assert result.content[0].text == "Analysis complete"
    assert result.structuredContent[0].data["score"] == 0.85


@pytest.mark.asyncio
async def test_tool_registry_call_unknown_tool():
    """Test calling unknown tool."""
    registry = ToolRegistry()
    
    result = await registry.call_tool("unknown", {})
    
    assert isinstance(result, ToolResult)
    assert result.isError is True
    assert "not found" in result.content[0].text


@pytest.mark.asyncio
async def test_tool_registry_call_tool_with_exception():
    """Test calling tool that raises exception."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema()
    tool = Tool(name="error_tool", inputSchema=schema)
    
    async def error_handler(args):
        raise ValueError("Something went wrong")
    
    registry.register_tool(tool, error_handler)
    
    result = await registry.call_tool("error_tool", {})
    
    assert isinstance(result, ToolResult)
    assert result.isError is True
    assert "Something went wrong" in result.content[0].text
    assert result.structuredContent[0].data["exception_type"] == "ValueError"


@pytest.mark.asyncio
async def test_tool_registry_call_tool_other_result():
    """Test calling tool that returns other types."""
    registry = ToolRegistry()
    
    schema = ToolInputSchema()
    tool = Tool(name="number_tool", inputSchema=schema)
    
    async def number_handler(args):
        return 42
    
    registry.register_tool(tool, number_handler)
    
    result = await registry.call_tool("number_tool", {})
    
    assert isinstance(result, ToolResult)
    assert result.structuredContent[0].data["result"] == 42


###############################################################################
# Example Tool Tests
###############################################################################

@pytest.mark.asyncio
async def test_example_structured_tool():
    """Test the example structured tool."""
    arguments = {"query": "Hello world example"}
    
    result = await example_structured_tool(arguments)
    
    assert isinstance(result, ToolResult)
    assert result.isError is False
    
    # Check text content
    assert len(result.content) == 1
    assert "Hello world example" in result.content[0].text
    assert "3 words" in result.content[0].text
    
    # Check structured content
    assert len(result.structuredContent) == 1
    structured = result.structuredContent[0]
    assert structured.type == "structured"
    assert structured.data["query"] == "Hello world example"
    assert structured.data["word_count"] == 3
    assert structured.data["character_count"] == 19
    assert structured.data["sentiment"] == "neutral"
    assert structured.data["keywords"] == ["Hello", "world", "example"]
    
    # Check schema (direct field access)
    assert structured.schema is not None
    assert "query" in structured.schema["properties"]
    assert structured.schema["properties"]["word_count"]["type"] == "integer"


@pytest.mark.asyncio
async def test_example_structured_tool_empty_query():
    """Test example tool with empty query."""
    result = await example_structured_tool({})
    
    assert result.structuredContent[0].data["query"] == ""
    assert result.structuredContent[0].data["word_count"] == 0
    assert result.structuredContent[0].data["character_count"] == 0
    assert result.structuredContent[0].data["keywords"] == []


###############################################################################
# Serialization and Compatibility Tests
###############################################################################

def test_tool_serialization():
    """Test tool serialization."""
    schema = ToolInputSchema(
        properties={"input": {"type": "string"}},
        required=["input"]
    )
    tool = Tool(name="test", description="Test tool", inputSchema=schema)
    
    data = tool.model_dump()
    
    assert data["name"] == "test"
    assert data["description"] == "Test tool"
    assert data["inputSchema"]["properties"]["input"]["type"] == "string"


def test_structured_content_serialization():
    """Test structured content serialization."""
    content = StructuredContent(
        type="structured",
        data={"key": "value"},
        schema={"type": "object"},
        mimeType="application/json"
    )
    
    data = content.model_dump()
    
    assert data["type"] == "structured"
    assert data["data"] == {"key": "value"}
    # Check that schema is serialized correctly with the alias
    assert data["schema"] == {"type": "object"}
    assert data["mimeType"] == "application/json"


def test_tool_result_serialization():
    """Test tool result serialization."""
    result = ToolResult(
        content=[create_text_content("test")],
        structuredContent=[StructuredContent(
            type="structured",
            data={"result": True}
        )],
        isError=False
    )
    
    data = result.model_dump(exclude_none=True)
    
    assert "content" in data
    assert "structuredContent" in data
    assert data["isError"] is False
    assert data["content"][0]["text"] == "test"
    assert data["structuredContent"][0]["data"]["result"] is True


def test_backwards_compatibility():
    """Test backwards compatibility with legacy tool results."""
    # Legacy result (pre-2025-06-18) - only text content
    legacy_data = {
        "content": [{"type": "text", "text": "Legacy result"}],
        "isError": False
    }
    
    result = ToolResult.model_validate(legacy_data)
    
    assert result.content[0].text == "Legacy result"
    assert result.structuredContent is None
    assert result.isError is False


def test_forward_compatibility():
    """Test forward compatibility with future fields."""
    # Future result with unknown fields
    future_data = {
        "content": [{"type": "text", "text": "Future result"}],
        "structuredContent": [{"type": "structured", "data": {"key": "value"}}],
        "isError": False,
        "futureField": "should be preserved"  # Unknown field
    }
    
    # Should parse without error due to extra="allow"
    result = ToolResult.model_validate(future_data)
    
    assert result.content[0].text == "Future result"
    assert result.structuredContent[0].data["key"] == "value"


###############################################################################
# Edge Cases and Error Handling
###############################################################################

def test_tool_input_schema_extra_fields():
    """Test tool input schema with extra fields."""
    schema = ToolInputSchema(
        type="object",
        properties={"name": {"type": "string"}},
        customField="allowed"  # Extra field should be preserved
    )
    
    data = schema.model_dump()
    assert data["customField"] == "allowed"


def test_empty_structured_content_data():
    """Test structured content with empty data."""
    content = StructuredContent(
        type="structured",
        data={}
    )
    
    assert content.data == {}
    assert content.type == "structured"


def test_tool_result_validation_edge_cases():
    """Test tool result validation with edge cases."""
    # None content lists
    result1 = ToolResult(content=None, structuredContent=None)
    assert validate_tool_result(result1) is False
    
    # Mixed None and empty
    result2 = ToolResult(content=[], structuredContent=None)
    assert validate_tool_result(result2) is False
    
    # One empty, one with content
    result3 = ToolResult(
        content=[],
        structuredContent=[StructuredContent(type="structured", data={})]
    )
    assert validate_tool_result(result3) is True


def test_tool_result_to_dict_invalid_type():
    """Test tool_result_to_dict with invalid input."""
    with pytest.raises(ValueError):
        tool_result_to_dict("invalid input")


###############################################################################
# Integration Tests
###############################################################################

@pytest.mark.asyncio
async def test_full_tool_workflow():
    """Test complete tool workflow from definition to execution."""
    # 1. Define a tool
    schema = ToolInputSchema(
        type="object",
        properties={
            "numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": "List of numbers to process"
            },
            "operation": {
                "type": "string",
                "enum": ["sum", "average", "max", "min"],
                "description": "Operation to perform"
            }
        },
        required=["numbers", "operation"]
    )
    
    tool = Tool(
        name="math_processor",
        description="Process numbers with various operations",
        inputSchema=schema
    )
    
    # 2. Implement handler
    async def math_handler(args):
        numbers = args["numbers"]
        operation = args["operation"]
        
        if operation == "sum":
            result_value = sum(numbers)
        elif operation == "average":
            result_value = sum(numbers) / len(numbers)
        elif operation == "max":
            result_value = max(numbers)
        elif operation == "min":
            result_value = min(numbers)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Return mixed content result
        text_content = [create_text_content(
            f"Calculated {operation} of {numbers}: {result_value}"
        )]
        
        structured_content = [StructuredContent(
            type="structured",
            data={
                "operation": operation,
                "input_numbers": numbers,
                "result": result_value,
                "count": len(numbers)
            },
            schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "input_numbers": {"type": "array", "items": {"type": "number"}},
                    "result": {"type": "number"},
                    "count": {"type": "integer"}
                }
            },
            mimeType="application/json"
        )]
        
        return ToolResult(
            content=text_content,
            structuredContent=structured_content,
            isError=False
        )
    
    # 3. Register and test
    registry = ToolRegistry()
    registry.register_tool(tool, math_handler)
    
    # Test different operations
    test_cases = [
        ({"numbers": [1, 2, 3, 4, 5], "operation": "sum"}, 15),
        ({"numbers": [10, 20, 30], "operation": "average"}, 20.0),
        ({"numbers": [5, 1, 9, 3], "operation": "max"}, 9),
        ({"numbers": [7, 2, 8, 1], "operation": "min"}, 1),
    ]
    
    for args, expected in test_cases:
        result = await registry.call_tool("math_processor", args)
        
        assert isinstance(result, ToolResult)
        assert result.isError is False
        
        # Check text content
        assert str(expected) in result.content[0].text
        
        # Check structured content
        structured_data = result.structuredContent[0].data
        assert structured_data["operation"] == args["operation"]
        assert structured_data["result"] == expected
        assert structured_data["input_numbers"] == args["numbers"]

def test_structured_content_creation():
    """Test creating structured content (2025-06-18 feature)."""
    data = {
        "temperature": 72.5,
        "humidity": 45,
        "pressure": 1013.25,
        "timestamp": "2025-07-09T12:00:00Z"
    }
    
    content = StructuredContent(
        type="structured",
        data=data,
        schema={
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "humidity": {"type": "integer"},
                "pressure": {"type": "number"},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        },
        mimeType="application/json"
    )
    
    assert content.type == "structured"
    assert content.data["temperature"] == 72.5
    # Now use direct field access
    assert content.schema["properties"]["temperature"]["type"] == "number"
    assert content.mimeType == "application/json"


def test_structured_content_minimal():
    """Test structured content with minimal fields."""
    content = StructuredContent(
        type="structured",
        data={"message": "hello"}
    )
    
    assert content.type == "structured"
    assert content.data == {"message": "hello"}
    assert content.schema is None
    assert content.mimeType is None


def test_create_structured_tool_result():
    """Test creating structured tool results."""
    data = {"temperature": 25.5, "unit": "celsius"}
    schema = {
        "type": "object",
        "properties": {
            "temperature": {"type": "number"},
            "unit": {"type": "string"}
        }
    }
    
    result = create_structured_tool_result(data, schema=schema)
    
    assert result.content is None
    assert len(result.structuredContent) == 1
    assert result.structuredContent[0].data["temperature"] == 25.5
    # Use direct field access
    assert result.structuredContent[0].schema == schema
    assert result.structuredContent[0].mimeType == "application/json"
    assert result.isError is False


def test_create_structured_tool_result_minimal():
    """Test creating structured tool result with minimal parameters."""
    data = {"status": "ok"}
    
    result = create_structured_tool_result(data)
    
    assert result.structuredContent[0].data == data
    assert result.structuredContent[0].schema is None
    assert result.structuredContent[0].mimeType == "application/json"


def test_structured_content_serialization():
    """Test structured content serialization."""
    content = StructuredContent(
        type="structured",
        data={"key": "value"},
        schema={"type": "object"},
        mimeType="application/json"
    )
    
    data = content.model_dump()
    
    assert data["type"] == "structured"
    assert data["data"] == {"key": "value"}
    # Direct field should serialize correctly
    assert data["schema"] == {"type": "object"}
    assert data["mimeType"] == "application/json"


def test_2025_06_18_feature_completeness():
    """Test that all 2025-06-18 features are implemented."""
    # Structured content attributes (check as instance attributes)
    content_instance = StructuredContent(type="structured", data={})
    assert hasattr(content_instance, 'type')
    assert hasattr(content_instance, 'data')
    assert hasattr(content_instance, 'schema')  # Direct field
    assert hasattr(content_instance, 'mimeType')
    
    # Tool result structured content (check on instance, not class)
    result_instance = ToolResult()
    assert hasattr(result_instance, 'structuredContent')
    
    # Helper functions for structured content
    result = create_structured_tool_result({"test": True})
    assert result.structuredContent is not None
    
    # Mixed content support
    mixed_result = create_mixed_tool_result(
        text_content=[create_text_content("test")],
        structured_content=[StructuredContent(type="structured", data={})]
    )
    assert mixed_result.content is not None
    assert mixed_result.structuredContent is not None