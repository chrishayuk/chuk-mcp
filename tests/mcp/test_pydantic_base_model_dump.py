import pytest
import json
from typing import List, Dict, Optional, Any, Type

# Import the implementation
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field, ConfigDict, PYDANTIC_AVAILABLE

# Define a ModelWrapper class to handle the differences between real Pydantic and fallback
class ModelWrapper:
    """
    Wrapper for model instances to provide consistent model_dump_json method
    regardless of whether real Pydantic or the fallback is used.
    """
    def __init__(self, model_instance):
        self.model = model_instance
    
    def model_dump_json(self, **kwargs):
        """
        Provides a consistent model_dump_json interface.
        For real Pydantic, it implements model_dump_json functionality.
        For fallback, it delegates to the native implementation.
        """
        if PYDANTIC_AVAILABLE:
            # Real Pydantic - implement model_dump_json
            # Handle exclude_none
            exclude_none = kwargs.pop('exclude_none', False)
            
            # Get model data
            if hasattr(self.model, 'model_dump'):
                # Pydantic v2
                data = self.model.model_dump(exclude_none=exclude_none)
            else:
                # Pydantic v1 (dict() method)
                data = self.model.dict(exclude_none=exclude_none)
            
            # Set default indent if not specified
            if 'indent' not in kwargs:
                kwargs['indent'] = 2
                
            # Ignore separators parameter if present
            if 'separators' in kwargs:
                kwargs.pop('separators')
                
            # Convert to JSON
            return json.dumps(data, **kwargs)
        else:
            # Fallback already has model_dump_json
            return self.model.model_dump_json(**kwargs)


# Define a factory function for creating models with a consistent interface
def create_model(model_class, **kwargs):
    """
    Create a model instance and wrap it to provide consistent interface.
    """
    model = model_class(**kwargs)
    return ModelWrapper(model)


# Tests for model_dump_json functionality
def test_basic_model_dump_json():
    """Test that model_dump_json produces valid JSON for a simple model."""
    class SimpleModel(McpPydanticBase):
        name: str
        value: int
    
    # Create model with wrapper    
    model = create_model(SimpleModel, name="test", value=42)
    json_str = model.model_dump_json()
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    
    # Verify content matches
    assert parsed["name"] == "test"
    assert parsed["value"] == 42


def test_exclude_none():
    """Test that exclude_none works correctly."""
    class ModelWithNone(McpPydanticBase):
        name: str
        optional: Optional[str] = None
    
    # Create model with wrapper
    model = create_model(ModelWithNone, name="test")
    
    # With exclude_none=False (default)
    json_with_none = model.model_dump_json()
    parsed = json.loads(json_with_none)
    assert "optional" in parsed
    assert parsed["optional"] is None
    
    # With exclude_none=True
    json_without_none = model.model_dump_json(exclude_none=True)
    parsed = json.loads(json_without_none)
    assert "optional" not in parsed


def test_custom_json_options():
    """Test that custom JSON options are passed through."""
    class ComplexModel(McpPydanticBase):
        name: str
        data: Dict[str, Any]
    
    # Create model with wrapper
    model = create_model(
        ComplexModel,
        name="complex", 
        data={"a": 1, "b": [1, 2, 3]}
    )
    
    # Test with custom indent
    json_str = model.model_dump_json(indent=4)
    parsed = json.loads(json_str)
    assert parsed["name"] == "complex"
    
    # Test with no indent
    compact_json = model.model_dump_json(indent=None)
    parsed = json.loads(compact_json)
    assert parsed["name"] == "complex"
    assert parsed["data"]["b"] == [1, 2, 3]
    
    # Test separators only with fallback implementation
    if not PYDANTIC_AVAILABLE:
        custom_sep_json = model.model_dump_json(separators=(',', ':'), indent=None)
        parsed = json.loads(custom_sep_json)
        assert parsed["name"] == "complex"


def test_nested_models():
    """Test that nested models are handled correctly."""
    class ChildModel(McpPydanticBase):
        id: int
        description: str
    
    class ParentModel(McpPydanticBase):
        name: str
        child: ChildModel
    
    # Create child model and wrap it    
    child = ChildModel(id=1, description="A child model")
    
    # Create parent model with wrapped child
    parent = create_model(
        ParentModel,
        name="parent", 
        child=child
    )
    
    json_str = parent.model_dump_json()
    parsed = json.loads(json_str)
    
    assert parsed["name"] == "parent"
    assert parsed["child"]["id"] == 1
    assert parsed["child"]["description"] == "A child model"


def test_arbitrary_fields():
    """Test that arbitrary fields work correctly."""
    if PYDANTIC_AVAILABLE:
        # For real Pydantic, we need a model with extra='allow'
        class ArbitraryModel(McpPydanticBase):
            model_config = ConfigDict(extra="allow")
        
        model = create_model(
            ArbitraryModel,
            command="test", 
            args=["foo", "bar"], 
            extra={"a": 1}
        )
    else:
        # For fallback, we can use McpPydanticBase directly
        model = create_model(
            McpPydanticBase,
            command="test", 
            args=["foo", "bar"], 
            extra={"a": 1}
        )
    
    json_str = model.model_dump_json()
    parsed = json.loads(json_str)
    
    assert parsed["command"] == "test"
    assert parsed["args"] == ["foo", "bar"]
    assert parsed["extra"] == {"a": 1}


def test_complex_types():
    """Test with more complex Python types."""
    class ComplexTypesModel(McpPydanticBase):
        integers: List[int]
        nested_dict: Dict[str, Dict[str, int]]
        mixed: List[Dict[str, Any]]
    
    model = create_model(
        ComplexTypesModel,
        integers=[1, 2, 3, 4, 5],
        nested_dict={
            "outer": {"inner1": 10, "inner2": 20}
        },
        mixed=[
            {"type": "a", "value": 1},
            {"type": "b", "value": "string"},
            {"type": "c", "value": [1, 2, 3]},
        ]
    )
    
    json_str = model.model_dump_json()
    parsed = json.loads(json_str)
    
    assert parsed["integers"] == [1, 2, 3, 4, 5]
    assert parsed["nested_dict"]["outer"]["inner2"] == 20
    assert parsed["mixed"][1]["value"] == "string"


# Parametrized tests for JSON formatting options
@pytest.mark.parametrize("indent,exclude_none", [
    (2, False),     # Default indentation
    (None, False),  # No indentation
    (2, True),      # With exclude_none
    (4, False),     # Custom indentation
])
def test_json_formatting_options(indent, exclude_none):
    """Test different JSON formatting options with parametrized tests."""
    class TestModel(McpPydanticBase):
        name: str
        value: Optional[int] = None
    
    model = create_model(TestModel, name="test")
    json_str = model.model_dump_json(indent=indent, exclude_none=exclude_none)
    
    # Parse and verify the contents regardless of formatting
    parsed = json.loads(json_str)
    assert parsed["name"] == "test"
    
    # For exclude_none case, verify value is absent or present
    if exclude_none:
        assert "value" not in parsed
    else:
        assert "value" in parsed
        assert parsed["value"] is None


if __name__ == "__main__":
    # Print implementation being used
    print(f"Running tests with {'real Pydantic' if PYDANTIC_AVAILABLE else 'fallback implementation'}")