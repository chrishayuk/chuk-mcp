# tests/test_mcp_pydantic_base_extra.py
import json
from typing import List, Optional, Dict, Any

import pytest

from chuk_mcp.mcp_client.mcp_pydantic_base import (
    McpPydanticBase,
    Field,
    ValidationError,
    PYDANTIC_AVAILABLE,
)
from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import (
    StdioServerParameters,
)

###############################################################################
# 1. default_factory should give each instance its own object
###############################################################################

@pytest.mark.skipif(PYDANTIC_AVAILABLE, reason="fallback-only behavior")
def test_default_factory_uniqueness():
    class DFModel(McpPydanticBase):
        tags: List[str] = Field(default_factory=list)

    a = DFModel()
    b = DFModel()
    a.tags.append("x")
    assert a.tags == ["x"]
    assert b.tags == []  # Not shared

###############################################################################
# 2. Optional field is not required + type-checked
###############################################################################

@pytest.mark.skipif(PYDANTIC_AVAILABLE, reason="fallback-only behavior")
def test_optional_not_required_and_type_validation():
    class OptModel(McpPydanticBase):
        opt: Optional[int]

    # not required
    OptModel()  # should not raise

    # bad type
    with pytest.raises(ValidationError):
        OptModel(opt="bad")  # type: ignore[arg-type]

###############################################################################
# 3. exclude argument works in model_dump / dict()
###############################################################################

def _dump(model):
    """Helper to get a dict representation across impl versions."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude={"secret"})
    return model.dict(exclude={"secret"})  # Pydantic v1


def test_exclude_argument():
    class Secret(McpPydanticBase):
        public: int
        secret: str

    dumped = _dump(Secret(public=1, secret="shhh"))
    assert dumped == {"public": 1}

###############################################################################
# 4. Nested exclude_none behaviour
###############################################################################

def test_nested_exclude_none():
    class Child(McpPydanticBase):
        maybe: Optional[str] = None

    class Parent(McpPydanticBase):
        child: Child
        other: Optional[int] = None

    parent = Parent(child=Child(), other=None)

    if hasattr(parent, "model_dump"):
        dumped = parent.model_dump(exclude_none=True)
    else:
        dumped = parent.dict(exclude_none=True)

    assert "other" not in dumped
    assert "maybe" not in dumped["child"], dumped  # cascaded exclusion

###############################################################################
# 5. Special-case models get their default tweaks even in fallback
###############################################################################

def test_special_case_defaults():
    # JSONRPCMessage gets jsonrpc="2.0"
    msg = JSONRPCMessage()
    raw = msg.model_dump() if hasattr(msg, "model_dump") else msg.dict()
    assert raw["jsonrpc"] == "2.0"

    # StdioServerParameters args defaults to [] and is not required
    params = StdioServerParameters(command="echo")
    raw_p = params.model_dump() if hasattr(params, "model_dump") else params.dict()
    assert raw_p["args"] == []
