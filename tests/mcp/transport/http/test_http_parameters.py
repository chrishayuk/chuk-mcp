# tests/mcp/transport/http/test_http_parameters.py
"""
Tests for Streamable HTTP transport parameters.
"""
import pytest

try:
    from pydantic import ValidationError
except ImportError:
    from chuk_mcp.protocol.mcp_pydantic_base import ValidationError

from chuk_mcp.transports.http.parameters import StreamableHTTPParameters


def test_streamable_http_parameters_minimal():
    """Test creating Streamable HTTP parameters with minimal required fields."""
    params = StreamableHTTPParameters(url="http://localhost:3000")
    
    assert params.url == "http://localhost:3000"
    # Headers will contain User-Agent automatically
    assert params.headers is not None
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert params.timeout == 60.0
    assert params.enable_streaming is True
    assert params.max_concurrent_requests == 10


def test_streamable_http_parameters_full():
    """Test creating Streamable HTTP parameters with all fields."""
    params = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer token", "X-Client": "test"},
        timeout=30.0,
        bearer_token="test-token",
        enable_streaming=False,
        max_concurrent_requests=5
    )
    
    assert params.url == "https://api.example.com/mcp"
    assert params.headers["Authorization"] == "Bearer token"
    assert params.headers["X-Client"] == "test"
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"  # Auto-added
    assert params.timeout == 30.0
    assert params.bearer_token == "test-token"
    assert params.enable_streaming is False
    assert params.max_concurrent_requests == 5


def test_streamable_http_parameters_default_values():
    """Test that default values are correct."""
    params = StreamableHTTPParameters(url="http://localhost:3000")
    
    # Test all defaults - headers will have User-Agent auto-added
    assert params.headers is not None
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert params.timeout == 60.0
    assert params.bearer_token is None
    assert params.session_id is None
    assert params.user_agent == "chuk-mcp/1.0.0"
    assert params.max_retries == 3
    assert params.retry_delay == 1.0
    assert params.enable_streaming is True
    assert params.max_concurrent_requests == 10


def test_streamable_http_parameters_url_validation():
    """Test URL validation."""
    # Valid URLs should work
    valid_urls = [
        "http://localhost:3000",
        "https://api.example.com",
        "http://127.0.0.1:8080/mcp",
        "https://subdomain.example.com:9000/path"
    ]
    
    for url in valid_urls:
        params = StreamableHTTPParameters(url=url)
        assert params.url == url
    
    # Invalid URLs should raise ValidationError
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="")
    
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="not-a-url")


def test_streamable_http_parameters_timeout_validation():
    """Test timeout validation."""
    # Valid timeouts
    valid_timeouts = [0.1, 1.0, 30.0, 60.0, 300.0]
    
    for timeout in valid_timeouts:
        params = StreamableHTTPParameters(url="http://localhost:3000", timeout=timeout)
        assert params.timeout == timeout
    
    # Invalid timeouts should raise ValidationError
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", timeout=0)
    
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", timeout=-1)


def test_streamable_http_parameters_auth_setup():
    """Test automatic auth header setup."""
    # Test with bearer token
    params = StreamableHTTPParameters(
        url="http://localhost:3000",
        bearer_token="test-token-123"
    )
    
    assert params.headers is not None
    assert params.headers["Authorization"] == "Bearer test-token-123"
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"
    
    # Test with Bearer prefix already included
    params = StreamableHTTPParameters(
        url="http://localhost:3000",
        bearer_token="Bearer already-prefixed-token"
    )
    
    assert params.headers["Authorization"] == "Bearer already-prefixed-token"


def test_streamable_http_parameters_headers_merge():
    """Test that headers are properly merged."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000",
        headers={"X-Custom": "value"},
        bearer_token="token-123"
    )
    
    # Should have both custom headers and auto-added ones
    assert params.headers["X-Custom"] == "value"
    assert params.headers["Authorization"] == "Bearer token-123"
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"


def test_streamable_http_parameters_concurrent_requests_validation():
    """Test max concurrent requests validation."""
    # Valid values
    params = StreamableHTTPParameters(url="http://localhost:3000", max_concurrent_requests=5)
    assert params.max_concurrent_requests == 5
    
    # Invalid values should raise ValidationError
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", max_concurrent_requests=0)
    
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", max_concurrent_requests=-1)


def test_streamable_http_parameters_retries_validation():
    """Test retry settings validation."""
    # Valid retry settings
    params = StreamableHTTPParameters(
        url="http://localhost:3000",
        max_retries=5,
        retry_delay=2.0
    )
    assert params.max_retries == 5
    assert params.retry_delay == 2.0
    
    # Invalid max_retries
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", max_retries=-1)
    
    # Invalid retry_delay
    with pytest.raises(ValidationError):
        StreamableHTTPParameters(url="http://localhost:3000", retry_delay=-1.0)


def test_streamable_http_parameters_model_dump():
    """Test model serialization."""
    params = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"X-Test": "value"},
        timeout=45.0,
        enable_streaming=False,
        max_concurrent_requests=8
    )
    
    dump = params.model_dump()
    
    assert dump["url"] == "https://api.example.com/mcp"
    assert dump["timeout"] == 45.0
    assert dump["enable_streaming"] is False
    assert dump["max_concurrent_requests"] == 8


def test_streamable_http_parameters_model_dump_json():
    """Test JSON serialization."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000",
        headers={"X-Test": "value"},
        timeout=15.0,
        enable_streaming=True
    )
    
    json_str = params.model_dump_json()
    
    assert '"url":"http://localhost:3000"' in json_str
    assert '"timeout":15.0' in json_str
    assert '"enable_streaming":true' in json_str


