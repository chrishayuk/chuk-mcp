# chuk_mcp/mcp_client/messages/__init__.py
"""
Messages module for the Model Context Protocol client.

This module provides the messaging layer for MCP communication, implementing
MCP features and protocol operations. The messaging layer handles JSON-RPC
message construction and protocol-specific operations.
"""

# Start with just the modules we know exist from your code examples
# Core infrastructure - only import if they exist
_exports = []

# Try to import core infrastructure
try:
    from .json_rpc_message import JSONRPCMessage
    _exports.extend(["JSONRPCMessage"])
except ImportError:
    pass

try:
    from .send_message import send_message
    _exports.extend(["send_message"])
except ImportError:
    pass

try:
    from .message_method import MessageMethod
    _exports.extend(["MessageMethod"])
except ImportError:
    pass

try:
    from .exceptions import RetryableError, NonRetryableError
    _exports.extend(["RetryableError", "NonRetryableError"])
except ImportError:
    pass

# Feature modules that we know exist
try:
    from .initialize import (
        send_initialize,
        send_initialized_notification,
        InitializeResult,
        MCPClientCapabilities,
        MCPServerCapabilities,
        VersionMismatchError,
    )
    _exports.extend([
        "send_initialize",
        "send_initialized_notification", 
        "InitializeResult",
        "MCPClientCapabilities",
        "MCPServerCapabilities",
        "VersionMismatchError",
    ])
except ImportError:
    pass

try:
    from .tools import (
        send_tools_list,
        send_tools_call,
        Tool,
        ToolResult,
    )
    _exports.extend([
        "send_tools_list",
        "send_tools_call",
        "Tool",
        "ToolResult",
    ])
except ImportError:
    pass

try:
    from .resources import (
        send_resources_list,
        send_resources_read,
        Resource,
        ResourceContent,
    )
    _exports.extend([
        "send_resources_list",
        "send_resources_read",
        "Resource", 
        "ResourceContent",
    ])
except ImportError:
    pass

try:
    from .prompts import (
        send_prompts_list,
        send_prompts_get,
    )
    _exports.extend([
        "send_prompts_list",
        "send_prompts_get",
    ])
except ImportError:
    pass

try:
    from .ping import send_ping
    _exports.extend(["send_ping"])
except ImportError:
    pass

# Other feature modules
try:
    from .sampling import (
        send_sampling_create_message,
        SamplingMessage,
        CreateMessageResult,
    )
    _exports.extend([
        "send_sampling_create_message",
        "SamplingMessage", 
        "CreateMessageResult",
    ])
except ImportError:
    pass

try:
    from .completion import (
        send_completion_complete,
        CompletionResult,
    )
    _exports.extend([
        "send_completion_complete",
        "CompletionResult",
    ])
except ImportError:
    pass

try:
    from .roots import (
        send_roots_list,
        Root,
    )
    _exports.extend([
        "send_roots_list",
        "Root",
    ])
except ImportError:
    pass

# Only export what was successfully imported
__all__ = _exports