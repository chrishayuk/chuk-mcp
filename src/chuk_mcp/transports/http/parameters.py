# chuk_mcp/transports/http/parameters.py
"""
Parameters for Streamable HTTP transport.

This implements the new MCP specification (2025-03-26) that replaces SSE transport.
"""

from typing import Optional, Dict
from pydantic import field_validator, model_validator
from ..base import TransportParameters
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class StreamableHTTPParameters(TransportParameters, McpPydanticBase):
    """
    Parameters for Streamable HTTP transport (MCP spec 2025-03-26).

    This is the modern replacement for the deprecated SSE transport.
    Supports both simple HTTP responses and optional SSE streaming.
    """

    url: str
    """Base URL for the MCP server (e.g., 'http://localhost:3000/mcp')"""

    headers: Optional[Dict[str, str]] = None
    """Optional HTTP headers to send with requests"""

    timeout: float = 60.0
    """Request timeout in seconds"""

    bearer_token: Optional[str] = None
    """Optional bearer token for authentication (added to Authorization header)"""

    session_id: Optional[str] = None
    """Optional session ID for reconnecting to existing sessions"""

    user_agent: str = "chuk-mcp/1.0.0"
    """User agent string for HTTP requests"""

    max_retries: int = 3
    """Maximum number of retry attempts for failed requests"""

    retry_delay: float = 1.0
    """Delay between retry attempts in seconds"""

    enable_streaming: bool = True
    """Whether to accept SSE streaming responses when available"""

    max_concurrent_requests: int = 10
    """Maximum number of concurrent requests"""

    model_config = {"extra": "allow"}

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v:
            raise ValueError("Streamable HTTP URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Streamable HTTP URL must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash for consistency

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v):
        """Validate max retries is non-negative."""
        if v < 0:
            raise ValueError("Max retries must be non-negative")
        return v

    @field_validator("retry_delay")
    @classmethod
    def validate_retry_delay(cls, v):
        """Validate retry delay is non-negative."""
        if v < 0:
            raise ValueError("Retry delay must be non-negative")
        return v

    @field_validator("max_concurrent_requests")
    @classmethod
    def validate_max_concurrent_requests(cls, v):
        """Validate max concurrent requests is positive."""
        if v <= 0:
            raise ValueError("Max concurrent requests must be positive")
        return v

    @model_validator(mode="after")
    def setup_auth_headers(self):
        """Set up authentication headers after model creation."""
        # FIXED: Don't directly assign to self.headers (causes recursion)
        # Instead, use object.__setattr__ to bypass validation

        if self.headers is None:
            object.__setattr__(self, "headers", {})

        # Make a copy to avoid modifying during iteration
        headers = dict(self.headers)

        # Add User-Agent if not present
        if "user-agent" not in {k.lower() for k in headers.keys()}:
            headers["User-Agent"] = self.user_agent

        # Add Authorization header if bearer token provided
        if self.bearer_token:
            if not any(key.lower() == "authorization" for key in headers.keys()):
                if self.bearer_token.startswith("Bearer "):
                    headers["Authorization"] = self.bearer_token
                else:
                    headers["Authorization"] = f"Bearer {self.bearer_token}"

        # Update headers using object.__setattr__ to avoid recursion
        object.__setattr__(self, "headers", headers)

        return self
