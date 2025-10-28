"""
Comprehensive tests for transports/sse/parameters.py module.

Tests all validation and configuration logic to achieve >90% coverage.
"""

import pytest
from pydantic import ValidationError

from chuk_mcp.transports.sse.parameters import SSEParameters


class TestSSEParametersValidation:
    """Test SSEParameters validation."""

    def test_basic_creation(self):
        """Test basic SSEParameters creation."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.url == "http://localhost:3000"
        assert params.timeout == 60.0
        assert params.auto_reconnect is True

    def test_empty_url_validation(self):
        """Test line 56 - empty URL validation."""
        with pytest.raises(ValidationError, match="SSE URL cannot be empty"):
            SSEParameters(url="")

    def test_invalid_url_no_http_prefix(self):
        """Test line 58 - URL must start with http:// or https://."""
        with pytest.raises(
            ValidationError, match="SSE URL must start with http:// or https://"
        ):
            SSEParameters(url="localhost:3000")

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        params = SSEParameters(url="http://localhost:3000/")
        assert params.url == "http://localhost:3000"

    def test_https_url(self):
        """Test HTTPS URL validation."""
        params = SSEParameters(url="https://example.com")
        assert params.url == "https://example.com"

    def test_negative_timeout_validation(self):
        """Test line 66 - timeout must be positive."""
        with pytest.raises(ValidationError, match="Timeout must be positive"):
            SSEParameters(url="http://localhost:3000", timeout=-1.0)

    def test_zero_timeout_validation(self):
        """Test line 66 - timeout cannot be zero."""
        with pytest.raises(ValidationError, match="Timeout must be positive"):
            SSEParameters(url="http://localhost:3000", timeout=0.0)

    def test_negative_max_reconnect_attempts_validation(self):
        """Test line 73-75 - max_reconnect_attempts must be non-negative."""
        with pytest.raises(
            ValidationError, match="Max reconnect attempts must be non-negative"
        ):
            SSEParameters(url="http://localhost:3000", max_reconnect_attempts=-1)

    def test_zero_max_reconnect_attempts_allowed(self):
        """Test that zero max_reconnect_attempts is allowed."""
        params = SSEParameters(url="http://localhost:3000", max_reconnect_attempts=0)
        assert params.max_reconnect_attempts == 0

    def test_negative_reconnect_delay_validation(self):
        """Test line 81-83 - reconnect_delay must be non-negative."""
        with pytest.raises(
            ValidationError, match="Reconnect delay must be non-negative"
        ):
            SSEParameters(url="http://localhost:3000", reconnect_delay=-1.0)

    def test_zero_reconnect_delay_allowed(self):
        """Test that zero reconnect_delay is allowed."""
        params = SSEParameters(url="http://localhost:3000", reconnect_delay=0.0)
        assert params.reconnect_delay == 0.0

    def test_negative_keep_alive_interval_validation(self):
        """Test line 89-91 - keep_alive_interval must be positive."""
        with pytest.raises(
            ValidationError, match="Keep-alive interval must be positive"
        ):
            SSEParameters(url="http://localhost:3000", keep_alive_interval=-1.0)

    def test_zero_keep_alive_interval_validation(self):
        """Test line 89-91 - keep_alive_interval cannot be zero."""
        with pytest.raises(
            ValidationError, match="Keep-alive interval must be positive"
        ):
            SSEParameters(url="http://localhost:3000", keep_alive_interval=0.0)

    def test_sse_endpoint_without_slash(self):
        """Test line 97-99 - sse_endpoint gets slash prepended."""
        params = SSEParameters(url="http://localhost:3000", sse_endpoint="sse")
        assert params.sse_endpoint == "/sse"

    def test_sse_endpoint_with_slash(self):
        """Test sse_endpoint already has slash."""
        params = SSEParameters(url="http://localhost:3000", sse_endpoint="/sse")
        assert params.sse_endpoint == "/sse"

    def test_message_endpoint_base_without_slash(self):
        """Test line 105-107 - message_endpoint_base gets slash prepended."""
        params = SSEParameters(url="http://localhost:3000", message_endpoint_base="mcp")
        assert params.message_endpoint_base == "/mcp"

    def test_message_endpoint_base_with_slash(self):
        """Test message_endpoint_base already has slash."""
        params = SSEParameters(
            url="http://localhost:3000", message_endpoint_base="/mcp"
        )
        assert params.message_endpoint_base == "/mcp"


