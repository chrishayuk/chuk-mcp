# chuk_mcp/protocol/__init__.py
"""
Protocol layer for the Model Context Protocol.

This module provides shared protocol components including message types,
data structures, and validation utilities.
"""

# Re-export key types for convenience
from .types import (
    ServerCapabilities,
    ClientCapabilities,
    ServerInfo,
    ClientInfo,
    # Legacy aliases
    MCPServerCapabilities,
    MCPClientCapabilities,
    MCPServerInfo,
    MCPClientInfo,
)

from .messages import (
    JSONRPCMessage,
    send_message,
    MessageMethod,
    RetryableError,
    NonRetryableError,
    # Initialization
    send_initialize,
    send_initialized_notification,
    InitializeResult,
    VersionMismatchError,
    # Core operations
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
    send_ping,
    # Data types
    Tool,
    ToolResult,
    Resource,
    ResourceContent,
)

__all__ = [
    # Types
    "ServerCapabilities",
    "ClientCapabilities",
    "ServerInfo",
    "ClientInfo",
    "MCPServerCapabilities",
    "MCPClientCapabilities",
    "MCPServerInfo",
    "MCPClientInfo",
    # Messages and operations
    "JSONRPCMessage",
    "send_message",
    "MessageMethod",
    "RetryableError",
    "NonRetryableError",
    "send_initialize",
    "send_initialized_notification",
    "InitializeResult",
    "VersionMismatchError",
    "send_tools_list",
    "send_tools_call",
    "send_resources_list",
    "send_resources_read",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
    "Tool",
    "ToolResult",
    "Resource",
    "ResourceContent",
]
