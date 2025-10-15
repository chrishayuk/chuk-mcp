# chuk_mcp/mcp_client/host/__init__.py
"""
Host module for the Model Context Protocol client.

This module provides host-level functionality for managing MCP server connections
and runtime environment configuration. The host layer sits above the transport
and messaging layers, providing higher-level abstractions for working with
multiple MCP servers simultaneously.

Key features:
- Server lifecycle management and connection orchestration
- Multi-server connection handling with graceful cleanup
- Environment variable management for subprocess servers
- Configuration-driven server parameter loading
- Intelligent server routing and selection
- Interactive and batch command execution support
- Cross-platform environment variable inheritance

Host Responsibilities:
1. **Server Management**: Start, initialize, and cleanly shut down server connections
2. **Environment Setup**: Provide appropriate environment variables for server processes
3. **Connection Orchestration**: Manage multiple concurrent server connections
4. **Error Handling**: Graceful error recovery and connection cleanup
5. **Command Execution**: Run commands against one or more connected servers

The host layer enables applications to:
- Connect to multiple MCP servers simultaneously
- Route requests to appropriate servers based on capabilities
- Handle server failures gracefully without affecting other connections
- Provide consistent environment setup across different platforms
- Support both interactive and programmatic server interactions

Usage Patterns:
- Command-line tools that need to work with multiple servers
- Interactive applications requiring server management
- Batch processing systems with multiple data sources
- Development and testing environments
"""

# Import environment utilities directly (no circular dependency)
from .environment import (
    get_default_environment,
    DEFAULT_INHERITED_ENV_VARS,
)

# Note: server_manager is imported at the bottom to avoid circular imports
# This is a common pattern when modules have interdependencies

__all__ = [
    # Server management
    "run_command",
    # Environment configuration
    "get_default_environment",
    "DEFAULT_INHERITED_ENV_VARS",
]

# Import server_manager at the end to avoid circular imports
from .server_manager import (
    run_command,
)
