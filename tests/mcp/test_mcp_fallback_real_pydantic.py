# test_mcp_fallback_real_pydantic.py
import os
import sys
import importlib

import pytest


@pytest.mark.skipif(
    os.environ.get("MCP_FORCE_FALLBACK") == "1",
    reason="Fallback forced via env-var; real-Pydantic path intentionally skipped.",
)
def test_mcp_pydantic_base_real_pydantic():
    """Ensure *McpPydanticBase* uses the real Pydantic implementation when available."""

    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 1. Import check
    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    try:
        import pydantic  # noqa: WPS433 - runtime import for version detection
    except ImportError:
        pytest.skip("Pydantic not installed - cannot exercise real‐Pydantic branch.")

    # Clear cached *mcp_pydantic_base* in case earlier tests forced fallback.
    sys.modules.pop("chuk_mcp.protocol.mcp_pydantic_base", None)
    mpb = importlib.import_module("chuk_mcp.protocol.mcp_pydantic_base")

    McpPydanticBase, Field, ConfigDict = (
        mpb.McpPydanticBase,
        mpb.Field,
        mpb.ConfigDict,
    )

    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 2. Sanity-check hierarchy
    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    assert issubclass(
        McpPydanticBase, pydantic.BaseModel
    ), "McpPydanticBase should alias pydantic.BaseModel when Pydantic is present."

    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 3. Define a tiny model compatible with both Pydantic v1 + v2 APIs
    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    if pydantic.version.VERSION.startswith("1."):

        class RealModel(McpPydanticBase):
            x: int = Field(default=123)

            class Config:  # noqa: D401 - Pydantic v1 config style
                extra = "forbid"

    else:  # v2

        class RealModel(McpPydanticBase):
            x: int = Field(default=123)
            model_config = ConfigDict(extra="forbid")

    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 4. Behaviour checks
    # ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    inst = RealModel()

    # v2 has .model_dump(); v1 has .dict()
    data = inst.model_dump() if hasattr(inst, "model_dump") else inst.dict()
    assert data == {"x": 123}

    inst2 = RealModel.model_validate({"x": 456})
    assert inst2.x == 456