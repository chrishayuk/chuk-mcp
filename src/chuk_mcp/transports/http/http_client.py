# chuk_mcp/transports/http/http_client.py
"""
Streamable HTTP client context manager.

This implements the modern MCP transport (spec 2025-03-26) that replaces SSE.
"""

import logging
from contextlib import asynccontextmanager
from typing import Tuple, Optional, AsyncGenerator

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .transport import StreamableHTTPTransport
from .parameters import StreamableHTTPParameters

logger = logging.getLogger(__name__)

__all__ = ["http_client", "streamable_http_client", "create_http_parameters_from_url"]


@asynccontextmanager
async def http_client(
    parameters: StreamableHTTPParameters,
) -> AsyncGenerator[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream], None]:
    """
    Create a Streamable HTTP client and return streams that work with send_message.

    This implements the modern MCP transport specification (2025-03-26) that
    replaces the deprecated SSE transport.

    Usage:
        async with http_client(http_params) as (read_stream, write_stream):
            response = await send_message(read_stream, write_stream, "ping")

    Args:
        parameters: Streamable HTTP transport parameters

    Returns:
        Tuple of (read_stream, write_stream) for JSON-RPC communication

    Raises:
        RuntimeError: If HTTP connection cannot be established
        TimeoutError: If connection setup times out
        Exception: For other connection failures
    """
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            f"🌐 Creating Streamable HTTP client connection to {parameters.url}"
        )

    transport = StreamableHTTPTransport(parameters)

    try:
        async with transport:
            streams = await transport.get_streams()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("✅ HTTP client streams ready")
            yield streams
    except (RuntimeError, TimeoutError, ConnectionError, OSError) as e:
        # FIXED: Only catch specific transport-related errors
        # Don't catch AssertionError, ValueError, or other test-related exceptions
        logger.error(f"❌ HTTP client error: {e}")
        raise
    # Let all other exceptions (including test assertions) bubble up naturally


# Alias for consistency with other transports
streamable_http_client = http_client


def create_http_parameters_from_url(
    url: str,
    bearer_token: Optional[str] = None,
    timeout: float = 60.0,
    enable_streaming: bool = True,
    **kwargs,
) -> StreamableHTTPParameters:
    """
    Convenience function to create HTTP parameters from a URL.

    Args:
        url: MCP server URL (should point to the /mcp endpoint)
        bearer_token: Optional authentication token
        timeout: Connection timeout in seconds
        enable_streaming: Whether to accept SSE streaming responses
        **kwargs: Additional parameters

    Returns:
        Configured StreamableHTTPParameters instance
    """
    return StreamableHTTPParameters(
        url=url,
        bearer_token=bearer_token,
        timeout=timeout,
        enable_streaming=enable_streaming,
        **kwargs,
    )


def is_streamable_http_url(url: str) -> bool:
    """
    Check if a URL appears to be a Streamable HTTP endpoint.

    Args:
        url: URL to check

    Returns:
        True if URL appears to be Streamable HTTP-compatible
    """
    if not url:
        return False

    url_lower = url.lower()

    # Common Streamable HTTP patterns
    http_indicators = [
        "/mcp",
        "/api/mcp",
        "/v1/mcp",
        "mcp.",  # subdomain
    ]

    # Avoid SSE-specific patterns
    sse_patterns = ["/sse", "/events", "/stream"]

    has_http_indicator = any(indicator in url_lower for indicator in http_indicators)
    has_sse_pattern = any(pattern in url_lower for pattern in sse_patterns)

    return has_http_indicator and not has_sse_pattern


async def detect_transport_type(
    url: str, bearer_token: Optional[str] = None, timeout: float = 10.0
) -> str:
    """
    Detect what type of MCP transport a server supports.

    This function attempts to determine if a server supports:
    - Streamable HTTP (modern)
    - SSE (deprecated)
    - Both

    Args:
        url: Server URL to test
        bearer_token: Optional authentication
        timeout: Test timeout

    Returns:
        One of: "streamable_http", "sse", "both", "unknown"
    """
    import httpx

    try:
        headers = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            # Test 1: Try Streamable HTTP with a simple test request
            streamable_http_works = False
            try:
                test_message = {
                    "jsonrpc": "2.0",
                    "id": "transport-detect",
                    "method": "ping",
                }

                response = await client.post(
                    url,
                    json=test_message,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                    },
                )

                if response.status_code in [200, 202]:
                    content_type = response.headers.get("content-type", "")
                    if (
                        "application/json" in content_type
                        or "text/event-stream" in content_type
                    ):
                        streamable_http_works = True

            except Exception:
                pass

            # Test 2: Try SSE endpoint detection
            sse_works = False
            try:
                # Common SSE endpoint patterns
                sse_urls = [
                    url.replace("/mcp", "/sse"),
                    f"{url.rstrip('/mcp')}/sse",
                    f"{url}/sse",
                ]

                for sse_url in sse_urls:
                    try:
                        response = await client.get(sse_url)
                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "")
                            if "text/event-stream" in content_type:
                                sse_works = True
                                break
                    except Exception:
                        continue

            except Exception:
                pass

            # Determine result
            if streamable_http_works and sse_works:
                return "both"
            elif streamable_http_works:
                return "streamable_http"
            elif sse_works:
                return "sse"
            else:
                return "unknown"

    except Exception as e:
        logger.debug(f"Transport detection failed for {url}: {e}")
        return "unknown"


# Migration helpers
async def try_http_with_sse_fallback(
    url: str, bearer_token: Optional[str] = None, timeout: float = 30.0, **kwargs
):
    """
    Attempt Streamable HTTP connection with automatic SSE fallback.

    This function tries the modern Streamable HTTP transport first,
    and falls back to SSE if the server doesn't support it.

    Args:
        url: Server URL (should be the MCP endpoint)
        bearer_token: Optional authentication
        timeout: Connection timeout
        **kwargs: Additional parameters

    Returns:
        HTTP client context manager or SSE client context manager

    Raises:
        Exception: If neither transport works
    """
    try:
        # First try Streamable HTTP
        params = StreamableHTTPParameters(
            url=url, bearer_token=bearer_token, timeout=timeout, **kwargs
        )

        # Test if HTTP transport works
        transport_type = await detect_transport_type(url, bearer_token, timeout=timeout)

        if transport_type in ["streamable_http", "both"]:
            logger.info(f"Using Streamable HTTP transport for {url}")
            return http_client(params)
        else:
            raise Exception("Server does not support Streamable HTTP")

    except Exception as http_error:
        logger.warning(f"Streamable HTTP failed for {url}: {http_error}")

        # Try SSE fallback
        try:
            from ..sse import sse_client, SSEParameters

            # Convert URL from /mcp to /sse
            sse_url = url.replace("/mcp", "").rstrip("/")

            sse_params = SSEParameters(
                url=sse_url, bearer_token=bearer_token, timeout=timeout
            )

            logger.info(f"Falling back to SSE transport for {sse_url}")
            return sse_client(sse_params)

        except Exception as sse_error:
            raise Exception(
                f"Both Streamable HTTP and SSE transports failed. "
                f"HTTP error: {http_error}. SSE error: {sse_error}. "
                f"Server may not support MCP or may be misconfigured."
            )
