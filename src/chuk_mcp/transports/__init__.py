# chuk_mcp/transports/__init__.py
"""
MCP transport implementations for chuk_mcp.
"""

from .base import Transport, TransportParameters

# Import stdio transport (always available)
from .stdio import StdioTransport, StdioParameters, stdio_client

# Import HTTP and SSE transports (may not be available if dependencies missing)
try:
    from .http import HTTPTransport, HTTPParameters, http_client  # type: ignore[attr-defined]

    HAS_HTTP = True
except ImportError:
    HTTPTransport = None  # type: ignore[assignment, misc]
    HTTPParameters = None  # type: ignore[assignment, misc]
    http_client = None  # type: ignore[assignment]
    HAS_HTTP = False

try:
    from .sse import SSETransport, SSEParameters, sse_client

    HAS_SSE = True
except ImportError:
    SSETransport = None  # type: ignore[assignment, misc]
    SSEParameters = None  # type: ignore[assignment, misc]
    sse_client = None  # type: ignore[assignment]
    HAS_SSE = False

__all__ = [
    # Base classes
    "Transport",
    "TransportParameters",
    # stdio transport (always available)
    "StdioTransport",
    "StdioParameters",
    "stdio_client",
    # HTTP transport (optional)
    "HTTPTransport",
    "HTTPParameters",
    "http_client",
    "HAS_HTTP",
    # SSE transport (optional)
    "SSETransport",
    "SSEParameters",
    "sse_client",
    "HAS_SSE",
]


def get_available_transports():
    """Get list of available transport types."""
    available = ["stdio"]  # Always available

    if HAS_HTTP:
        available.append("http")

    if HAS_SSE:
        available.append("sse")

    return available


def create_transport(transport_type: str, parameters) -> Transport:
    """
    Factory function to create transport instances.

    Args:
        transport_type: Type of transport ("stdio", "http", "sse")
        parameters: Transport parameters object

    Returns:
        Transport instance

    Raises:
        ValueError: If transport type is not supported or available
    """
    if transport_type == "stdio":
        return StdioTransport(parameters)
    elif transport_type == "http":
        if not HAS_HTTP:
            raise ValueError("HTTP transport not available - install httpx dependency")
        return HTTPTransport(parameters)
    elif transport_type == "sse":
        if not HAS_SSE:
            raise ValueError("SSE transport not available - install httpx dependency")
        return SSETransport(parameters)
    else:
        available = get_available_transports()
        raise ValueError(
            f"Unknown transport type: {transport_type}. Available: {available}"
        )


def create_client(transport_type: str, parameters):
    """
    Factory function to create client context managers.

    Args:
        transport_type: Type of transport ("stdio", "http", "sse")
        parameters: Transport parameters object

    Returns:a
        Client context manager that yields (read_stream, write_stream)

    Raises:
        ValueError: If transport type is not supported or available
    """
    if transport_type == "stdio":
        return stdio_client(parameters)
    elif transport_type == "http":
        if not HAS_HTTP:
            raise ValueError("HTTP transport not available - install httpx dependency")
        return http_client(parameters)
    elif transport_type == "sse":
        if not HAS_SSE:
            raise ValueError("SSE transport not available - install httpx dependency")
        return sse_client(parameters)
    else:
        available = get_available_transports()
        raise ValueError(
            f"Unknown transport type: {transport_type}. Available: {available}"
        )
