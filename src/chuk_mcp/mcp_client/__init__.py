# chuk_mcp/mcp_client/__init__.py
"""
Backward compatibility shim for the old mcp_client structure.

This module re-exports everything from the new locations while maintaining
the old API surface for backward compatibility.
"""

import warnings
import os
import sys
from types import ModuleType

# Only show deprecation warnings if explicitly enabled
if os.environ.get("CHUK_MCP_SHOW_DEPRECATIONS", "false").lower() == "true":
    warnings.warn(
        "chuk_mcp.mcp_client is deprecated. Use chuk_mcp.client or chuk_mcp.server instead.",
        DeprecationWarning,
        stacklevel=2,
    )

# Import from new transport location but maintain old API
# Updated to use the new transports structure
from ..transports.stdio import stdio_client
from ..transports.stdio.parameters import StdioParameters as StdioServerParameters
from ..transports.stdio.transport import StdioTransport as StdioClient


# Create compatibility functions for old API
async def stdio_client_with_initialize(
    server_params,
    timeout: float = 5.0,
    supported_versions=None,
    preferred_version=None,
):
    """Compatibility wrapper for stdio_client_with_initialize."""
    from ..protocol.messages.initialize import send_initialize

    async with stdio_client(server_params) as (read_stream, write_stream):
        # Perform initialization
        init_result = await send_initialize(read_stream, write_stream, timeout=timeout)
        if not init_result:
            raise Exception("Initialization failed")

        # Yield streams and init result (old API format)
        yield read_stream, write_stream, init_result


# Create compatibility for shutdown function
async def shutdown_stdio_server(
    read_stream=None, write_stream=None, process=None, timeout=5.0
):
    """Compatibility wrapper for shutdown_stdio_server."""
    # In the new architecture, shutdown is handled by the transport's __aexit__
    # This is just a no-op for compatibility
    pass


# Re-export from protocol layer
from ..protocol.messages import (  # noqa: E402
    send_initialize,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
    send_ping,
    JSONRPCMessage,
    send_message,
    MessageMethod,
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
)

# Import ValidationError with fallback
try:
    from ..protocol.types.errors import ValidationError
except ImportError:
    try:
        from ..protocol.mcp_pydantic_base import ValidationError  # type: ignore[assignment]
    except ImportError:

        class ValidationError(ValueError):  # type: ignore[no-redef]
            pass


from ..protocol.messages.tools import Tool, ToolResult  # noqa: E402
from ..protocol.messages.resources import Resource, ResourceContent  # noqa: E402
from ..protocol.messages.initialize import InitializeResult  # noqa: E402
from ..protocol.types import (  # noqa: E402
    MCPClientCapabilities,
    MCPServerCapabilities,
)

# Re-export from host layer (if it exists)
try:
    from .host.environment import get_default_environment
    from .host.server_manager import run_command
except ImportError:
    # Create minimal implementations
    def get_default_environment():  # type: ignore[misc]
        import os

        return dict(os.environ)

    def run_command(*args, **kwargs):  # type: ignore[misc]
        raise NotImplementedError("run_command not available in restructured version")


# Version info
try:
    from ..protocol.mcp_pydantic_base import PYDANTIC_AVAILABLE
except ImportError:
    PYDANTIC_AVAILABLE = True

__version__ = "0.4.0"

# Import the actual StdioClient (not the transport wrapper) for tests
from ..transports.stdio.stdio_client import (  # noqa: E402
    StdioClient as ActualStdioClient,
    _supports_batch_processing,
)


# Create fake transport module structure for backward compatibility
class FakeTransportModule(ModuleType):
    """Fake module to handle old import paths."""

    def __init__(self, name):
        super().__init__(name)

    def __getattr__(self, name):
        if name == "stdio":
            return FakeStdioModule("chuk_mcp.mcp_client.transport.stdio")
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")


class FakeStdioModule(ModuleType):
    """Fake stdio module to handle old import paths."""

    def __init__(self, name):
        super().__init__(name)
        # Add all the stdio exports - use actual StdioClient for tests
        self.stdio_client = stdio_client
        self.StdioClient = (
            ActualStdioClient  # Use the actual client, not the transport wrapper
        )
        self.stdio_client_with_initialize = stdio_client_with_initialize

    def __getattr__(self, name):
        if name == "stdio_client":
            return stdio_client
        elif name == "StdioClient":
            return ActualStdioClient  # Use the actual client
        elif name == "stdio_client_with_initialize":
            return stdio_client_with_initialize
        elif name == "stdio_server_parameters":
            return FakeStdioServerParametersModule(
                "chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters"
            )
        elif name == "stdio_server_shutdown":
            return FakeStdioServerShutdownModule(
                "chuk_mcp.mcp_client.transport.stdio.stdio_server_shutdown"
            )
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")


class FakeStdioClientModule(ModuleType):
    """Fake stdio_client module to handle direct imports."""

    def __init__(self, name):
        super().__init__(name)
        self.stdio_client = stdio_client
        self.StdioClient = ActualStdioClient
        self.stdio_client_with_initialize = stdio_client_with_initialize
        self._supports_batch_processing = _supports_batch_processing

    def __getattr__(self, name):
        if name == "stdio_client":
            return stdio_client
        elif name == "StdioClient":
            return ActualStdioClient
        elif name == "stdio_client_with_initialize":
            return stdio_client_with_initialize
        elif name == "_supports_batch_processing":
            return _supports_batch_processing
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")


class FakeStdioServerParametersModule(ModuleType):
    """Fake stdio_server_parameters module."""

    def __init__(self, name):
        super().__init__(name)
        self.StdioServerParameters = StdioServerParameters

    def __getattr__(self, name):
        if name == "StdioServerParameters":
            return StdioServerParameters
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")


class FakeStdioServerShutdownModule(ModuleType):
    """Fake stdio_server_shutdown module."""

    def __init__(self, name):
        super().__init__(name)
        self.shutdown_stdio_server = shutdown_stdio_server

    def __getattr__(self, name):
        if name == "shutdown_stdio_server":
            return shutdown_stdio_server
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")


# Inject fake modules into sys.modules for backward compatibility
transport_module = FakeTransportModule("chuk_mcp.mcp_client.transport")
stdio_module = FakeStdioModule("chuk_mcp.mcp_client.transport.stdio")
stdio_client_module = FakeStdioClientModule(
    "chuk_mcp.mcp_client.transport.stdio.stdio_client"
)
stdio_params_module = FakeStdioServerParametersModule(
    "chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters"
)
stdio_shutdown_module = FakeStdioServerShutdownModule(
    "chuk_mcp.mcp_client.transport.stdio.stdio_server_shutdown"
)

sys.modules["chuk_mcp.mcp_client.transport"] = transport_module
sys.modules["chuk_mcp.mcp_client.transport.stdio"] = stdio_module
sys.modules["chuk_mcp.mcp_client.transport.stdio.stdio_client"] = stdio_client_module
sys.modules["chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters"] = (
    stdio_params_module
)
sys.modules["chuk_mcp.mcp_client.transport.stdio.stdio_server_shutdown"] = (
    stdio_shutdown_module
)

__all__ = [
    # Core client functionality
    "stdio_client",
    "ActualStdioClient",  # Export the actual client for tests
    "StdioClient",  # Keep the transport alias
    "StdioServerParameters",
    "stdio_client_with_initialize",
    "shutdown_stdio_server",
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
    # Version info
    "__version__",
    "PYDANTIC_AVAILABLE",
]
