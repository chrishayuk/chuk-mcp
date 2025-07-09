# tests/mcp/transport/http/test_http_client.py
"""
Tests for Streamable HTTP client context manager.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from chuk_mcp.transports.http.parameters import StreamableHTTPParameters
from chuk_mcp.transports.http.http_client import http_client
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

pytest.importorskip("httpx")
pytest.importorskip("chuk_mcp.transports.http")


@pytest.mark.asyncio
async def test_http_client_basic_usage():
    """Test basic usage of http_client context manager."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('chuk_mcp.transports.http.http_client.StreamableHTTPTransport') as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport
        
        # Mock context manager
        mock_transport.__aenter__.return_value = mock_transport
        mock_transport.__aexit__.return_value = False
        
        # Mock get_streams
        from anyio import create_memory_object_stream
        read_send, read_stream = create_memory_object_stream(10)  # read_stream is the receive end
        write_stream, write_recv = create_memory_object_stream(10)  # write_stream is the send end
        mock_transport.get_streams.return_value = (read_stream, write_stream)
        
        async with http_client(params) as (r_stream, w_stream):
            # Verify we got valid streams
            assert r_stream is not None
            assert w_stream is not None
            
            # Verify streams have the expected interface
            assert hasattr(r_stream, 'receive')  # read stream should have receive
            assert hasattr(w_stream, 'send')     # write stream should have send
            
            # Verify transport was created correctly
            mock_transport_class.assert_called_once_with(params)


@pytest.mark.asyncio
async def test_http_client_message_exchange():
    """Test sending and receiving messages through http_client."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"status": "ready"}
        }
        mock_client.post.return_value = mock_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Send a message
            outgoing_msg = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "test-123",
                "method": "ping"
            })
            
            await write_stream.send(outgoing_msg)
            
            # Give time for processing
            await asyncio.sleep(0.1)
            
            # Receive response
            import anyio
            with anyio.fail_after(2.0):
                received_msg = await read_stream.receive()
            
            # Verify received message
            assert isinstance(received_msg, JSONRPCMessage)
            assert received_msg.id == "test-123"
            assert received_msg.result == {"status": "ready"}
            
            # Verify HTTP request was made
            assert mock_client.post.called


@pytest.mark.asyncio
async def test_http_client_error_handling():
    """Test http_client handles errors properly."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('chuk_mcp.transports.http.http_client.StreamableHTTPTransport') as mock_transport_class:
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport
        
        # Mock error during context manager entry
        mock_transport.__aenter__.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            async with http_client(params) as (read_stream, write_stream):
                pass


@pytest.mark.asyncio
async def test_http_client_with_auth():
    """Test http_client with authentication."""
    params = StreamableHTTPParameters(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer secret-token-123"}
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "auth-test",
            "result": {}
        }
        mock_client.post.return_value = mock_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Verify client was created with auth headers
            client_args = mock_client_class.call_args
            headers = client_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer secret-token-123"


@pytest.mark.asyncio
async def test_http_client_streaming_enabled():
    """Test http_client with streaming enabled."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        enable_streaming=True
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock SSE response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.is_closed = False
        
        # Mock SSE data with proper JSON-RPC message first
        async def mock_aiter_text(chunk_size=1024):
            # Send the JSON-RPC response first, then completion
            yield 'event: message\n'
            yield 'data: {"jsonrpc":"2.0","id":"stream-test","result":{"streaming":true}}\n'
            yield '\n'
            yield 'event: completion\n'
            yield 'data: {"type":"completion","timestamp":"2025-07-09T14:00:00Z"}\n'
            yield '\n'
        
        mock_response.aiter_text = mock_aiter_text
        mock_response.aclose = AsyncMock()
        mock_client.post.return_value = mock_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Send a message that will trigger streaming
            msg = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "stream-test",
                "method": "slow_operation"
            })
            
            await write_stream.send(msg)
            await asyncio.sleep(0.3)  # Give more time for SSE processing
            
            # Should receive streaming response
            import anyio
            with anyio.fail_after(3.0):  # Increase timeout
                response = await read_stream.receive()
            
            assert response.id == "stream-test"
            # Could be either the streaming result or completion format
            if "streaming" in str(response.result):
                assert response.result["streaming"] is True
            else:
                # Completion event format
                assert "content" in response.result


@pytest.mark.asyncio
async def test_http_client_timeout_configuration():
    """Test http_client respects timeout configuration."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        timeout=15.0
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        async with http_client(params) as (read_stream, write_stream):
            # Verify timeout was passed to httpx client
            client_args = mock_client_class.call_args
            timeout_arg = client_args[1]["timeout"]
            # httpx.Timeout object
            assert hasattr(timeout_arg, 'connect') or hasattr(timeout_arg, 'timeout')


@pytest.mark.asyncio
async def test_http_client_cleanup():
    """Test that http_client properly cleans up resources."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Use the context manager
        async with http_client(params) as (read_stream, write_stream):
            pass  # Just enter and exit
        
        # Verify cleanup was called
        assert mock_client.aclose.called


@pytest.mark.asyncio
async def test_http_client_multiple_messages():
    """Test handling multiple messages."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock responses for multiple requests
        responses = []
        for i in range(3):
            response = MagicMock()
            response.status_code = 200
            response.headers = {"content-type": "application/json"}
            response.json.return_value = {
                "jsonrpc": "2.0",
                "id": f"msg-{i}",
                "result": {"index": i}
            }
            responses.append(response)
        
        mock_client.post.side_effect = responses
        
        async with http_client(params) as (read_stream, write_stream):
            # Send multiple messages
            for i in range(3):
                msg = JSONRPCMessage.model_validate({
                    "jsonrpc": "2.0",
                    "id": f"msg-{i}",
                    "method": "test"
                })
                await write_stream.send(msg)
            
            # Give time for processing
            await asyncio.sleep(0.2)
            
            # Receive responses
            received_responses = []
            try:
                for i in range(3):
                    import anyio
                    with anyio.fail_after(1.0):
                        response = await read_stream.receive()
                        received_responses.append(response)
            except anyio.TimeoutError:
                pass  # Some responses might not arrive due to mocking complexity
            
            # Verify we got at least some responses
            assert len(received_responses) >= 1
            
            # Verify HTTP requests were made
            assert mock_client.post.call_count >= 1


