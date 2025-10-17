# chuk_mcp/protocol/messages/__init__.py
"""
Messages module for the Model Context Protocol client.

This module provides the messaging layer for MCP communication, implementing
MCP features and protocol operations. The messaging layer handles JSON-RPC
message construction and protocol-specific operations.
"""

# Core infrastructure
from .json_rpc_message import JSONRPCMessage
from .send_message import send_message
from .message_method import MessageMethod

# Error types from the protocol types layer
from ..types.errors import (
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
)

# Initialization
from .initialize import (
    send_initialize,
    send_initialized_notification,
    InitializeResult,
)

# Core operations
from .tools import (
    send_tools_list,
    send_tools_call,
    Tool,
    ToolResult,
)

from .resources import (
    send_resources_list,
    send_resources_read,
    Resource,
    ResourceContent,
)

from .prompts import (
    send_prompts_list,
    send_prompts_get,
)

from .ping import (
    send_ping,
)

# Optional features (import with try/except for compatibility)
_optional_exports = []

try:
    from .sampling import (  # noqa: F401
        send_sampling_create_message,  # noqa: F401
        SamplingMessage,  # noqa: F401
        CreateMessageResult,  # noqa: F401
    )

    _optional_exports.extend(
        [
            "send_sampling_create_message",
            "SamplingMessage",
            "CreateMessageResult",
        ]
    )
except ImportError:
    pass

try:
    from .completions import (  # noqa: F401
        send_completion_complete,  # noqa: F401
        CompletionResult,  # noqa: F401
    )

    _optional_exports.extend(
        [
            "send_completion_complete",
            "CompletionResult",
        ]
    )
except ImportError:
    pass

try:
    from .roots import (  # noqa: F401
        send_roots_list,  # noqa: F401
        Root,  # noqa: F401
    )

    _optional_exports.extend(
        [
            "send_roots_list",
            "Root",
        ]
    )
except ImportError:
    pass

try:
    from .logging import (  # noqa: F401  # type: ignore
        send_logging_set_level,  # noqa: F401
    )

    _optional_exports.extend(
        [
            "send_logging_set_level",
        ]
    )
except ImportError:
    pass

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
] + _optional_exports