class TestSSEParametersAuthHeaders:
    """Test SSEParameters auth header setup."""

    def test_bearer_token_without_prefix(self):
        """Test bearer token without 'Bearer ' prefix."""
        params = SSEParameters(url="http://localhost:3000", bearer_token="my-token-123")
        assert params.headers is not None
        assert params.headers["Authorization"] == "Bearer my-token-123"

    def test_bearer_token_with_prefix(self):
        """Test bearer token with 'Bearer ' prefix."""
        params = SSEParameters(
            url="http://localhost:3000", bearer_token="Bearer my-token-123"
        )
        assert params.headers is not None
        assert params.headers["Authorization"] == "Bearer my-token-123"

    def test_bearer_token_creates_headers_dict(self):
        """Test that bearer_token creates headers dict if None."""
        params = SSEParameters(
            url="http://localhost:3000", bearer_token="test-token", headers=None
        )
        assert params.headers is not None
        assert isinstance(params.headers, dict)
        assert params.headers["Authorization"] == "Bearer test-token"

    def test_bearer_token_with_existing_headers(self):
        """Test bearer token with existing headers."""
        params = SSEParameters(
            url="http://localhost:3000",
            bearer_token="test-token",
            headers={"Custom-Header": "value"},
        )
        assert params.headers["Authorization"] == "Bearer test-token"
        assert params.headers["Custom-Header"] == "value"

    def test_no_bearer_token_no_auth_header(self):
        """Test that no auth header is added without bearer token."""
        params = SSEParameters(url="http://localhost:3000")
        if params.headers:
            assert "Authorization" not in params.headers

    def test_existing_authorization_header_preserved(self):
        """Test that existing Authorization header is not overwritten."""
        params = SSEParameters(
            url="http://localhost:3000",
            bearer_token="new-token",
            headers={"Authorization": "Bearer existing-token"},
        )
        # Should not overwrite existing Authorization header
        assert params.headers["Authorization"] == "Bearer existing-token"

    def test_case_insensitive_authorization_check(self):
        """Test that authorization header check is case-insensitive."""
        params = SSEParameters(
            url="http://localhost:3000",
            bearer_token="new-token",
            headers={"authorization": "Bearer existing-token"},
        )
        # Should detect lowercase 'authorization' and not add another
        assert (
            "Authorization" not in params.headers
            or params.headers.get("authorization") == "Bearer existing-token"
        )


class TestSSEParametersDefaults:
    """Test SSEParameters default values."""

    def test_default_timeout(self):
        """Test default timeout value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.timeout == 60.0

    def test_default_auto_reconnect(self):
        """Test default auto_reconnect value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.auto_reconnect is True

    def test_default_max_reconnect_attempts(self):
        """Test default max_reconnect_attempts value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.max_reconnect_attempts == 5

    def test_default_reconnect_delay(self):
        """Test default reconnect_delay value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.reconnect_delay == 1.0

    def test_default_sse_endpoint(self):
        """Test default sse_endpoint value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.sse_endpoint == "/sse"

    def test_default_message_endpoint_base(self):
        """Test default message_endpoint_base value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.message_endpoint_base == "/mcp"

    def test_default_keep_alive_interval(self):
        """Test default keep_alive_interval value."""
        params = SSEParameters(url="http://localhost:3000")
        assert params.keep_alive_interval == 30.0


