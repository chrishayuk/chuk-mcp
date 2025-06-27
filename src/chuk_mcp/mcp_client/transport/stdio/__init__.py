# chuk_mcp/mcp_client/transport/stdio/__init__.py
"""
Stdio transport module for the Model Context Protocol client.

This module provides standard input/output (stdio) transport functionality for
communicating with MCP servers that run as separate processes. The stdio transport
is one of the most common ways to connect to MCP servers, especially those written
in different programming languages or those that need to run with specific
environments or permissions.

Key features:
- Subprocess-based server communication via stdin/stdout
- Newline-delimited JSON-RPC message handling
- Batch message support (per JSON-RPC 2.0 specification)
- Graceful server startup and shutdown
- Process lifecycle management with proper cleanup
- Environment variable support for server configuration
- Performance-optimized message routing
- Comprehensive error handling and logging

Transport Flow:
1. Start server subprocess with specified command and arguments
2. Establish bidirectional communication via stdin/stdout pipes
3. Send JSON-RPC messages as newline-delimited JSON
4. Route incoming responses and notifications to appropriate streams
5. Handle graceful shutdown with proper process termination

The stdio transport is ideal for:
- Language-agnostic MCP server implementations
- Servers requiring specific runtime environments
- Sandboxed or containerized server processes
- Development and testing scenarios
"""

from .stdio_client import (
    StdioClient,
    stdio_client,
    stdio_client_with_initialize,
)

from .stdio_server_parameters import (
    StdioServerParameters,
)

from .stdio_server_shutdown import (
    shutdown_stdio_server,
)

__all__ = [
    # Main client class and context manager
    "StdioClient",
    "stdio_client",
    "stdio_client_with_initialize",
    
    # Configuration
    "StdioServerParameters",
    
    # Lifecycle management
    "shutdown_stdio_server",
]