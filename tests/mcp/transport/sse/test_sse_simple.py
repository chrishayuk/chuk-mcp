# tests/mcp/transport/sse/test_sse_simple.py
"""
Tests for SSE transport implementation - Fixed for isinstance issues.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from chuk_mcp.transports.sse.parameters import SSEParameters
from chuk_mcp.transports.sse.transport import SSETransport
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage


def assert_is_jsonrpc_message(obj, expected_values=None):
    """Helper function to test if object is a JSONRPCMessage with expected values."""
    # Check structure
    assert hasattr(obj, 'jsonrpc'), f"Missing jsonrpc field, got: {type(obj)}"
    assert obj.jsonrpc == "2.0", f"Wrong jsonrpc version: {obj.jsonrpc}"
    
    # Check it's the right type by name (more reliable than isinstance)
    assert type(obj).__name__ == "JSONRPCMessage", f"Wrong type: {type(obj)}"
    
    # Check expected values if provided
    if expected_values:
        for key, value in expected_values.items():
            assert hasattr(obj, key), f"Missing field {key}"
            actual_value = getattr(obj, key)
            assert actual_value == value, f"Wrong {key}: {actual_value} != {value}"


@pytest.mark.asyncio
async def test_handle_incoming_message():
    """Test handling incoming messages."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Set up streams manually for testing
    from anyio import create_memory_object_stream
    transport._incoming_send, transport._incoming_recv = create_memory_object_stream(10)
    
    # Test valid message
    message_data = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"status": "ok"}
    }
    
    # Updated: Use the correct method name
    await transport._route_incoming_message(message_data)
    
    # Verify message was routed
    received = await transport._incoming_recv.receive()
    
    # FIXED: Use helper function instead of isinstance
    assert_is_jsonrpc_message(received, {
        "id": "test-123",
        "result": {"status": "ok"}
    })


@pytest.mark.asyncio
async def test_realistic_message_flow():
    """Test a realistic message flow with minimal mocking."""
    params = SSEParameters(url="http://localhost:3000", timeout=1.0)
    transport = SSETransport(params)
    
    # Manually set up the transport state (bypass SSE connection)
    transport._message_url = "http://localhost:3000/mcp"
    transport._session_id = "test-session"
    transport._connected.set()  # Mark as connected
    
    # Set up streams
    from anyio import create_memory_object_stream
    transport._incoming_send, transport._incoming_recv = create_memory_object_stream(10)
    transport._outgoing_send, transport._outgoing_recv = create_memory_object_stream(10)
    
    # Mock HTTP client - use _send_client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test-outgoing",
        "result": {"tools": []}
    }
    mock_client.post.return_value = mock_response
    transport._send_client = mock_client
    
    # Get streams
    read_stream, write_stream = transport._incoming_recv, transport._outgoing_send
    
    # Start the outgoing handler
    outgoing_task = asyncio.create_task(transport._outgoing_message_handler())
    
    try:
        # Test sending a message
        outgoing_message = JSONRPCMessage.model_validate({
            "jsonrpc": "2.0",
            "id": "test-outgoing",
            "method": "tools/list"
        })
        
        await write_stream.send(outgoing_message)
        
        # Give the handler time to process
        await asyncio.sleep(0.1)
        
        # Should have called HTTP post
        assert mock_client.post.called
        
        # The response from the mock should have been routed to incoming
        # (because it's an immediate HTTP 200 response)
        received_response = await read_stream.receive()
        
        # FIXED: Use helper function instead of isinstance
        assert_is_jsonrpc_message(received_response, {
            "id": "test-outgoing",
            "result": {"tools": []}
        })
        
    finally:
        outgoing_task.cancel()
        try:
            await outgoing_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_handle_message_event():
    """Test handling message event from SSE."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Set up incoming stream
    from anyio import create_memory_object_stream
    transport._incoming_send, transport._incoming_recv = create_memory_object_stream(10)
    
    # Test handling a response to a pending request
    transport._pending_requests["test-123"] = asyncio.Future()
    
    message_json = json.dumps({
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"status": "ok"}
    })
    
    await transport._handle_message_event(message_json)
    
    # Should have resolved the future
    assert "test-123" not in transport._pending_requests
    
    # Test handling a server-initiated message
    server_message = json.dumps({
        "jsonrpc": "2.0",
        "method": "notification",
        "params": {"data": "test"}
    })
    
    await transport._handle_message_event(server_message)
    
    # Should be routed to incoming stream
    received = await transport._incoming_recv.receive()
    
    # FIXED: Use helper function instead of isinstance
    assert_is_jsonrpc_message(received, {
        "method": "notification",
        "params": {"data": "test"}
    })


@pytest.mark.asyncio
async def test_send_message_timeout():
    """Test message timeout handling."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000", timeout=0.1))
    transport._message_url = "http://localhost:3000/mcp"
    
    # Set up streams
    from anyio import create_memory_object_stream
    transport._incoming_send, transport._incoming_recv = create_memory_object_stream(10)
    
    # Mock HTTP client that returns 202 (async response expected)
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client.post.return_value = mock_response
    transport._send_client = mock_client
    
    # Send a message that will timeout
    message = JSONRPCMessage.model_validate({
        "jsonrpc": "2.0",
        "id": "timeout-test",
        "method": "slow-operation"
    })
    
    # Don't set up any SSE response - let it timeout
    await transport._send_message_via_http(message)
    
    # Should have sent timeout error to incoming stream
    received = await transport._incoming_recv.receive()
    
    # FIXED: Use helper function instead of isinstance
    assert_is_jsonrpc_message(received, {
        "id": "timeout-test",
        "error": {"code": -32000, "message": "Request timeout"}
    })


