# chuk_mcp/protocol/messages/roots/__init__.py
"""Roots feature — Rust-backed via chuk_mcp_rs.

Kept as an import path for backward compatibility with code (and examples)
that import ``chuk_mcp.protocol.messages.roots``.
"""

from ..._rust import send_roots_list, send_roots_list_changed_notification

__all__ = ["send_roots_list", "send_roots_list_changed_notification"]