def test_streamable_http_parameters_inheritance():
    """Test that StreamableHTTPParameters properly inherits from TransportParameters."""
    from chuk_mcp.transports.base import TransportParameters
    
    params = StreamableHTTPParameters(url="http://localhost:3000")
    
    assert isinstance(params, TransportParameters)


def test_streamable_http_parameters_with_transport():
    """Test that StreamableHTTPParameters work with StreamableHTTPTransport."""
    from chuk_mcp.transports.http.transport import StreamableHTTPTransport
    
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        headers={"X-Test": "value"},
        timeout=30.0,
        enable_streaming=False
    )
    transport = StreamableHTTPTransport(params)
    
    # Verify the transport holds the parameters correctly
    assert transport.endpoint_url == "http://localhost:3000/mcp"
    # Headers will include both custom header and auto-added User-Agent
    assert transport.headers["X-Test"] == "value"
    assert transport.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert transport.timeout == 30.0
    assert transport.enable_streaming is False


def test_streamable_http_parameters_url_trailing_slash():
    """Test URL trailing slash handling."""
    # URL with trailing slash should be normalized
    params = StreamableHTTPParameters(url="http://localhost:3000/")
    assert params.url == "http://localhost:3000"
    
    # URL without trailing slash should remain unchanged
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    assert params.url == "http://localhost:3000/mcp"


def test_streamable_http_parameters_complex_scenarios():
    """Test complex real-world scenarios."""
    # Production API setup
    params = StreamableHTTPParameters(
        url="https://api.mycompany.com/mcp/v2",
        bearer_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test",
        timeout=45.0,
        enable_streaming=True,
        max_concurrent_requests=15,
        max_retries=5,
        retry_delay=2.0,
        session_id="existing-session-123"
    )
    
    assert params.url == "https://api.mycompany.com/mcp/v2"
    assert params.headers["Authorization"].startswith("Bearer eyJ0eXAi")
    assert params.timeout == 45.0
    assert params.enable_streaming is True
    assert params.max_concurrent_requests == 15
    assert params.max_retries == 5
    assert params.retry_delay == 2.0
    assert params.session_id == "existing-session-123"
    
    # Local development setup
    params = StreamableHTTPParameters(
        url="http://localhost:8000/mcp",
        headers={"X-Dev-Mode": "true"},
        timeout=5.0,
        enable_streaming=False  # Disable for simpler debugging
    )
    
    assert params.url == "http://localhost:8000/mcp"
    assert params.headers["X-Dev-Mode"] == "true"
    assert params.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert params.timeout == 5.0
    assert params.enable_streaming is False


def test_streamable_http_parameters_round_trip():
    """Test parameter round-trip serialization."""
    original = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer token", "X-Custom": "value"},
        timeout=30.0,
        bearer_token="token",
        enable_streaming=True,
        max_concurrent_requests=8
    )
    
    # Serialize and deserialize
    data = original.model_dump()
    restored = StreamableHTTPParameters.model_validate(data)
    
    assert restored.url == original.url
    assert restored.timeout == original.timeout
    assert restored.enable_streaming == original.enable_streaming
    assert restored.max_concurrent_requests == original.max_concurrent_requests
    
    # JSON round-trip
    json_str = original.model_dump_json()
    import json
    data = json.loads(json_str)
    restored = StreamableHTTPParameters.model_validate(data)
    
    assert restored.url == original.url
    assert restored.timeout == original.timeout


def test_streamable_http_parameters_headers_behavior():
    """Test how headers are handled in different scenarios."""
    
    # Test 1: No headers provided - should auto-add User-Agent
    params1 = StreamableHTTPParameters(url="http://localhost:3000")
    assert "User-Agent" in params1.headers
    assert params1.headers["User-Agent"] == "chuk-mcp/1.0.0"
    
    # Test 2: Custom headers provided - should merge with User-Agent
    params2 = StreamableHTTPParameters(
        url="http://localhost:3000",
        headers={"X-Custom": "value"}
    )
    assert "User-Agent" in params2.headers
    assert "X-Custom" in params2.headers
    assert params2.headers["User-Agent"] == "chuk-mcp/1.0.0"
    assert params2.headers["X-Custom"] == "value"
    
    # Test 3: Bearer token provided - should add Authorization
    params3 = StreamableHTTPParameters(
        url="http://localhost:3000",
        bearer_token="test123"
    )
    assert "User-Agent" in params3.headers
    assert "Authorization" in params3.headers
    assert params3.headers["Authorization"] == "Bearer test123"
    assert params3.headers["User-Agent"] == "chuk-mcp/1.0.0"