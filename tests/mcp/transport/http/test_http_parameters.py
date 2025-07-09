# tests/mcp/transport/http/test_http_parameters.py
"""
Tests for HTTP transport parameters.
"""
import pytest

try:
    from pydantic import ValidationError
except ImportError:
    from chuk_mcp.protocol.mcp_pydantic_base import ValidationError

from chuk_mcp.transports.http.parameters import HTTPParameters


def test_http_parameters_minimal():
    """Test creating HTTP parameters with minimal required fields."""
    params = HTTPParameters(url="http://localhost:3000")
    
    assert params.url == "http://localhost:3000"
    assert params.headers is None
    assert params.timeout == 60.0
    assert params.method == "POST"


def test_http_parameters_full():
    """Test creating HTTP parameters with all fields."""
    params = HTTPParameters(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer token", "X-Client": "test"},
        timeout=30.0,
        method="PUT"
    )
    
    assert params.url == "https://api.example.com/mcp"
    assert params.headers == {"Authorization": "Bearer token", "X-Client": "test"}
    assert params.timeout == 30.0
    assert params.method == "PUT"


def test_http_parameters_default_values():
    """Test that default values are correct."""
    params = HTTPParameters(url="http://localhost:3000")
    
    # Test all defaults
    assert params.headers is None
    assert params.timeout == 60.0
    assert params.method == "POST"


def test_http_parameters_various_methods():
    """Test HTTP parameters with different HTTP methods."""
    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    
    for method in methods:
        params = HTTPParameters(url="http://localhost:3000", method=method)
        assert params.method == method


def test_http_parameters_various_urls():
    """Test HTTP parameters with different URL formats."""
    urls = [
        "http://localhost:3000",
        "https://api.example.com",
        "http://127.0.0.1:8080",
        "https://subdomain.example.com:9000/path",
        "http://example.com/mcp/v1",
        "https://api.example.com/mcp?param=value"
    ]
    
    for url in urls:
        params = HTTPParameters(url=url)
        assert params.url == url


def test_http_parameters_timeout_values():
    """Test HTTP parameters with different timeout values."""
    timeouts = [1.0, 30.0, 60.0, 120.0, 300.0]
    
    for timeout in timeouts:
        params = HTTPParameters(url="http://localhost:3000", timeout=timeout)
        assert params.timeout == timeout


def test_http_parameters_headers():
    """Test HTTP parameters with various headers."""
    # Test with authentication
    params = HTTPParameters(
        url="http://localhost:3000",
        headers={"Authorization": "Bearer abc123"}
    )
    assert params.headers["Authorization"] == "Bearer abc123"
    
    # Test with multiple headers
    params = HTTPParameters(
        url="http://localhost:3000",
        headers={
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
            "X-API-Version": "v1",
            "User-Agent": "MyApp/1.0"
        }
    )
    assert len(params.headers) == 4
    assert params.headers["Authorization"] == "Bearer token"
    assert params.headers["X-API-Version"] == "v1"
    
    # Test with empty headers dict
    params = HTTPParameters(url="http://localhost:3000", headers={})
    assert params.headers == {}


def test_http_parameters_model_dump():
    """Test model serialization."""
    params = HTTPParameters(
        url="https://api.example.com/mcp",
        headers={"X-Test": "value"},
        timeout=45.0,
        method="PUT"
    )
    
    dump = params.model_dump()
    expected = {
        "url": "https://api.example.com/mcp",
        "headers": {"X-Test": "value"},
        "timeout": 45.0,
        "method": "PUT"
    }
    
    assert dump == expected


def test_http_parameters_model_dump_exclude():
    """Test model serialization with exclusions."""
    params = HTTPParameters(
        url="https://api.example.com",
        headers={"Authorization": "Bearer secret"},
        timeout=30.0,
        method="POST"
    )
    
    dump = params.model_dump(exclude={"headers"})
    
    assert "headers" not in dump
    assert dump["url"] == "https://api.example.com"
    assert dump["timeout"] == 30.0
    assert dump["method"] == "POST"


def test_http_parameters_model_dump_json():
    """Test JSON serialization."""
    params = HTTPParameters(
        url="http://localhost:3000",
        headers={"X-Test": "value"},
        timeout=15.0,
        method="GET"
    )
    
    json_str = params.model_dump_json()
    
    assert '"url":"http://localhost:3000"' in json_str
    assert '"timeout":15.0' in json_str
    assert '"method":"GET"' in json_str
    assert '"X-Test":"value"' in json_str


def test_http_parameters_inheritance():
    """Test that HTTPParameters properly inherits from TransportParameters."""
    from chuk_mcp.transports.base import TransportParameters
    
    params = HTTPParameters(url="http://localhost:3000")
    
    assert isinstance(params, TransportParameters)


def test_http_parameters_with_transport():
    """Test that HTTPParameters work with HTTPTransport."""
    from chuk_mcp.transports.http.transport import HTTPTransport
    
    params = HTTPParameters(
        url="http://localhost:3000/mcp",
        headers={"X-Test": "value"},
        timeout=30.0,
        method="PUT"
    )
    transport = HTTPTransport(params)
    
    # Verify the transport holds the parameters correctly
    assert transport.parameters == params
    assert transport.url == "http://localhost:3000/mcp"
    assert transport.headers == {"X-Test": "value"}
    assert transport.timeout == 30.0
    assert transport.method == "PUT"


