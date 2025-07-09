# tests/mcp/transport/http/test_http_transport.py
"""
Tests for HTTP transport implementation.
"""
import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from chuk_mcp.transports.http.parameters import HTTPParameters
from chuk_mcp.transports.http.transport import HTTPTransport
from chuk_mcp.transports.http import http_client
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

pytest.importorskip("httpx")
pytest.importorskip("chuk_mcp.transports.http")

###############################################################################
# Parameter Tests
###############################################################################

def test_http_parameters_creation():
    """Test creating HTTP parameters."""
    params = HTTPParameters(url="http://localhost:3000/mcp")
    assert params.url == "http://localhost:3000/mcp"
    assert params.headers is None
    assert params.timeout == 60.0
    assert params.method == "POST"

def test_http_parameters_with_all_fields():
    """Test HTTP parameters with all fields."""
    params = HTTPParameters(
        url="https://api.example.com/mcp",
        headers={"X-API-Key": "key123"},
        timeout=30.0,
        method="PUT"
    )
    
    assert params.url == "https://api.example.com/mcp"
    assert params.headers == {"X-API-Key": "key123"}
    assert params.timeout == 30.0
    assert params.method == "PUT"

def test_http_parameters_validation():
    """Test HTTP parameter validation."""
    # Basic validation - these should work
    params = HTTPParameters(url="http://localhost:3000")
    assert params.url == "http://localhost:3000"
    
    # Test serialization
    data = params.model_dump()
    assert data["url"] == "http://localhost:3000"
    assert data["method"] == "POST"

def test_http_parameters_serialization():
    """Test parameter serialization."""
    params = HTTPParameters(
        url="https://api.example.com",
        headers={"Authorization": "Bearer token"},
        timeout=45.0,
        method="POST"
    )
    
    # Test dict serialization
    data = params.model_dump()
    assert data["url"] == "https://api.example.com"
    assert data["timeout"] == 45.0
    assert data["method"] == "POST"
    
    # Test JSON serialization
    json_str = params.model_dump_json()
    assert "api.example.com" in json_str
    assert "POST" in json_str

###############################################################################
# Transport Creation Tests
###############################################################################

def test_http_transport_creation():
    """Test creating HTTP transport."""
    params = HTTPParameters(url="http://localhost:3000/mcp")
    transport = HTTPTransport(params)
    
    assert transport.parameters == params
    assert transport.url == "http://localhost:3000/mcp"
    assert transport.method == "POST"
    assert transport._client is None
    assert transport._negotiated_version is None

def test_http_transport_with_custom_method():
    """Test HTTP transport with custom method."""
    params = HTTPParameters(url="http://localhost:3000", method="PUT")
    transport = HTTPTransport(params)
    
    assert transport.method == "PUT"

def test_http_transport_get_streams_before_start():
    """Test that get_streams raises error before starting."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    with pytest.raises(RuntimeError, match="Transport not started"):
        asyncio.run(transport.get_streams())

def test_http_transport_protocol_version():
    """Test protocol version handling."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Initially no version
    assert transport.get_protocol_version() is None
    assert transport.is_version_header_required() is False
    
    # Set old version (no header required)
    transport.set_protocol_version("2025-03-26")
    assert transport.get_protocol_version() == "2025-03-26"
    assert transport.is_version_header_required() is False
    
    # Set new version (header required)
    transport.set_protocol_version("2025-06-18")
    assert transport.get_protocol_version() == "2025-06-18"
    assert transport.is_version_header_required() is True

###############################################################################
# Message Sending Tests
###############################################################################

@pytest.mark.asyncio
async def test_send_message_success():
    """Test successful message sending."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    transport.set_protocol_version("2025-06-18")
    
    # Mock HTTP client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"status": "ok"}
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.request.return_value = mock_response
    transport._client = mock_client
    
    # Test message
    test_message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "ping"
    })
    
    # Send message
    response = await transport._send_message(test_message)
    
    # Verify request was made correctly
    assert mock_client.request.called
    call_args = mock_client.request.call_args
    
    # Check HTTP method and URL
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "http://localhost:3000"
    
    # Check request body
    assert call_args[1]["json"]["method"] == "ping"
    
    # Check headers include protocol version
    headers = call_args[1]["headers"]
    assert headers["MCP-Protocol-Version"] == "2025-06-18"
    assert headers["Content-Type"] == "application/json"
    
    # Check response
    assert isinstance(response, JSONRPCMessage)
    assert response.id == "test-123"
    assert response.result == {"status": "ok"}

@pytest.mark.asyncio
async def test_send_message_without_version():
    """Test sending message without protocol version set."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Mock HTTP client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "init",
        "result": {"protocolVersion": "2025-06-18"}
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.request.return_value = mock_response
    transport._client = mock_client
    
    # Test initialization message
    init_message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize"
    })
    
    # Send message
    response = await transport._send_message(init_message)
    
    # FIX: Get the call args from the mock
    call_args = mock_client.request.call_args
    
    # Check that no protocol version header was sent
    headers = call_args[1]["headers"]
    assert "MCP-Protocol-Version" not in headers
    
    # Response should be valid
    assert response.id == "init"
    
