# chuk_mcp/protocol/messages/__init__.py
"""
Messages module for the Model Context Protocol — Rust-backed via chuk_mcp_rs.

The ``send_*`` protocol operations and the initialization handshake are
implemented in the Rust core and operate on the Rust stream handles returned by
``stdio_client``. The JSON-RPC data model (``JSONRPCMessage``) and the method
enumeration (``MessageMethod``) remain pure-Python value types.
"""

# Rust-backed operations and result types.
from ..._rust import (
    send_message,
    send_initialize,
    send_initialized_notification,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
    send_ping,
    InitializeResult,
    Tool,
    ToolResult,
    Resource,
    ResourceContent,
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
)

# Pure-Python data model layer.
from .json_rpc_message import JSONRPCMessage
from .message_method import MessageMethod

__all__ = [
    # Core infrastructure
    "JSONRPCMessage",
    "send_message",
    "MessageMethod",
    # Error handling
    "RetryableError",
    "NonRetryableError",
    "VersionMismatchError",
    # Initialization
    "send_initialize",
    "send_initialized_notification",
    "InitializeResult",
    # Core operations
    "send_tools_list",
    "send_tools_call",
    "Tool",
    "ToolResult",
    "send_resources_list",
    "send_resources_read",
    "Resource",
    "ResourceContent",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
]