def test_http_parameters_edge_cases():
    """Test edge cases and boundary values."""
    # Very short timeout
    params = HTTPParameters(url="http://localhost:3000", timeout=0.1)
    assert params.timeout == 0.1
    
    # Very long timeout
    params = HTTPParameters(url="http://localhost:3000", timeout=3600.0)
    assert params.timeout == 3600.0
    
    # Long URL
    long_url = "https://very-long-subdomain.example.com:8080/very/long/path/to/mcp/endpoint?param1=value1&param2=value2"
    params = HTTPParameters(url=long_url)
    assert params.url == long_url
    
    # Custom method
    params = HTTPParameters(url="http://localhost:3000", method="CUSTOM")
    assert params.method == "CUSTOM"


def test_http_parameters_complex_scenarios():
    """Test complex real-world scenarios."""
    # API with authentication and custom headers
    params = HTTPParameters(
        url="https://api.mycompany.com/mcp/v2",
        headers={
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "X-API-Version": "2024-01",
            "X-Client-ID": "my-app",
            "User-Agent": "MyApp/2.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        timeout=45.0,
        method="POST"
    )
    
    assert params.url == "https://api.mycompany.com/mcp/v2"
    assert len(params.headers) == 6
    assert params.headers["Authorization"].startswith("Bearer eyJ0eXAi")
    assert params.headers["X-API-Version"] == "2024-01"
    assert params.timeout == 45.0
    assert params.method == "POST"
    
    # Local development setup
    params = HTTPParameters(
        url="http://localhost:8080/mcp",
        headers={"X-Dev-Mode": "true"},
        timeout=5.0,
        method="POST"
    )
    
    assert params.url == "http://localhost:8080/mcp"
    assert params.headers["X-Dev-Mode"] == "true"
    assert params.timeout == 5.0
    assert params.method == "POST"
    
    # Microservice internal communication
    params = HTTPParameters(
        url="http://mcp-service:3000/internal/mcp",
        headers={
            "X-Service-Name": "api-gateway",
            "X-Request-ID": "req-123456",
            "X-Internal-Auth": "service-token"
        },
        timeout=10.0,
        method="POST"
    )
    
    assert params.url == "http://mcp-service:3000/internal/mcp"
    assert params.headers["X-Service-Name"] == "api-gateway"
    assert params.headers["X-Request-ID"] == "req-123456"
    assert params.timeout == 10.0


def test_http_parameters_pydantic_features():
    """Test that HTTPParameters has proper pydantic functionality."""
    params = HTTPParameters(
        url="https://api.example.com",
        headers={"Authorization": "Bearer token"},
        timeout=30.0,
        method="PUT"
    )
    
    # Test that pydantic methods exist and work
    assert hasattr(params, 'model_dump')
    assert hasattr(params, 'model_dump_json')
    assert hasattr(params, 'model_validate')
    assert callable(params.model_dump)
    assert callable(params.model_dump_json)
    assert callable(params.model_validate)
    
    # Test round-trip serialization
    data = params.model_dump()
    restored = HTTPParameters.model_validate(data)
    
    assert restored.url == params.url
    assert restored.headers == params.headers
    assert restored.timeout == params.timeout
    assert restored.method == params.method
    
    # Test JSON round-trip
    json_str = params.model_dump_json()
    import json
    data = json.loads(json_str)
    restored = HTTPParameters.model_validate(data)
    
    assert restored.url == params.url
    assert restored.headers == params.headers
    assert restored.timeout == params.timeout
    assert restored.method == params.method


def test_http_parameters_immutability():
    """Test parameter immutability and copying."""
    original = HTTPParameters(
        url="http://localhost:3000",
        headers={"X-Test": "original"},
        timeout=60.0,
        method="POST"
    )
    
    # Test copying
    data = original.model_dump()
    copy = HTTPParameters.model_validate(data)
    
    # Modify copy's headers
    if copy.headers:
        copy.headers["X-Test"] = "modified"
    
    # Original should be unchanged
    assert original.headers["X-Test"] == "original"
    assert copy.headers["X-Test"] == "modified"


def test_http_parameters_validation_compatibility():
    """Test compatibility with different validation approaches."""
    # Test that basic validation works
    params = HTTPParameters(url="http://localhost:3000")
    assert params.url == "http://localhost:3000"
    
    # Test that model_validate works
    data = {"url": "http://example.com", "method": "GET"}
    params = HTTPParameters.model_validate(data)
    assert params.url == "http://example.com"
    assert params.method == "GET"
    
    # Test that extra fields are handled gracefully (if allowed)
    try:
        data_with_extra = {
            "url": "http://localhost:3000",
            "extra_field": "should_be_ignored_or_allowed"
        }
        params = HTTPParameters.model_validate(data_with_extra)
        # If we get here, extra fields are allowed
        assert params.url == "http://localhost:3000"
    except ValidationError:
        # If we get here, extra fields are not allowed (also fine)
        pass