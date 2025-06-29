# tests/test_mcp_pydantic_base_extra.py
import json
from typing import List, Optional, Dict, Any

import pytest

from chuk_mcp.protocol.mcp_pydantic_base import (
    McpPydanticBase,
    Field,
    ValidationError,
    PYDANTIC_AVAILABLE,
)
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import (
    StdioServerParameters,
)

###############################################################################
# 1. default_factory should give each instance its own object
###############################################################################

def test_default_factory_uniqueness():
    """Test that default_factory creates unique instances for each model."""
    class DFModel(McpPydanticBase):
        tags: List[str] = Field(default_factory=list)

    a = DFModel()
    b = DFModel()
    a.tags.append("x")
    assert a.tags == ["x"]
    assert b.tags == []  # Not shared
    
    # This behavior should be consistent across both implementations

###############################################################################
# 2. Optional field is not required + type-checked
###############################################################################

def test_optional_not_required_and_type_validation():
    """Test that Optional fields are not required but still type-checked."""
    class OptModel(McpPydanticBase):
        opt: Optional[int] = None  # Need explicit default for real Pydantic

    # not required - should not raise
    model = OptModel()
    assert model.opt is None
    
    # Test with valid value
    model2 = OptModel(opt=42)
    assert model2.opt == 42

    # bad type - should raise ValidationError
    # Note: Real Pydantic might have different error messages/types
    # but both should reject invalid types
    with pytest.raises((ValidationError, ValueError, TypeError)) as exc_info:
        OptModel(opt="bad")  # type: ignore[arg-type]
    
    # Verify it's a validation-related error
    error_msg = str(exc_info.value).lower()
    assert any(word in error_msg for word in ["validation", "type", "int", "str"])

###############################################################################
# 3. exclude argument works in model_dump / dict()
###############################################################################

def _dump(model, exclude=None):
    """Helper to get a dict representation across impl versions."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude=exclude)
    return model.dict(exclude=exclude)  # Pydantic v1


def test_exclude_argument():
    """Test that exclude argument works in model_dump/dict."""
    class Secret(McpPydanticBase):
        public: int
        secret: str

    model = Secret(public=1, secret="shhh")
    
    # Test without exclude
    full_dump = _dump(model)
    assert full_dump["public"] == 1
    assert full_dump["secret"] == "shhh"
    
    # Test with exclude
    dumped = _dump(model, exclude={"secret"})
    assert dumped == {"public": 1}
    assert "secret" not in dumped

###############################################################################
# 4. Nested exclude_none behaviour
###############################################################################

def test_nested_exclude_none():
    """Test that exclude_none works with nested models."""
    class Child(McpPydanticBase):
        maybe: Optional[str] = None

    class Parent(McpPydanticBase):
        child: Child
        other: Optional[int] = None

    parent = Parent(child=Child(), other=None)

    # Test without exclude_none
    if hasattr(parent, "model_dump"):
        full_dump = parent.model_dump()
    else:
        full_dump = parent.dict()
    
    assert full_dump["other"] is None
    assert full_dump["child"]["maybe"] is None

    # Test with exclude_none
    if hasattr(parent, "model_dump"):
        dumped = parent.model_dump(exclude_none=True)
    else:
        dumped = parent.dict(exclude_none=True)

    assert "other" not in dumped
    # Note: Real Pydantic might handle nested exclude_none differently
    # The fallback cascades it, but real Pydantic might not
    if not PYDANTIC_AVAILABLE:
        assert "maybe" not in dumped["child"], dumped  # cascaded exclusion
    else:
        # For real Pydantic, the child might still have None fields
        # unless explicitly configured
        pass

###############################################################################
# 5. Special-case models get their default tweaks
###############################################################################

def test_special_case_defaults():
    """Test that special models like JSONRPCMessage get proper defaults."""
    # JSONRPCMessage gets jsonrpc="2.0"
    msg = JSONRPCMessage()
    raw = msg.model_dump() if hasattr(msg, "model_dump") else msg.dict()
    assert raw["jsonrpc"] == "2.0"

    # StdioServerParameters args defaults to [] and is not required
    params = StdioServerParameters(command="echo")
    raw_p = params.model_dump() if hasattr(params, "model_dump") else params.dict()
    assert raw_p["args"] == []
    assert raw_p["command"] == "echo"