"""
Chuk MCP — A Comprehensive Model Context Protocol Implementation.

As of the Rust-backed release, the behavioural core of chuk-mcp (transports, the
high- and low-level client, the server, and every ``send_*`` protocol operation)
is implemented in Rust in the companion ``chuk-mcp-rs`` project and exposed here
through its ``chuk_mcp_rs`` extension. The pure-data model layer
(``JSONRPCMessage``, ``MessageMethod``, capability/info models) remains in
Python. All public import paths are preserved.

Quick start:

```python
from chuk_mcp import connect_to_server, StdioParameters

params = StdioParameters(command="python", args=["server.py"])
async with await connect_to_server(params) as client:
    tools = await client.list_tools()
    result = await client.call_tool("hello", {"name": "World"})
```

Legacy low-level API (still supported):

```python
from chuk_mcp import stdio_client, StdioServerParameters, send_tools_list

params = StdioServerParameters(command="python", args=["server.py"])
async with stdio_client(params) as (read, write):
    from chuk_mcp import send_initialize
    await send_initialize(read, write)
    tools = await send_tools_list(read, write)
```
"""

# ---------------------------------------------------------------------------
# Behavioural API — Rust-backed via chuk_mcp_rs
# ---------------------------------------------------------------------------
from ._rust import (
    # Transports / parameters
    StdioParameters,
    StdioServerParameters,
    stdio_client,
    # High-level client / server
    MCPClient,
    connect_to_server,
    MCPServer,
    # Low-level message operations
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
    # Result / data types
    Tool,
    ToolResult,
    Resource,
    ResourceContent,
    InitializeResult,
    # Errors
    McpError,
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
    ValidationError,
    # Environment / versions
    get_default_environment,
    supported_versions,
    CURRENT_VERSION,
    LATEST_LEGACY_VERSION,
    core_version,
)

# ---------------------------------------------------------------------------
# Pure-Python data-model layer
# ---------------------------------------------------------------------------
from .protocol.types import (
    ServerInfo,
    ClientInfo,
    ServerCapabilities,
    ClientCapabilities,
    # Legacy aliases
    MCPServerInfo,
    MCPClientInfo,
    MCPServerCapabilities,
    MCPClientCapabilities,
)
from .protocol.messages.json_rpc_message import JSONRPCMessage
from .protocol.messages.message_method import MessageMethod

try:
    from .protocol.mcp_pydantic_base import PYDANTIC_AVAILABLE
except ImportError:  # pragma: no cover
    PYDANTIC_AVAILABLE = False

# Configuration utilities (legacy, pure-Python).
try:
    from .config import load_config
except ImportError:  # pragma: no cover

    def load_config(*args, **kwargs):  # type: ignore[misc]
        raise NotImplementedError("load_config not available in this build")


# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------
__title__ = "chuk-mcp"
__description__ = "A comprehensive Model Context Protocol implementation (Rust-backed)"
__license__ = "Apache-2.0"
__version__ = "0.10.0"

__all__ = [
    # Transports
    "stdio_client",
    "StdioParameters",
    "StdioServerParameters",
    # High-level client / server
    "MCPClient",
    "connect_to_server",
    "MCPServer",
    # Low-level protocol operations
    "send_message",
    "send_initialize",
    "send_initialized_notification",
    "send_tools_list",
    "send_tools_call",
    "send_resources_list",
    "send_resources_read",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
    # Data / result types
    "JSONRPCMessage",
    "MessageMethod",
    "Tool",
    "ToolResult",
    "Resource",
    "ResourceContent",
    "InitializeResult",
    "ServerInfo",
    "ClientInfo",
    "ServerCapabilities",
    "ClientCapabilities",
    "MCPServerInfo",
    "MCPClientInfo",
    "MCPServerCapabilities",
    "MCPClientCapabilities",
    # Errors
    "McpError",
    "RetryableError",
    "NonRetryableError",
    "VersionMismatchError",
    "ValidationError",
    # Utilities
    "get_default_environment",
    "load_config",
    "supported_versions",
    "core_version",
    "CURRENT_VERSION",
    "LATEST_LEGACY_VERSION",
    "PYDANTIC_AVAILABLE",
    # Metadata
    "__version__",
    "__title__",
    "__description__",
    "__license__",
]
