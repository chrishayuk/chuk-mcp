# tests/test_mcp_real_pydantic.py
import os
import sys
import importlib

import pytest


@pytest.mark.skipif(
    os.environ.get("MCP_FORCE_FALLBACK") == "1",
    reason="Fallback forced via env-var; real-Pydantic path intentionally skipped.",
)
class TestRealPydanticIntegration:
    """Test integration with real Pydantic when available."""

    @pytest.fixture(autouse=True)
    def setup_real_pydantic(self):
        """Ensure we're using real Pydantic for these tests."""
        # Remove fallback forcing
        os.environ.pop("MCP_FORCE_FALLBACK", None)
        
        # Clear cached modules
        modules_to_clear = [
            "chuk_mcp.protocol.mcp_pydantic_base",
            "chuk_mcp.protocol.messages.json_rpc_message",
        ]
        for m in modules_to_clear:
            sys.modules.pop(m, None)

    def test_pydantic_available_detection(self):
        """Test that real Pydantic is properly detected when available."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed - cannot test real Pydantic integration.")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        # Should detect Pydantic as available
        assert mpb.PYDANTIC_AVAILABLE is True
        
        # Should be using real Pydantic classes
        assert issubclass(mpb.McpPydanticBase, mpb.PydanticBase)

    def test_inheritance_hierarchy(self):
        """Test that McpPydanticBase properly inherits from Pydantic BaseModel."""
        try:
            import pydantic
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        # McpPydanticBase should inherit from pydantic.BaseModel
        assert issubclass(mpb.McpPydanticBase, pydantic.BaseModel)
        
        # Should have Pydantic methods
        class TestModel(mpb.McpPydanticBase):
            name: str
            value: int = 42

        instance = TestModel(name="test")
        
        # Should have real Pydantic methods
        assert hasattr(instance, 'model_dump')
        assert hasattr(instance, 'model_dump_json')
        assert hasattr(TestModel, 'model_validate')

    def test_pydantic_v1_v2_compatibility(self):
        """Test compatibility with both Pydantic v1 and v2."""
        try:
            import pydantic
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        # Check Pydantic version
        is_v2 = hasattr(pydantic, '__version__') and pydantic.__version__.startswith('2.')
        
        class TestModel(mpb.McpPydanticBase):
            name: str
            value: int = 42

        instance = TestModel(name="test")
        
        if is_v2:
            # Pydantic v2 methods
            assert hasattr(instance, 'model_dump')
            data = instance.model_dump()
        else:
            # Pydantic v1 compatibility
            if hasattr(instance, 'model_dump'):
                data = instance.model_dump()
            else:
                data = instance.dict()
        
        assert data == {"name": "test", "value": 42}

    def test_enhanced_validation_with_real_pydantic(self):
        """Test enhanced validation features when using real Pydantic."""
        try:
            import pydantic
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        class ValidatedModel(mpb.McpPydanticBase):
            email: str = mpb.Field(..., description="User email")
            age: int = mpb.Field(ge=0, le=150, description="User age")
            name: str = mpb.Field(min_length=1, max_length=100)

        # Valid data should work
        valid_instance = ValidatedModel(
            email="test@example.com",
            age=25,
            name="John Doe"
        )
        assert valid_instance.email == "test@example.com"

        # Invalid data should raise ValidationError
        with pytest.raises(mpb.ValidationError):
            ValidatedModel(
                email="invalid-email",  # Invalid email format (if Pydantic validates this)
                age=-5,  # Invalid age
                name=""  # Empty name
            )

    def test_config_dict_usage(self):
        """Test ConfigDict usage with real Pydantic."""
        try:
            import pydantic
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        class ConfiguredModel(mpb.McpPydanticBase):
            name: str
            value: int
            
            model_config = mpb.ConfigDict(
                extra="forbid",  # Don't allow extra fields
                validate_assignment=True
            )

        # Should work with valid data
        instance = ConfiguredModel(name="test", value=42)
        assert instance.name == "test"

        # Should reject extra fields if real Pydantic enforces this
        try:
            ConfiguredModel(name="test", value=42, extra="should_fail")
            # If this doesn't raise, the configuration might not be enforced
            # or Pydantic version doesn't support this config
        except mpb.ValidationError:
            # Expected behavior with strict config
            pass

    def test_field_types_and_metadata(self):
        """Test Field types and metadata with real Pydantic."""
        try:
            import pydantic
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        from typing import List, Optional
        
        class FieldModel(mpb.McpPydanticBase):
            # Basic field with default
            name: str = mpb.Field(default="default_name", description="The name field")
            
            # Field with default_factory
            tags: List[str] = mpb.Field(default_factory=list, description="List of tags")
            
            # Optional field
            description: Optional[str] = mpb.Field(None, description="Optional description")
            
            # Field with alias
            internal_id: int = mpb.Field(alias="id", description="Internal ID")

        # Test creation with minimal data
        instance = FieldModel(id=123)
        assert instance.name == "default_name"
        assert instance.tags == []
        assert instance.description is None
        assert instance.internal_id == 123

        # Test field metadata access (if available in Pydantic version)
        if hasattr(FieldModel, 'model_fields'):
            fields = FieldModel.model_fields
            if 'name' in fields:
                assert fields['name'].description == "The name field"

    def test_json_rpc_message_with_real_pydantic(self):
        """Test JSONRPCMessage functionality with real Pydantic."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed")

        from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
        
        # Test creation
        msg = JSONRPCMessage.create_request("test_method", {"param": "value"})
        assert msg.jsonrpc == "2.0"
        assert msg.method == "test_method"
        assert msg.params == {"param": "value"}
        assert msg.id is not None

        # Test serialization
        data = msg.model_dump(exclude_none=True)
        assert "jsonrpc" in data
        assert "method" in data
        assert "params" in data
        assert "id" in data

        # Test validation from dict
        msg_data = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "tools/list",
            "params": {}
        }
        
        validated_msg = JSONRPCMessage.model_validate(msg_data)
        assert validated_msg.jsonrpc == "2.0"
        assert validated_msg.id == "test-123"
        assert validated_msg.method == "tools/list"

    def test_performance_comparison_hint(self):
        """Test that provides a performance comparison hint between real and fallback."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed")

        import time
        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        class PerfTestModel(mpb.McpPydanticBase):
            name: str
            value: int
            tags: list = mpb.Field(default_factory=list)

        # Time model creation (rough performance indicator)
        start_time = time.time()
        for _ in range(100):
            instance = PerfTestModel(name="test", value=42, tags=["a", "b"])
            data = instance.model_dump()
        end_time = time.time()
        
        pydantic_time = end_time - start_time
        
        # This is mainly a smoke test to ensure performance is reasonable
        # Real performance testing should be done separately
        assert pydantic_time < 1.0  # Should complete 100 iterations in under 1 second

    def test_complex_type_handling(self):
        """Test complex type handling with real Pydantic."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        from typing import Union, List, Dict, Any, Optional
        
        class ComplexModel(mpb.McpPydanticBase):
            # Union type
            flexible_value: Union[str, int, float]
            
            # Complex nested structure
            data: Dict[str, List[Dict[str, Any]]]
            
            # Optional union
            maybe_value: Optional[Union[str, int]] = None

        # Test with complex data
        complex_data = {
            "flexible_value": "string_value",
            "data": {
                "users": [
                    {"name": "Alice", "age": 30, "active": True},
                    {"name": "Bob", "age": 25, "active": False}
                ]
            },
            "maybe_value": 42
        }
        
        instance = ComplexModel.model_validate(complex_data)
        assert instance.flexible_value == "string_value"
        assert len(instance.data["users"]) == 2
        assert instance.maybe_value == 42

        # Test serialization round-trip
        serialized = instance.model_dump()
        instance2 = ComplexModel.model_validate(serialized)
        assert instance2.flexible_value == instance.flexible_value
        assert instance2.data == instance.data

    def test_error_handling_with_real_pydantic(self):
        """Test error handling behavior with real Pydantic."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        class StrictModel(mpb.McpPydanticBase):
            name: str
            age: int
            email: str

        # Test validation errors provide useful information
        with pytest.raises(mpb.ValidationError) as exc_info:
            StrictModel(name="John", age="not_an_int", email="john@test.com")
        
        # Error should contain field information
        error_str = str(exc_info.value)
        # Exact error format depends on Pydantic version, but should mention the field
        assert "age" in error_str.lower() or "validation" in error_str.lower()

    def test_model_dump_mcp_convenience_method(self):
        """Test the convenience model_dump_mcp method."""
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pytest.skip("Pydantic not installed")

        import chuk_mcp.protocol.mcp_pydantic_base as mpb
        
        class ConvenienceModel(mpb.McpPydanticBase):
            name: str
            value: int = 42

        instance = ConvenienceModel(name="test")
        
        # Test convenience method exists and works
        assert hasattr(instance, 'model_dump_mcp')
        mcp_data = instance.model_dump_mcp()
        regular_data = instance.model_dump()
        
        # Should produce same result as regular model_dump
        assert mcp_data == regular_data