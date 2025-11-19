# Configuration utilities (legacy)
try:
    from .config import load_config
except ImportError:

    def load_config(*args, **kwargs):  # type: ignore[misc]
        raise NotImplementedError(
            "load_config not available in this version"
        )  # chuk_mcp/__init__.py


"""
Chuk MCP - A Comprehensive Model Context Protocol Implementation

This package provides both client and server implementations of the MCP protocol,
with support for multiple transports and a clean, easy-to-use API.

What is MCP?
The Model Context Protocol enables LLM applications to securely connect to external
tools, databases, APIs, and other resources. It provides a standardized way for
language models to access real-time information and perform actions in the world,
while maintaining security and user control.

Package Architecture:

🔧 **Client Module** (`client/`)
High-level client for connecting to MCP servers:
- Clean API with automatic initialization
- Multi-transport support (stdio, http, sse)
- Type-safe operations and error handling

🖥️ **Server Module** (`server/`)  
Server-side implementation for building MCP servers:
- Protocol handler with session management
- Tool and resource registration
- Transport-agnostic design

🚀 **Transport Layer** (`transports/`)
Pluggable transport implementations:
- stdio: Standard input/output with subprocess
- http: HTTP-based communication (future)
- sse: Server-Sent Events streaming (future)

⚙️ **Protocol Layer** (`protocol/`)
Shared protocol components:
- Message definitions and JSON-RPC handling
- Type definitions and capabilities
- Version negotiation and error handling

Quick Start Examples:

```python
# New high-level client API
from chuk_mcp import MCPClient, connect_to_server, StdioParameters

# Simple connection
params = StdioParameters(command="python", args=["server.py"])
async with connect_to_server(params) as client:
    tools = await client.list_tools()
    result = await client.call_tool("hello", {"name": "World"})

# Server implementation
from chuk_mcp import MCPServer

server = MCPServer("My Server")

@server.register_tool("greet", {"name": {"type": "string"}})
async def greet(name: str) -> str:
    return f"Hello, {name}!"
```

Legacy Usage (Still Supported):
```python
# Old API still works
from chuk_mcp import stdio_client, StdioServerParameters

server_params = StdioServerParameters(command="python", args=["server.py"])
async with stdio_client(server_params) as (read_stream, write_stream):
    from chuk_mcp import send_tools_list
    tools = await send_tools_list(read_stream, write_stream)
```
"""

# ============================================================================
# New Clean API (Recommended) - with fallback handling
# ============================================================================

# Client exports - graceful fallback if new structure isn't ready
try:
    from .client import (
        MCPClient,
        connect_to_server,
    )

    _NEW_CLIENT_AVAILABLE = True
except ImportError:
    # Fallback: create basic implementations using legacy code
    _NEW_CLIENT_AVAILABLE = False

    # We'll define these after legacy imports
    MCPClient = None  # type: ignore[assignment, misc]
    connect_to_server = None  # type: ignore[assignment, misc]

# Server exports - graceful fallback if new structure isn't ready
try:
    from .server import (
        MCPServer,
        ProtocolHandler,
        SessionManager,
    )

    _NEW_SERVER_AVAILABLE = True
except ImportError:
    _NEW_SERVER_AVAILABLE = False
    MCPServer = None  # type: ignore[assignment, misc]
    ProtocolHandler = None  # type: ignore[assignment, misc]
    SessionManager = None  # type: ignore[assignment, misc]

# Transport exports - graceful fallback
try:
    from .transports import (
        stdio_client,
        StdioTransport,
        StdioParameters,
        Transport,
        TransportParameters,
    )

    _NEW_TRANSPORTS_AVAILABLE = True
except ImportError:
    _NEW_TRANSPORTS_AVAILABLE = False
    # Will be defined after legacy imports
    StdioTransport = None  # type: ignore[assignment, misc]
    Transport = None  # type: ignore[assignment, misc]
    TransportParameters = None  # type: ignore[assignment, misc]

# Protocol exports (for advanced usage) - with graceful fallback
try:
    from .protocol import (
        JSONRPCMessage,
        send_message,
        send_initialize,
        send_tools_list,
        send_tools_call,
        send_resources_list,
        send_resources_read,
        send_prompts_list,
        send_prompts_get,
        send_ping,
        ServerInfo,
        ClientInfo,
        ServerCapabilities,
        ClientCapabilities,
        MessageMethod,
        RetryableError,
        NonRetryableError,
        VersionMismatchError,
    )

    _PROTOCOL_AVAILABLE = True
except ImportError:
    _PROTOCOL_AVAILABLE = False
    # Will be imported from mcp_client compatibility layer

# Try to get ValidationError from protocol, fallback to mcp_pydantic_base
try:
    from .protocol.types.errors import ValidationError
except ImportError:
    try:
        from .protocol.mcp_pydantic_base import ValidationError  # type: ignore[assignment]
    except ImportError:
        # Create a minimal ValidationError for compatibility
        class ValidationError(ValueError):  # type: ignore[no-redef]
            pass

# ============================================================================
# Backward Compatibility Layer
# ============================================================================

