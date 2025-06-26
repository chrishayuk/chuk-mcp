# tests/test_mcp_pydantic_fallback.py

import importlib
import sys

import pytest


def _reload_with_fallback(monkeypatch):
    """Reload *mcp_pydantic_base* forcing the pure-python fallback path."""
    # 1. Force env-var so import branch chooses the fallback regardless of
    #    whether real Pydantic is installed in the environment running the tests.
    monkeypatch.setenv("MCP_FORCE_FALLBACK", "1")

    # 2. Remove cached modules so reload really re-evaluates the top of file.
    for m in list(sys.modules):
        if m.startswith("chuk_mcp.mcp_client.mcp_pydantic_base") or m == "pydantic":
            sys.modules.pop(m, None)

    # 3. (Re)import
    import chuk_mcp.mcp_client.mcp_pydantic_base as mpb  # noqa: WPS433 – runtime import needed

    importlib.reload(mpb)
    return mpb


def test_fallback_basic(monkeypatch):
    mpb = _reload_with_fallback(monkeypatch)
    McpPydanticBase, Field, ConfigDict = (
        mpb.McpPydanticBase,
        mpb.Field,
        mpb.ConfigDict,
    )

    # ------------------------------------------------------------------
    # Define a tiny model that uses a default + extra-allow config
    # ------------------------------------------------------------------
    class Model(McpPydanticBase):
        x: int = Field(default=123)
        model_config = ConfigDict(extra="allow")

    # 1) Defaults work
    inst = Model()
    dump = inst.model_dump()
    assert dump["x"] == 123
    # no private keys in the dump
    assert all(not k.startswith("_") for k in dump)

    # 2) model_validate works
    inst2 = Model.model_validate({"x": 456})
    assert inst2.x == 456

    # 3) class‐level config still accessible
    assert inst.model_config == {"extra": "allow"}

    # 4) Extra fields are allowed
    extra_data = {"x": 789, "command": "uv", "args": ["run", "srv"]}
    inst3 = Model.model_validate(extra_data)
    assert inst3.command == "uv"
    assert inst3.args == ["run", "srv"]

    # 5) They round-trip through model_dump for only public fields
    dump3 = inst3.model_dump()
    assert dump3["x"] == 789
    assert dump3["command"] == "uv"
    assert dump3["args"] == ["run", "srv"]
    assert all(not k.startswith("_") for k in dump3)