@pytest.mark.asyncio
async def test_send_message_http_error():
    """Test handling HTTP errors."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Mock HTTP client that raises an error
    mock_client = AsyncMock()
    mock_client.request.side_effect = Exception("Connection failed")
    transport._client = mock_client
    
    test_message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "test",
        "method": "ping"
    })
    
    # Send message
    response = await transport._send_message(test_message)
    
    # Should get error response
    assert isinstance(response, JSONRPCMessage)
    assert response.id == "test"
    assert response.error is not None
    assert "Connection failed" in response.error["message"]

@pytest.mark.asyncio
async def test_send_message_no_client():
    """Test sending message when client is None."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    transport._client = None
    
    test_message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "test",
        "method": "ping"
    })
    
    # Should return None gracefully
    response = await transport._send_message(test_message)
    assert response is None

###############################################################################
# Context Manager Tests
###############################################################################

@pytest.mark.asyncio
async def test_http_transport_context_manager():
    """Test HTTP transport as context manager."""
    params = HTTPParameters(url="http://localhost:3000")
    transport = HTTPTransport(params)
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        async with transport:
            # Verify client was created
            assert transport._client == mock_client
            
            # Verify streams are available
            read_stream, write_stream = await transport.get_streams()
            assert read_stream is not None
            assert write_stream is not None
        
        # Verify cleanup
        assert mock_client.aclose.called

@pytest.mark.asyncio
async def test_http_transport_with_auth_headers():
    """Test HTTP transport with authentication headers."""
    params = HTTPParameters(
        url="http://localhost:3000",
        headers={"Authorization": "Bearer token123"}
    )
    transport = HTTPTransport(params)
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        async with transport:
            # Verify client was created with correct headers
            client_args = mock_client_class.call_args
            headers = client_args[1]["headers"]
            assert headers["Authorization"] == "Bearer token123"
            assert headers["Content-Type"] == "application/json"

@pytest.mark.asyncio
async def test_http_transport_env_bearer_token():
    """Test automatic bearer token from environment."""
    params = HTTPParameters(url="http://localhost:3000")
    transport = HTTPTransport(params)
    
    with patch.dict(os.environ, {"MCP_BEARER_TOKEN": "env-token-456"}):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            async with transport:
                # Verify env token was used
                client_args = mock_client_class.call_args
                headers = client_args[1]["headers"]
                assert headers["Authorization"] == "Bearer env-token-456"

###############################################################################
# HTTP Client Context Manager Tests
###############################################################################

@pytest.mark.asyncio
async def test_http_client_context_manager():
    """Test http_client context manager."""
    params = HTTPParameters(url="http://localhost:3000")
    
    with patch('chuk_mcp.transports.http.http_client.HTTPTransport') as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport
        
        # Mock context manager
        mock_transport.__aenter__.return_value = mock_transport
        mock_transport.__aexit__.return_value = False
        
        # Mock get_streams
        from anyio import create_memory_object_stream
        read_stream, write_send = create_memory_object_stream(10)
        write_recv, write_stream = create_memory_object_stream(10)
        mock_transport.get_streams.return_value = (read_stream, write_stream)
        
        async with http_client(params) as (r_stream, w_stream):
            assert r_stream is not None
            assert w_stream is not None
            
            # Verify transport was created correctly
            mock_transport_class.assert_called_once_with(params)

@pytest.mark.asyncio
async def test_http_client_error_propagation():
    """Test that http_client propagates errors correctly."""
    params = HTTPParameters(url="http://localhost:3000")
    
    with patch('chuk_mcp.transports.http.http_client.HTTPTransport') as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport
        
        # Mock error during context manager entry
        mock_transport.__aenter__.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            async with http_client(params) as (read_stream, write_stream):
                pass

###############################################################################
# Protocol Version Tests
###############################################################################

def test_version_header_requirement_detection():
    """Test detection of when MCP-Protocol-Version header is required."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # No version set
    assert transport.is_version_header_required() is False
    
    # Old versions (before 2025-06-18)
    for version in ["2024-11-05", "2025-03-26", "2025-06-17"]:
        transport.set_protocol_version(version)
        assert transport.is_version_header_required() is False, f"Version {version} should not require header"
    
    # New versions (2025-06-18 and later)
    for version in ["2025-06-18", "2025-06-19", "2025-07-01", "2026-01-01"]:
        transport.set_protocol_version(version)
        assert transport.is_version_header_required() is True, f"Version {version} should require header"
    
    # Invalid versions (should return False for safety)
    for version in ["invalid", "2025", "2025-06", "not-a-date"]:
        transport.set_protocol_version(version)
        assert transport.is_version_header_required() is False, f"Invalid version {version} should not require header"

def test_set_protocol_version():
    """Test setting protocol version."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Test setting version
    transport.set_protocol_version("2025-06-18")
    assert transport.get_protocol_version() == "2025-06-18"
    
    # Test updating version
    transport.set_protocol_version("2025-07-01")
    assert transport.get_protocol_version() == "2025-07-01"

