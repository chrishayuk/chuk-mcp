# chuk_mcp/transports/sse/sse_client.py
"""
SSE client context manager similar to stdio_client.

⚠️ DEPRECATION NOTICE: SSE transport is deprecated as of MCP spec 2025-03-26.
This client maintains backwards compatibility for existing SSE-based MCP servers.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional, Tuple, AsyncGenerator

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .transport import SSETransport
from .parameters import SSEParameters

logger = logging.getLogger(__name__)

__all__ = ["sse_client"]


@asynccontextmanager
async def sse_client(
    parameters: SSEParameters,
) -> AsyncGenerator[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream], None]:
    """
    Create an SSE client and return streams that work with send_message.

    ⚠️ DEPRECATION NOTICE: SSE transport is deprecated as of MCP spec 2025-03-26.
    This function maintains backwards compatibility for existing deployments.

    Usage:
        async with sse_client(sse_params) as (read_stream, write_stream):
            response = await send_message(read_stream, write_stream, "ping")

    Args:
        parameters: SSE transport parameters

    Returns:
        Tuple of (read_stream, write_stream) for JSON-RPC communication

    Raises:
        RuntimeError: If SSE connection cannot be established
        TimeoutError: If connection setup times out
        Exception: For other connection failures
    """
    if logger.isEnabledFor(logging.INFO):
        logger.info(f"🌊 Creating SSE client connection to {parameters.url}")

    transport = SSETransport(parameters)

    try:
        async with transport:
            streams = await transport.get_streams()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("✅ SSE client streams ready")
            yield streams
    except Exception as e:
        logger.error(f"❌ SSE client error: {e}")
        # Let exceptions propagate - caller should handle them
        raise


# Enhanced utility functions for SSE transport backwards compatibility
def create_sse_parameters_from_url(
    url: str, bearer_token: Optional[str] = None, timeout: float = 60.0, **kwargs
) -> SSEParameters:
    """
    Convenience function to create SSE parameters from a URL.

    Args:
        url: SSE server URL
        bearer_token: Optional authentication token
        timeout: Connection timeout in seconds
        **kwargs: Additional parameters

    Returns:
        Configured SSEParameters instance
    """
    return SSEParameters(url=url, bearer_token=bearer_token, timeout=timeout, **kwargs)


def is_sse_url(url: str) -> bool:
    """
    Check if a URL appears to be an SSE endpoint.

    This is a heuristic check for backwards compatibility.

    Args:
        url: URL to check

    Returns:
        True if URL appears to be SSE-compatible
    """
    if not url:
        return False

    url_lower = url.lower()

    # Common SSE endpoint patterns
    sse_indicators = [
        "/sse",
        "events",
        "stream",
        ":8080",  # Common SSE port
        ":3000",  # Common dev port
    ]

    return any(indicator in url_lower for indicator in sse_indicators)


# Migration helper for transitioning from SSE to Streamable HTTP
async def try_sse_with_fallback(
    url: str, bearer_token: Optional[str] = None, timeout: float = 30.0, **kwargs
):
    """
    Attempt SSE connection with helpful error messages for migration.

    This function helps users transition from SSE to newer transports
    by providing clear migration guidance when SSE fails.

    Args:
        url: Server URL
        bearer_token: Optional authentication
        timeout: Connection timeout
        **kwargs: Additional SSE parameters

    Returns:
        SSE client context manager

    Raises:
        Exception: With migration guidance if SSE is not supported
    """
    try:
        params = SSEParameters(
            url=url, bearer_token=bearer_token, timeout=timeout, **kwargs
        )
        return sse_client(params)

    except Exception as e:
        error_msg = str(e).lower()

        # Provide migration guidance for common errors
        if "not found" in error_msg or "404" in error_msg:
            raise Exception(
                f"SSE endpoint not found at {url}. "
                "This server may have migrated to Streamable HTTP transport. "
                "Try using the Streamable HTTP transport instead of SSE."
            ) from e

        elif "method not allowed" in error_msg or "405" in error_msg:
            raise Exception(
                f"SSE transport not supported by server at {url}. "
                "The server may only support Streamable HTTP transport. "
                "Consider updating your client to use the new transport method."
            ) from e

        else:
            # Re-raise with original error for other cases
            raise
