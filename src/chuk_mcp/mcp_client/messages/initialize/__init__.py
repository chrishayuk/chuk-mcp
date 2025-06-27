# chuk_mcp/mcp_client/messages/initialize/__init__.py
"""
Initialize module for the Model Context Protocol client.

This module handles the critical initialization handshake between MCP clients 
and servers, implementing the complete MCP lifecycle protocol. The initialization
process establishes the communication channel, negotiates protocol versions,
and exchanges capability information between client and server.

MCP Initialization Flow:
1. Client sends 'initialize' request with proposed protocol version and capabilities
2. Server responds with accepted/counter-proposed version and its capabilities  
3. Client validates version compatibility (disconnects if unsupported)
4. Client sends 'notifications/initialized' to complete handshake
5. Normal MCP operations can begin

Key features:
- Protocol version negotiation with fallback support
- Capability exchange for both client and server
- Structured error handling for version mismatches
- Compliance with official MCP specification
- Support for experimental capabilities

Supported Protocol Versions:
- 2025-06-18 (current)
- 2025-03-26 (previous) 
- 2024-11-05 (legacy)
"""

from .send_messages import (
    # Main initialization functions
    send_initialize,
    send_initialized_notification,
    
    # Version management utilities
    get_supported_versions,
    get_current_version,
    is_version_supported,
    validate_version_format,
    SUPPORTED_PROTOCOL_VERSIONS,
    
    # Protocol data models
    InitializeParams,
    InitializeResult,
)

from .errors import (
    VersionMismatchError,
)

from .mcp_client_capabilities import (
    MCPClientCapabilities,
    RootsCapability,
    SamplingCapability,
    ElicitationCapability,
)

from .mcp_client_info import (
    MCPClientInfo,
)

from .mcp_server_capabilities import (
    MCPServerCapabilities,
    LoggingCapability,
    PromptsCapability,
    ResourcesCapability,
    ToolsCapability,
    CompletionCapability,
)

from .mcp_server_info import (
    MCPServerInfo,
)

__all__ = [
    # Core initialization functions
    "send_initialize",
    "send_initialized_notification",
    
    # Version management
    "get_supported_versions",
    "get_current_version", 
    "is_version_supported",
    "validate_version_format",
    "SUPPORTED_PROTOCOL_VERSIONS",
    
    # Protocol data models
    "InitializeParams",
    "InitializeResult",
    
    # Error handling
    "VersionMismatchError",
    
    # Client-side models
    "MCPClientCapabilities",
    "MCPClientInfo",
    "RootsCapability",
    "SamplingCapability", 
    "ElicitationCapability",
    
    # Server-side models
    "MCPServerCapabilities",
    "MCPServerInfo",
    "LoggingCapability",
    "PromptsCapability",
    "ResourcesCapability",
    "ToolsCapability",
    "CompletionCapability",
]