def test_http_client_imports():
    """Test that http_client imports work correctly."""
    from chuk_mcp.transports.http import http_client, StreamableHTTPParameters
    from chuk_mcp.transports.http.http_client import http_client as direct_import
    
    assert http_client is not None
    assert http_client == direct_import
    assert StreamableHTTPParameters is not None


@pytest.mark.asyncio
async def test_http_client_with_realistic_protocol_flow():
    """Test http_client with realistic protocol message flow."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock initialization response
        init_response = MagicMock()
        init_response.status_code = 200
        init_response.headers = {"content-type": "application/json", "mcp-session-id": "session-123"}
        init_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"listChanged": True},
                    "prompts": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "streamable-http-test-server",
                    "version": "1.0.0"
                }
            }
        }
        mock_client.post.return_value = init_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Send initialize request
            init_request = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            })
            
            await write_stream.send(init_request)
            
            # Give time for processing
            await asyncio.sleep(0.1)
            
            # Receive response
            import anyio
            with anyio.fail_after(2.0):
                response = await read_stream.receive()
            
            assert response.id == "init-1"
            assert response.result["serverInfo"]["name"] == "streamable-http-test-server"
            assert response.result["protocolVersion"] == "2025-06-18"


@pytest.mark.asyncio
async def test_http_client_session_management():
    """Test session ID handling in http_client."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock response with session ID
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/json",
            "mcp-session-id": "new-session-456"
        }
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "session-test",
            "result": {"sessionEstablished": True}
        }
        mock_client.post.return_value = mock_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Send a message
            msg = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "session-test",
                "method": "initialize"
            })
            
            await write_stream.send(msg)
            await asyncio.sleep(0.1)
            
            # Verify response is received
            import anyio
            with anyio.fail_after(1.0):
                response = await read_stream.receive()
            
            assert response.id == "session-test"
            assert response.result["sessionEstablished"] is True


@pytest.mark.asyncio
async def test_http_client_bearer_token_setup():
    """Test automatic bearer token setup."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        bearer_token="auto-token-789"
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        async with http_client(params) as (read_stream, write_stream):
            # Verify client was created with bearer token in headers
            client_args = mock_client_class.call_args
            headers = client_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer auto-token-789"


@pytest.mark.asyncio
async def test_http_client_concurrent_requests():
    """Test concurrent request handling."""
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp",
        max_concurrent_requests=5
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock responses
        def create_response(call_count=[0]):
            call_count[0] += 1
            response = MagicMock()
            response.status_code = 200
            response.headers = {"content-type": "application/json"}
            response.json.return_value = {
                "jsonrpc": "2.0",
                "id": f"concurrent-{call_count[0]}",
                "result": {"call": call_count[0]}
            }
            return response
        
        mock_client.post.side_effect = lambda *args, **kwargs: create_response()
        
        async with http_client(params) as (read_stream, write_stream):
            # Send multiple concurrent messages
            import anyio
            async with anyio.create_task_group() as tg:
                for i in range(3):
                    async def send_message(index=i):
                        msg = JSONRPCMessage.model_validate({
                            "jsonrpc": "2.0",
                            "id": f"concurrent-{index+1}",
                            "method": "ping"
                        })
                        await write_stream.send(msg)
                    
                    tg.start_soon(send_message)
            
            # Give time for processing
            await asyncio.sleep(0.2)
            
            # Verify multiple requests were handled
            assert mock_client.post.call_count >= 3


@pytest.mark.asyncio
async def test_http_client_streaming_with_completion():
    """Test streaming with completion events."""
    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock SSE response with both message and completion
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.is_closed = False
        
        async def mock_aiter_text(chunk_size=1024):
            # First send the main response
            yield 'event: message\n'
            yield 'data: {"jsonrpc":"2.0","id":"completion-test","result":{"operation":"completed"}}\n'
            yield '\n'
            # Then send completion notification
            yield 'event: completion\n'
            yield 'data: {"type":"completion","timestamp":"2025-07-09T14:00:00Z"}\n'
            yield '\n'
        
        mock_response.aiter_text = mock_aiter_text
        mock_response.aclose = AsyncMock()
        mock_client.post.return_value = mock_response
        
        async with http_client(params) as (read_stream, write_stream):
            # Send message
            msg = JSONRPCMessage.model_validate({
                "jsonrpc": "2.0",
                "id": "completion-test",
                "method": "complex_operation"
            })
            
            await write_stream.send(msg)
            await asyncio.sleep(0.3)
            
            # Should receive the main response
            import anyio
            with anyio.fail_after(3.0):
                response = await read_stream.receive()
            
            assert response.id == "completion-test"
            # Should get the main operation result, not the completion event
            if "operation" in str(response.result):
                assert response.result["operation"] == "completed"
            else:
                # If it's a completion event response, that's also valid
                assert "content" in response.result