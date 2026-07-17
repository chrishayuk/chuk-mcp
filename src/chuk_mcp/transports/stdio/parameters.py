# chuk_mcp/transports/stdio/parameters.py
"""Stdio transport parameters — Rust-backed via chuk_mcp_rs.

Kept as an import path for backward compatibility with downstream consumers
(e.g. chuk-tool-processor) that import
``chuk_mcp.transports.stdio.parameters.StdioParameters``.
"""

from ..._rust import StdioParameters

__all__ = ["StdioParameters"]
