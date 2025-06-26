# chuk_mcp/mcp_client/transport/__init__.py
"""
Transport module for the Model Context Protocol client.

This module provides various transport mechanisms for communicating with MCP servers.
Transports handle the low-level communication layer, abstracting the specifics of
how messages are sent and received between clients and servers. The MCP protocol
is transport-agnostic, allowing implementations to choose the most appropriate
communication method for their use case.

Available Transports:
- **Stdio**: Communication via standard input/output with subprocess servers
  - Best for: Cross-language servers, sandboxed processes, development
  - Protocol: Newline-delimited JSON-RPC over stdin/stdout pipes

Transport Selection Guidelines:
- Use **stdio** for most MCP servers, especially those in different languages
- Stdio transport provides excellent isolation and process management
- Future transports may include HTTP, WebSockets, named pipes, etc.

All transports provide:
- JSON-RPC 2.0 compliant message handling
- Proper error handling and recovery
- Graceful connection lifecycle management
- Performance-optimized message routing
- Support for both requests and notifications

Transport Interface:
Each transport provides streams compatible with the messaging layer:
- Read stream: For receiving responses and notifications
- Write stream: For sending requests and notifications

This abstraction allows the same messaging code to work across different
transport implementations.
"""

from .stdio import (
    StdioClient,
    stdio_client,
    StdioServerParameters,
    shutdown_stdio_server,
)

__all__ = [
    # Stdio transport
    "StdioClient",
    "stdio_client", 
    "StdioServerParameters",
    "shutdown_stdio_server",
]