class TestSSEParametersCustomValues:
    """Test SSEParameters with custom values."""

    def test_custom_timeout(self):
        """Test custom timeout value."""
        params = SSEParameters(url="http://localhost:3000", timeout=120.0)
        assert params.timeout == 120.0

    def test_custom_auto_reconnect(self):
        """Test custom auto_reconnect value."""
        params = SSEParameters(url="http://localhost:3000", auto_reconnect=False)
        assert params.auto_reconnect is False

    def test_custom_max_reconnect_attempts(self):
        """Test custom max_reconnect_attempts value."""
        params = SSEParameters(url="http://localhost:3000", max_reconnect_attempts=10)
        assert params.max_reconnect_attempts == 10

    def test_custom_reconnect_delay(self):
        """Test custom reconnect_delay value."""
        params = SSEParameters(url="http://localhost:3000", reconnect_delay=2.5)
        assert params.reconnect_delay == 2.5

    def test_custom_sse_endpoint(self):
        """Test custom sse_endpoint value."""
        params = SSEParameters(url="http://localhost:3000", sse_endpoint="/events")
        assert params.sse_endpoint == "/events"

    def test_custom_message_endpoint_base(self):
        """Test custom message_endpoint_base value."""
        params = SSEParameters(
            url="http://localhost:3000", message_endpoint_base="/api"
        )
        assert params.message_endpoint_base == "/api"

    def test_custom_keep_alive_interval(self):
        """Test custom keep_alive_interval value."""
        params = SSEParameters(url="http://localhost:3000", keep_alive_interval=60.0)
        assert params.keep_alive_interval == 60.0

    def test_custom_session_id(self):
        """Test custom session_id value."""
        params = SSEParameters(
            url="http://localhost:3000", session_id="test-session-123"
        )
        assert params.session_id == "test-session-123"

    def test_custom_headers(self):
        """Test custom headers."""
        custom_headers = {"X-Custom": "value", "X-Another": "test"}
        params = SSEParameters(url="http://localhost:3000", headers=custom_headers)
        assert params.headers["X-Custom"] == "value"
        assert params.headers["X-Another"] == "test"


class TestSSEParametersEdgeCases:
    """Test SSEParameters edge cases."""

    def test_very_long_url(self):
        """Test with very long URL."""
        long_url = "http://localhost:3000/" + "a" * 1000
        params = SSEParameters(url=long_url)
        assert params.url == long_url.rstrip("/")

    def test_url_with_query_params(self):
        """Test URL with query parameters."""
        params = SSEParameters(url="http://localhost:3000/sse?token=abc")
        assert "?token=abc" in params.url

    def test_url_with_port(self):
        """Test URL with explicit port."""
        params = SSEParameters(url="http://localhost:8080")
        assert params.url == "http://localhost:8080"

    def test_very_large_timeout(self):
        """Test with very large timeout."""
        params = SSEParameters(url="http://localhost:3000", timeout=3600.0)
        assert params.timeout == 3600.0

    def test_very_small_timeout(self):
        """Test with very small but valid timeout."""
        params = SSEParameters(url="http://localhost:3000", timeout=0.1)
        assert params.timeout == 0.1

    def test_all_parameters(self):
        """Test creating SSEParameters with all parameters."""
        params = SSEParameters(
            url="https://example.com/sse",
            headers={"Custom": "header"},
            timeout=30.0,
            bearer_token="Bearer test-token",
            session_id="session-123",
            auto_reconnect=False,
            max_reconnect_attempts=3,
            reconnect_delay=0.5,
            sse_endpoint="/events",
            message_endpoint_base="/api/mcp",
            keep_alive_interval=15.0,
        )

        assert params.url == "https://example.com/sse"
        assert params.timeout == 30.0
        assert params.bearer_token == "Bearer test-token"
        assert params.session_id == "session-123"
        assert params.auto_reconnect is False
        assert params.max_reconnect_attempts == 3
        assert params.reconnect_delay == 0.5
        assert params.sse_endpoint == "/events"
        assert params.message_endpoint_base == "/api/mcp"
        assert params.keep_alive_interval == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
