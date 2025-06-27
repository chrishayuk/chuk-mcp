# chuk_mcp/__init__.py
"""
Chuk MCP - A Comprehensive Model Context Protocol Implementation

This package provides a complete, production-ready implementation of the Model Context
Protocol (MCP), designed for building intelligent applications that can communicate
with external tools and data sources through a standardized interface.

What is MCP?
The Model Context Protocol enables LLM applications to securely connect to external
tools, databases, APIs, and other resources. It provides a standardized way for
language models to access real-time information and perform actions in the world,
while maintaining security and user control.

Package Components:

🚀 **MCP Client Library** (`mcp_client/`)
A full-featured Python client for connecting to and communicating with MCP servers:
- Complete protocol implementation with all standard features
- Multiple transport support (stdio, future: HTTP, WebSockets)  
- Type-safe message handling with comprehensive error recovery
- Multi-server connection management and orchestration
- Cross-platform compatibility with optimized performance

⚙️ **Configuration Management** (`config.py`)
Flexible configuration system for managing server connections:
- JSON-based server configuration with environment support
- Multiple server profile management
- Runtime parameter validation and error handling

🎯 **Command Line Interface** (`__main__.py`)
Ready-to-use CLI for testing and development:
- Quick server connectivity testing
- Interactive protocol exploration
- Development and debugging utilities

Key Features:
✅ **Complete MCP Protocol Support**: Tools, resources, prompts, sampling, completion
✅ **Production Ready**: Robust error handling, logging, and connection management  
✅ **Type Safe**: Full type annotations with Pydantic integration
✅ **Multi-Server**: Connect to multiple servers simultaneously
✅ **Cross-Platform**: Windows, macOS, Linux support
✅ **Dependency Flexible**: Graceful fallback when optional dependencies unavailable

Quick Start:
```python
import chuk_mcp

# Using the high-level client
from chuk_mcp.mcp_client import stdio_client, StdioServerParameters

# Configure and connect to a server
server_params = StdioServerParameters(command="python", args=["my_server.py"])
async with stdio_client(server_params) as (read_stream, write_stream):
    # Use any MCP feature
    from chuk_mcp.mcp_client.messages.tools import send_tools_list
    tools = await send_tools_list(read_stream, write_stream)
    print(f"Available tools: {tools}")
```

Command Line Usage:
```bash
# Test server connectivity
python -m chuk_mcp

# Interactive exploration (if implemented)
python -m chuk_mcp --interactive --server my_server
```

For detailed documentation and examples, see the individual module documentation.
"""

# Re-export the most commonly used functionality from mcp_client
from .mcp_client import (
    # Core client functionality
    stdio_client,
    StdioClient,
    StdioServerParameters,
    
    # Common message operations
    send_initialize,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
    send_ping,
    
    # Core infrastructure
    JSONRPCMessage,
    send_message,
    MessageMethod,
    
    # Host-level functionality
    run_command,
    get_default_environment,
    
    # Common data types
    Tool,
    ToolResult,
    Resource,
    ResourceContent,
    InitializeResult,
    MCPClientCapabilities,
    MCPServerCapabilities,
    
    # Error handling
    VersionMismatchError,
    RetryableError,
    NonRetryableError,
    ValidationError,
    
    # Version and feature info
    __version__,
    PYDANTIC_AVAILABLE,
)

# Configuration utilities
from .config import (
    load_config,
)

# Package metadata
__title__ = "chuk-mcp"
__description__ = "A comprehensive Model Context Protocol implementation"
__author__ = "Your Name"  # Update with your actual name
__license__ = "MIT"  # Update with your actual license

# Expose everything commonly needed
__all__ = [
    # Client functionality
    "stdio_client",
    "StdioClient", 
    "StdioServerParameters",
    
    # Message operations
    "send_initialize",
    "send_tools_list",
    "send_tools_call",
    "send_resources_list", 
    "send_resources_read",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
    
    # Core infrastructure
    "JSONRPCMessage",
    "send_message",
    "MessageMethod",
    
    # Host functionality
    "run_command",
    "get_default_environment",
    
    # Data types
    "Tool",
    "ToolResult",
    "Resource", 
    "ResourceContent",
    "InitializeResult",
    "MCPClientCapabilities",
    "MCPServerCapabilities",
    
    # Error handling
    "VersionMismatchError",
    "RetryableError",
    "NonRetryableError", 
    "ValidationError",
    
    # Configuration
    "load_config",
    
    # Package info
    "__version__",
    "__title__",
    "__description__",
    "__author__",
    "__license__",
    "PYDANTIC_AVAILABLE",
]