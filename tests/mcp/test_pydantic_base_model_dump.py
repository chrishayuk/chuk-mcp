# tests/test_pydantic_base_model_dump.py
import json
from typing import Any, Dict, List, Optional

import pytest

# Implementation under test
from chuk_mcp.mcp_client.mcp_pydantic_base import (
    McpPydanticBase,
    ConfigDict,
    ValidationError,
    PYDANTIC_AVAILABLE,
)

###############################################################################
# Test helpers                                                                 
###############################################################################
class _ModelWrapper:  # noqa: D401 – helper
    """Normalises *model_dump_json* across Pydantic‑v1, v2 and the fallback."""

    def __init__(self, instance):
        self._instance = instance

    def model_dump_json(self, **kwargs):  # noqa: D401
        # Fallback or Pydantic v2 already expose the method natively.
        if hasattr(self._instance, "model_dump_json"):
            if PYDANTIC_AVAILABLE and "separators" in kwargs:
                # Real Pydantic rejects «separators» kwarg
                kwargs.pop("separators")
            return self._instance.model_dump_json(**kwargs)

        # Pydantic v1 shim
        exclude_none = kwargs.pop("exclude_none", False)
        indent = kwargs.pop("indent", None)
        separators = kwargs.pop("separators", (",", ":"))
        data = self._instance.dict(exclude_none=exclude_none)
        return json.dumps(data, indent=indent, separators=separators)


def _new(model_cls, **kwargs):
    """Instantiate *model_cls* and wrap it for uniform API access."""
    return _ModelWrapper(model_cls(**kwargs))

###############################################################################
# Positive‑path tests                                                         
###############################################################################

def test_basic_dump():
    class Simple(McpPydanticBase):
        name: str
        value: int

    mdl = _new(Simple, name="foo", value=1)
    assert json.loads(mdl.model_dump_json()) == {"name": "foo", "value": 1}


def test_exclude_none():
    class Demo(McpPydanticBase):
        x: str
        y: Optional[int] = None

    mdl = _new(Demo, x="a")
    assert "y" in json.loads(mdl.model_dump_json())  # default – included
    assert "y" not in json.loads(mdl.model_dump_json(exclude_none=True))


def test_custom_json_options():
    class Complex(McpPydanticBase):
        name: str
        data: Dict[str, Any]

    mdl = _new(Complex, name="bar", data={"a": 1})

    pretty = mdl.model_dump_json(indent=4)
    if not PYDANTIC_AVAILABLE:
        compact = mdl.model_dump_json(indent=None, separators=(",", ":"))
    else:
        compact = mdl.model_dump_json(indent=None)

    # pretty‑printed output contains a newline; compact should not.
    assert pretty.startswith("{\n")
    assert "\n" not in compact  # no newlines in compact form


def test_nested_models():
    class Child(McpPydanticBase):
        id: int
        label: str

    class Parent(McpPydanticBase):
        child: Child

    dumped = json.loads(_new(Parent, child=Child(id=1, label="x")).model_dump_json())
    assert dumped == {"child": {"id": 1, "label": "x"}}


def test_arbitrary_fields_allowed():
    class Extra(McpPydanticBase):
        model_config = ConfigDict(extra="allow")

    dumped = json.loads(_new(Extra, foo=1, bar="baz").model_dump_json())
    assert dumped == {"foo": 1, "bar": "baz"}


def test_complex_types_roundtrip():
    class Big(McpPydanticBase):
        ints: List[int]
        mapping: Dict[str, Dict[str, int]]

    dumped = json.loads(_new(Big, ints=[1, 2], mapping={"a": {"x": 3}}).model_dump_json())
    assert dumped["mapping"]["a"]["x"] == 3

###############################################################################
# Negative‑path / validation tests                                            
###############################################################################

def test_missing_required_raises():
    class Req(McpPydanticBase):
        must: int

    with pytest.raises(ValidationError):
        Req()  # type: ignore[arg-type]


def test_type_validation_raises():
    class Types(McpPydanticBase):
        num: int
        tags: List[str]

    with pytest.raises(ValidationError):
        Types(num="bad", tags=[1, 2])  # type: ignore[arg-type]

###############################################################################
# Param grid – indent × exclude_none                                          
###############################################################################
@pytest.mark.parametrize("indent, exclude_none", [(2, False), (None, False), (4, True)])
def test_param_grid(indent, exclude_none):
    class Tmp(McpPydanticBase):
        x: str
        y: Optional[int] = None

    dumped = json.loads(_new(Tmp, x="z").model_dump_json(indent=indent, exclude_none=exclude_none))
    assert dumped["x"] == "z"
    if exclude_none:
        assert "y" not in dumped
    else:
        assert dumped["y"] is None


if __name__ == "__main__":
    impl = "real Pydantic" if PYDANTIC_AVAILABLE else "fallback implementation"
    print(f"Running tests with {impl}")