# Legacy imports from old mcp_client structure - these should always work
from .mcp_client import (  # noqa: E402
    # Core client functionality (legacy)
    stdio_client as _legacy_stdio_client,
    StdioClient,  # noqa: F401
    StdioServerParameters,
    # Common data types (legacy)
    Tool,  # noqa: F401
    ToolResult,  # noqa: F401
    Resource,  # noqa: F401
    ResourceContent,  # noqa: F401
    InitializeResult,  # noqa: F401
    MCPClientCapabilities,  # noqa: F401
    MCPServerCapabilities,  # noqa: F401
    # Host-level functionality (legacy)
    run_command,  # noqa: F401
    get_default_environment,  # noqa: F401
    # Feature info
    PYDANTIC_AVAILABLE,  # noqa: F401
)

# Use legacy stdio_client if new transports not available
if not _NEW_TRANSPORTS_AVAILABLE:
    stdio_client = _legacy_stdio_client  # type: ignore[assignment, misc]
    StdioParameters = StdioServerParameters  # type: ignore[assignment, misc]  # Alias for consistency

# If protocol layer imports failed, import from mcp_client compatibility layer
if not _PROTOCOL_AVAILABLE:
    from .mcp_client import (  # noqa: F401  # type: ignore[assignment]
        JSONRPCMessage,  # noqa: F401
        send_message,  # noqa: F401
        send_initialize,  # noqa: F401
        send_tools_list,  # noqa: F401
        send_tools_call,  # noqa: F401
        send_resources_list,  # noqa: F401
        send_resources_read,  # noqa: F401
        send_prompts_list,  # noqa: F401
        send_prompts_get,  # noqa: F401
        send_ping,  # noqa: F401
        MessageMethod,  # noqa: F401
        RetryableError,  # noqa: F401
        NonRetryableError,  # noqa: F401
        VersionMismatchError,  # noqa: F401
    )

    # Import types from protocol if available
    try:
        from .protocol.types import (  # type: ignore[assignment]
            ServerInfo,
            ClientInfo,
            ServerCapabilities,
            ClientCapabilities,
        )
    except ImportError:
        # Create minimal type stubs
        class ServerInfo:  # type: ignore[no-redef]
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        class ClientInfo:  # type: ignore[no-redef]
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        class ServerCapabilities:  # type: ignore[no-redef]
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        class ClientCapabilities:  # type: ignore[no-redef]
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)


# Package metadata
__title__ = "chuk-mcp"
__description__ = "A comprehensive Model Context Protocol implementation"
__author__ = "Your Name"  # Update with your actual name
__license__ = "MIT"  # Update with your actual license

# ============================================================================
# Exports (New + Legacy for Backward Compatibility)
# ============================================================================

# ============================================================================
# Exports (New + Legacy for Backward Compatibility)
# ============================================================================

# Build __all__ dynamically based on what's available
_base_exports = [
    # Core always available
    "stdio_client",
    "StdioParameters",
    # Protocol (advanced)
    "JSONRPCMessage",
    "send_message",
    "send_initialize",
    "send_tools_list",
    "send_tools_call",
    "send_resources_list",
    "send_resources_read",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
    "ServerInfo",
    "ClientInfo",
    "ServerCapabilities",
    "ClientCapabilities",
    "MessageMethod",
    "RetryableError",
    "NonRetryableError",
    "VersionMismatchError",
    "ValidationError",
    # Legacy API (always available)
    "StdioClient",
    "StdioServerParameters",
    "Tool",
    "ToolResult",
    "Resource",
    "ResourceContent",
    "InitializeResult",
    "MCPClientCapabilities",
    "MCPServerCapabilities",
    "run_command",
    "get_default_environment",
    "load_config",
    # Package info
    "__version__",
    "__title__",
    "__description__",
    "__author__",
    "__license__",
    "PYDANTIC_AVAILABLE",
]

# Add new API exports if available
_new_exports = []
if _NEW_CLIENT_AVAILABLE:
    _new_exports.extend(["MCPClient", "connect_to_server"])
if _NEW_SERVER_AVAILABLE:
    _new_exports.extend(["MCPServer", "ProtocolHandler", "SessionManager"])
if _NEW_TRANSPORTS_AVAILABLE:
    _new_exports.extend(["StdioTransport", "Transport", "TransportParameters"])

__all__ = _base_exports + _new_exports

# ============================================================================
# Version Information
# ============================================================================

__version__ = "0.9"

# ============================================================================
# Deprecation Warnings for Guidance
# ============================================================================

import warnings  # noqa: E402
import os  # noqa: E402

# Only show deprecation warnings if explicitly enabled
if os.environ.get("CHUK_MCP_SHOW_DEPRECATIONS", "false").lower() == "true":

    def _deprecated_import_warning():
        warnings.warn(
            "Using legacy chuk_mcp imports. Consider migrating to the new API:\n"
            "  Old: from chuk_mcp import stdio_client, StdioServerParameters\n"
            "  New: from chuk_mcp import connect_to_server, StdioParameters\n"
            "Set CHUK_MCP_SHOW_DEPRECATIONS=false to disable these warnings.",
            DeprecationWarning,
            stacklevel=3,
        )

    # This will be called when legacy imports are used
    _deprecated_import_warning()
