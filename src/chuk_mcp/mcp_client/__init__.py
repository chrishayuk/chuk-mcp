# chuk_mcp/mcp_client/__init__.py
"""
Model Context Protocol (MCP) Client Library

This is a comprehensive Python client implementation for the Model Context Protocol,
providing a complete toolkit for building applications that communicate with MCP
servers. The library is designed to be both powerful for advanced use cases and
simple for basic integrations.

Architecture Overview:
The client library is organized into several layers, each providing different
levels of abstraction:

┌─────────────────────────────────────────────────────────────────┐
│ Host Layer (host/)                                              │
│ • Multi-server management and orchestration                     │
│ • Environment configuration and lifecycle management            │
│ • High-level command execution and error handling               │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Protocol Layer (../protocol/)                                   │
│ • Shared protocol components (types, messages, versioning)      │
│ • MCP feature implementations (sampling, completion, etc.)      │
│ • JSON-RPC message construction and parsing                     │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Transport Layer (transport/)                                    │
│ • Low-level communication mechanisms (stdio, future: HTTP, WS)  │
│ • Connection management and message routing                     │
│ • Process lifecycle and cleanup                                 │
└─────────────────────────────────────────────────────────────────┘

Key Features:
• **Complete MCP Protocol Support**: All standard MCP features including tools,
  resources, prompts, sampling, completion, and roots
• **Multiple Transport Options**: Currently supports stdio, designed for extensibility
• **Robust Error Handling**: Comprehensive error handling with retries and graceful fallback
• **High Performance**: Optimized message routing and minimal overhead
• **Type Safety**: Full type annotations with Pydantic integration (or fallback)
• **Multi-Server Support**: Connect to and manage multiple MCP servers simultaneously
• **Cross-Platform**: Works on Windows, macOS, and Linux with appropriate environment handling

Quick Start:
```python
from chuk_mcp.mcp_client import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages.tools import send_tools_list

# Connect to an MCP server
server_params = StdioServerParameters(command="python", args=["my_server.py"])
async with stdio_client(server_params) as (read_stream, write_stream):
    # List available tools
    response = await send_tools_list(read_stream, write_stream)
    print(f"Available tools: {response['tools']}")
```

Dependency Management:
The library includes a fallback implementation for core functionality when Pydantic
is not available, making it suitable for environments with minimal dependencies.
Use `MCP_FORCE_FALLBACK=1` to test fallback behavior even when Pydantic is installed.
"""

# Core base class and utilities from protocol layer
from ..protocol.mcp_pydantic_base import (
    McpPydanticBase,
    Field,
    ValidationError,
    PYDANTIC_AVAILABLE,
)

# Transport layer - stdio is the primary transport
from .transport import (
    StdioClient,
    stdio_client,
    StdioServerParameters,
    shutdown_stdio_server,
)

# Host layer - high-level management
from .host import (
    run_command,
    get_default_environment,
    DEFAULT_INHERITED_ENV_VARS,
)

# Core messaging infrastructure from protocol layer
from ..protocol.messages import (
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
    
    # Common operations
    send_tools_list,
    send_tools_call,
    Tool,
    ToolResult,
    send_resources_list,
    send_resources_read,
    Resource,
    ResourceContent,
    send_prompts_list,
    send_prompts_get,
    send_ping,
)

# Import capabilities and info types from protocol layer
from ..protocol.types import (
    ClientCapabilities,
    ServerCapabilities,
    ClientInfo,
    ServerInfo,
    
    # Legacy aliases for backward compatibility
    MCPClientCapabilities,
    MCPServerCapabilities,
    MCPClientInfo,
    MCPServerInfo,
)

__version__ = "0.3.0"

__all__ = [
    # Version info
    "__version__",
    
    # Core infrastructure
    "McpPydanticBase",
    "Field", 
    "ValidationError",
    "PYDANTIC_AVAILABLE",
    
    # Transport layer
    "StdioClient",
    "stdio_client",
    "StdioServerParameters", 
    "shutdown_stdio_server",
    
    # Host layer
    "run_command",
    "get_default_environment",
    "DEFAULT_INHERITED_ENV_VARS",
    
    # Core messaging
    "JSONRPCMessage",
    "send_message",
    "MessageMethod",
    "RetryableError",
    "NonRetryableError",
    
    # Initialization
    "send_initialize",
    "send_initialized_notification", 
    "InitializeResult",
    "VersionMismatchError",
    
    # Capabilities and info types
    "ClientCapabilities",
    "ServerCapabilities",
    "ClientInfo",
    "ServerInfo",
    "MCPClientCapabilities",  # Legacy alias
    "MCPServerCapabilities",  # Legacy alias
    "MCPClientInfo",         # Legacy alias
    "MCPServerInfo",         # Legacy alias
    
    # Common operations - tools
    "send_tools_list",
    "send_tools_call",
    "Tool",
    "ToolResult",
    
    # Common operations - resources  
    "send_resources_list",
    "send_resources_read",
    "Resource",
    "ResourceContent",
    
    # Common operations - prompts
    "send_prompts_list", 
    "send_prompts_get",
    
    # Utilities
    "send_ping",
]