@pytest.mark.asyncio
async def test_sse_connection_with_auth():
    """Test SSE connection with authentication."""
    params = SSEParameters(
        url="http://localhost:3000",
        bearer_token="test-token-123"
    )
    
    transport = SSETransport(params)
    
    # Verify auth headers are set up correctly
    headers = transport._get_headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-token-123"


@pytest.mark.asyncio
async def test_sse_cleanup():
    """Test SSE transport cleanup."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Test cleanup without initialization
    await transport._cleanup()
    
    # Should not raise any errors
    assert True


@pytest.mark.asyncio
async def test_sse_endpoint_event():
    """Test handling endpoint event."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Test endpoint event handling
    await transport._handle_endpoint_event("/messages/?session_id=test123")
    
    # Should set message URL and session ID
    assert transport._message_url == "http://localhost:3000/messages/?session_id=test123"
    assert transport._session_id == "test123"


@pytest.mark.asyncio
async def test_sse_is_connected():
    """Test connection status checking."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Initially not connected
    assert not transport.is_connected()
    
    # Set connected state manually
    transport._connected.set()
    transport._message_url = "http://localhost:3000/mcp"
    
    # Now should be connected
    assert transport.is_connected()


def test_sse_transport_repr():
    """Test string representation."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    repr_str = repr(transport)
    assert "SSETransport" in repr_str
    assert "http://localhost:3000" in repr_str
    assert "disconnected" in repr_str


@pytest.mark.asyncio
async def test_sse_message_lock():
    """Test message locking mechanism."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Test that message lock exists and can be acquired
    async with transport._message_lock:
        # Should be able to acquire the lock
        assert True


@pytest.mark.asyncio 
async def test_sse_process_stream():
    """Test SSE stream processing."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Set up connected state manually
    transport._connected.set()
    
    # Test empty stream processing (shouldn't crash)
    # This is a minimal test since we can't easily mock the SSE stream
    assert transport._connected.is_set()


def test_sse_parameters_validation():
    """Test SSE parameters validation."""
    # Valid parameters
    params = SSEParameters(url="http://localhost:3000")
    assert params.url == "http://localhost:3000"
    
    # Test with bearer token
    params = SSEParameters(
        url="http://localhost:3000",
        bearer_token="test-token"
    )
    assert params.headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_sse_notification_handling():
    """Test handling of notifications (messages without IDs)."""
    transport = SSETransport(SSEParameters(url="http://localhost:3000"))
    
    # Set up streams
    from anyio import create_memory_object_stream
    transport._incoming_send, transport._incoming_recv = create_memory_object_stream(10)
    
    # Test notification message
    notification_json = json.dumps({
        "jsonrpc": "2.0",
        "method": "server/notification",
        "params": {"type": "info", "message": "Server status update"}
    })
    
    await transport._handle_message_event(notification_json)
    
    # Should be routed to incoming stream
    received = await transport._incoming_recv.receive()
    
    # FIXED: Use helper function instead of isinstance
    assert_is_jsonrpc_message(received, {
        "method": "server/notification",
        "params": {"type": "info", "message": "Server status update"}
    })
    # Notifications should have id=None
    assert received.id is None


def test_sse_imports():
    """Test that SSE imports work correctly."""
    from chuk_mcp.transports.sse import SSETransport, SSEParameters, sse_client
    
    assert SSETransport is not None
    assert SSEParameters is not None 
    assert sse_client is not None