###############################################################################
# Integration Tests
###############################################################################

@pytest.mark.asyncio
async def test_full_message_flow():
    """Test complete message send/receive flow."""
    params = HTTPParameters(url="http://localhost:3000/mcp")
    transport = HTTPTransport(params)
    transport.set_protocol_version("2025-06-18")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "flow-test",
            "result": {"tools": [{"name": "echo"}]}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.request.return_value = mock_response
        
        async with transport:
            read_stream, write_stream = await transport.get_streams()
            
            # Send a message
            outgoing_message = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "flow-test",
                "method": "tools/list"
            })
            
            await write_stream.send(outgoing_message)
            
            # Give time for processing
            await asyncio.sleep(0.1)
            
            # Should receive response
            import anyio
            with anyio.fail_after(1.0):
                response = await read_stream.receive()
            
            assert response.id == "flow-test"
            assert response.result["tools"][0]["name"] == "echo"
            
            # Verify HTTP request was made correctly
            assert mock_client.request.called
            call_args = mock_client.request.call_args
            assert call_args[1]["headers"]["MCP-Protocol-Version"] == "2025-06-18"

###############################################################################
# Edge Cases and Error Handling
###############################################################################

@pytest.mark.asyncio
async def test_malformed_response_handling():
    """Test handling of malformed HTTP responses."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Mock client that returns invalid JSON
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.raise_for_status = MagicMock()
    mock_client.request.return_value = mock_response
    transport._client = mock_client
    
    test_message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "test",
        "method": "ping"
    })
    
    # Should get error response
    response = await transport._send_message(test_message)
    assert response.error is not None
    assert "Invalid JSON" in response.error["message"]

def test_transport_interface_compliance():
    """Test that HTTPTransport implements the Transport interface."""
    from chuk_mcp.transports.base import Transport, TransportParameters
    
    params = HTTPParameters(url="http://localhost:3000")
    transport = HTTPTransport(params)
    
    # Verify inheritance
    assert isinstance(transport, Transport)
    assert isinstance(params, TransportParameters)
    
    # Verify required methods exist
    assert hasattr(transport, 'get_streams')
    assert hasattr(transport, '__aenter__')
    assert hasattr(transport, '__aexit__')
    assert hasattr(transport, 'set_protocol_version')
    
    # Verify methods are callable
    assert callable(transport.get_streams)
    assert callable(transport.__aenter__)
    assert callable(transport.__aexit__)
    assert callable(transport.set_protocol_version)

def test_imports_work():
    """Test that HTTP transport imports work correctly."""
    from chuk_mcp.transports.http import HTTPTransport, HTTPParameters, http_client
    from chuk_mcp.transports.base import Transport, TransportParameters
    
    # Verify inheritance
    assert issubclass(HTTPTransport, Transport)
    assert issubclass(HTTPParameters, TransportParameters)
    
    # Verify exports
    assert HTTPTransport is not None
    assert HTTPParameters is not None
    assert http_client is not None

###############################################################################
# Performance and Resource Tests
###############################################################################

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling multiple concurrent requests."""
    transport = HTTPTransport(HTTPParameters(url="http://localhost:3000"))
    
    # Mock client that responds to each request
    mock_client = AsyncMock()
    
    def create_response(call_count):
        response = MagicMock()
        response.json.return_value = {
            "jsonrpc": "2.0",
            "id": f"req-{call_count}",
            "result": {"response": call_count}
        }
        response.raise_for_status = MagicMock()
        return response
    
    call_count = 0
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return create_response(call_count)
    
    mock_client.request = mock_request
    transport._client = mock_client
    
    # Send multiple messages
    messages = []
    for i in range(5):
        msg = JSONRPCMessage.model_validate({
            "jsonrpc": "2.0",
            "id": f"req-{i+1}",
            "method": "ping"
        })
        messages.append(msg)
    
    # Send all messages concurrently
    import anyio
    async with anyio.create_task_group() as tg:
        results = []
        for msg in messages:
            async def send_msg(message=msg):
                response = await transport._send_message(message)
                results.append(response)
            tg.start_soon(send_msg)
    
    # Verify all responses
    assert len(results) == 5
    for i, response in enumerate(results):
        assert response.result["response"] == i + 1

def test_resource_cleanup():
    """Test that resources are properly cleaned up."""
    params = HTTPParameters(url="http://localhost:3000")
    transport = HTTPTransport(params)
    
    # After creation, no resources should be allocated
    assert transport._client is None
    assert transport._incoming_send is None
    assert transport._outgoing_send is None