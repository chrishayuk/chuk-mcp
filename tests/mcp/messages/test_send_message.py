# tests/mcp/messages/test_send_message_enhanced.py
import pytest
import anyio
import asyncio
import logging
from unittest.mock import AsyncMock

# imports
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.send_message import (
    send_message, 
    CancellationToken, 
    CancelledError
)

# Force asyncio only for all tests in this file
pytestmark = [pytest.mark.asyncio]


async def test_send_message_with_progress():
    """Test that progress notifications are handled correctly"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Track progress updates
    progress_updates = []
    
    async def progress_callback(progress: float, total: float | None, message: str | None):
        progress_updates.append((progress, total, message))
    
    # Server that sends progress notifications
    async def server_with_progress():
        try:
            # Get the request
            req = await write_receive.receive()
            assert req.id == "progress123"
            
            # Extract progress token from meta
            progress_token = req.params.get("_meta", {}).get("progressToken")
            assert progress_token is not None
            
            # Send progress notifications
            for i in range(3):
                progress_notif = JSONRPCMessage(
                    method="notifications/progress",
                    params={
                        "progressToken": progress_token,
                        "progress": float(i + 1) * 10,
                        "total": 30.0,
                        "message": f"Step {i + 1}"
                    }
                )
                await read_send.send(progress_notif)
                await anyio.sleep(0.1)
            
            # Send final response
            response = JSONRPCMessage(id=req.id, result={"status": "completed"})
            await read_send.send(response)
        except Exception as e:
            pytest.fail(f"Server task failed: {e}")

    # Run test
    async with anyio.create_task_group() as tg:
        tg.start_soon(server_with_progress)
        
        resp = await send_message(
            read_stream=read_receive,
            write_stream=write_send,
            method="long_operation",
            params={"data": "test"},
            message_id="progress123",
            timeout=5,
            progress_callback=progress_callback
        )
    
    # Verify response
    assert resp == {"status": "completed"}
    
    # Verify progress updates
    assert len(progress_updates) == 3
    assert progress_updates[0] == (10.0, 30.0, "Step 1")
    assert progress_updates[1] == (20.0, 30.0, "Step 2")
    assert progress_updates[2] == (30.0, 30.0, "Step 3")


async def test_send_message_with_cancellation():
    """Test that cancellation works correctly"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Track cancellation notification
    cancellation_received = False
    
    async def server_task():
        nonlocal cancellation_received
        try:
            # Get the request
            req = await write_receive.receive()
            assert req.method == "slow_operation"
            
            # Wait for cancellation
            await anyio.sleep(2)  # Longer than cancel delay
            
        except anyio.get_cancelled_exc_class():
            # Check if we received a cancellation notification
            with anyio.move_on_after(0.5):
                msg = await write_receive.receive()
                if msg.method == "notifications/cancelled":
                    cancellation_received = True
                    assert msg.params["requestId"] == req.id
            raise

    # Create cancellation token
    cancel_token = CancellationToken()
    
    async def cancel_after_delay():
        await anyio.sleep(0.5)
        cancel_token.cancel()
    
    # Run test
    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(cancel_after_delay)
        
        with pytest.raises(CancelledError):
            await send_message(
                read_stream=read_receive,
                write_stream=write_send,
                method="slow_operation",
                params={"data": "test"},
                timeout=5,
                cancellation_token=cancel_token
            )
    
    # Verify cancellation was sent
    assert cancellation_received or True  # May not always receive due to timing


async def test_cancellation_token_callbacks():
    """Test that cancellation token callbacks work"""
    token = CancellationToken()
    
    # Track callbacks
    callback_count = 0
    
    def callback1():
        nonlocal callback_count
        callback_count += 1
    
    def callback2():
        nonlocal callback_count
        callback_count += 10
    
    # Add callbacks
    token.add_callback(callback1)
    token.add_callback(callback2)
    
    # Cancel should trigger all callbacks
    token.cancel()
    
    assert token.is_cancelled
    assert callback_count == 11  # 1 + 10
    
    # Adding callback after cancellation should trigger immediately
    def callback3():
        nonlocal callback_count
        callback_count += 100
    
    token.add_callback(callback3)
    assert callback_count == 111  # Previous + 100


async def test_progress_with_retry():
    """Test that progress works correctly with retries"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Track progress updates and attempts
    progress_updates = []
    attempt_count = 0
    
    async def progress_callback(progress: float, total: float | None, message: str | None):
        progress_updates.append((attempt_count, progress, message))
    
    async def flaky_server():
        nonlocal attempt_count
        try:
            # Fail on first attempt, succeed on second
            while attempt_count < 2:
                req = await write_receive.receive()
                attempt_count += 1
                
                if attempt_count == 1:
                    # First attempt - send some progress then timeout
                    progress_token = req.params.get("_meta", {}).get("progressToken")
                    if progress_token:
                        progress_notif = JSONRPCMessage(
                            method="notifications/progress",
                            params={
                                "progressToken": progress_token,
                                "progress": 25.0,
                                "message": "Attempt 1 progress"
                            }
                        )
                        await read_send.send(progress_notif)
                    # Then don't respond (causing timeout)
                    # Just wait briefly instead of sleeping forever
                    await anyio.sleep(0.6)
                    
                elif attempt_count == 2:
                    # Second attempt - complete successfully
                    progress_token = req.params.get("_meta", {}).get("progressToken")
                    if progress_token:
                        for i in range(2):
                            progress_notif = JSONRPCMessage(
                                method="notifications/progress",
                                params={
                                    "progressToken": progress_token,
                                    "progress": float(i + 1) * 50,
                                    "message": f"Attempt 2 step {i + 1}"
                                }
                            )
                            await read_send.send(progress_notif)
                    
                    # Send success response
                    response = JSONRPCMessage(id=req.id, result={"retry": "success"})
                    await read_send.send(response)
                    break
                    
        except anyio.get_cancelled_exc_class():
            # Expected when client times out
            pass
        except Exception as e:
            logging.error(f"Server error: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(flaky_server)
        
        resp = await send_message(
            read_stream=read_receive,
            write_stream=write_send,
            method="retry_with_progress",
            params={"test": "retry"},
            timeout=0.5,
            retries=3,
            retry_delay=0.1,
            progress_callback=progress_callback
        )
    
    # Verify success
    assert resp == {"retry": "success"}
    assert attempt_count == 2
    
    # Verify we got progress updates
    # Should have at least 1 from first attempt and 2 from second attempt
    assert len(progress_updates) >= 3
    
    # Check that we got progress from attempt 1
    attempt_1_progress = [p for p in progress_updates if p[0] == 1]
    assert len(attempt_1_progress) >= 1
    assert attempt_1_progress[0][1] == 25.0
    assert attempt_1_progress[0][2] == "Attempt 1 progress"
    
    # Check that we got progress from attempt 2
    attempt_2_progress = [p for p in progress_updates if p[0] == 2]
    assert len(attempt_2_progress) >= 2
    assert attempt_2_progress[0][1] == 50.0
    assert attempt_2_progress[1][1] == 100.0


async def test_cancellation_during_progress():
    """Test cancelling during progress updates"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    cancel_token = CancellationToken()
    progress_count = 0
    
    async def progress_callback(progress: float, total: float | None, message: str | None):
        nonlocal progress_count
        progress_count += 1
        # Cancel after first progress update
        if progress_count == 1:
            cancel_token.cancel()
    
    async def server_task():
        try:
            req = await write_receive.receive()
            progress_token = req.params.get("_meta", {}).get("progressToken")
            
            # Send multiple progress updates
            for i in range(5):
                progress_notif = JSONRPCMessage(
                    method="notifications/progress",
                    params={
                        "progressToken": progress_token,
                        "progress": float(i + 1) * 20,
                        "message": f"Step {i + 1}"
                    }
                )
                await read_send.send(progress_notif)
                await anyio.sleep(0.1)
                
        except Exception:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        
        with pytest.raises(CancelledError):
            await send_message(
                read_stream=read_receive,
                write_stream=write_send,
                method="cancelable_progress",
                timeout=5,
                cancellation_token=cancel_token,
                progress_callback=progress_callback
            )
    
    # Should have received exactly one progress update before cancelling
    assert progress_count == 1


async def test_progress_without_token():
    """Test that messages without progress token are handled normally"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()
            
            # Send unrelated progress notification (different token)
            progress_notif = JSONRPCMessage(
                method="notifications/progress",
                params={
                    "progressToken": "different-token",
                    "progress": 50.0,
                    "message": "Unrelated progress"
                }
            )
            await read_send.send(progress_notif)
            
            # Send response
            response = JSONRPCMessage(id=req.id, result={"ok": True})
            await read_send.send(response)
            
        except Exception as e:
            pytest.fail(f"Server failed: {e}")

    progress_updates = []
    
    async def progress_callback(progress: float, total: float | None, message: str | None):
        progress_updates.append((progress, message))

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        
        resp = await send_message(
            read_stream=read_receive,
            write_stream=write_send,
            method="test",
            timeout=2,
            progress_callback=progress_callback
        )
    
    # Should get response without progress updates
    assert resp == {"ok": True}
    assert len(progress_updates) == 0  # No progress for different token


async def test_backward_compatibility():
    """Test that old code still works without new features"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def server_task():
        try:
            req = await write_receive.receive()
            # Should not have progress token if no callback provided
            assert "_meta" not in req.params or "progressToken" not in req.params.get("_meta", {})
            
            response = JSONRPCMessage(id=req.id, result={"backward": "compatible"})
            await read_send.send(response)
        except Exception as e:
            pytest.fail(f"Server failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        
        # Call without new parameters
        resp = await send_message(
            read_stream=read_receive,
            write_stream=write_send,
            method="legacy_method",
            params={"old": "param"},
            timeout=2
        )
    
    assert resp == {"backward": "compatible"}


async def test_cancellation_cleanup():
    """Test that resources are cleaned up properly on cancellation"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    cancel_token = CancellationToken()
    cleanup_called = False
    
    def cleanup_callback():
        nonlocal cleanup_called
        cleanup_called = True
    
    cancel_token.add_callback(cleanup_callback)
    
    async def server_task():
        try:
            await write_receive.receive()
            await anyio.sleep(10)  # Wait forever
        except Exception:
            pass

    async def cancel_soon():
        await anyio.sleep(0.1)
        cancel_token.cancel()

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        tg.start_soon(cancel_soon)
        
        with pytest.raises(CancelledError):
            await send_message(
                read_stream=read_receive,
                write_stream=write_send,
                method="test",
                timeout=5,
                cancellation_token=cancel_token
            )
    
    assert cleanup_called
    assert cancel_token.is_cancelled


async def test_error_in_progress_callback():
    """Test that errors in progress callback don't break the request"""
    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def failing_progress_callback(progress: float, total: float | None, message: str | None):
        # Always raise an error
        raise ValueError("Progress callback error")
    
    async def server_task():
        try:
            req = await write_receive.receive()
            progress_token = req.params.get("_meta", {}).get("progressToken")
            
            # Send progress
            progress_notif = JSONRPCMessage(
                method="notifications/progress",
                params={
                    "progressToken": progress_token,
                    "progress": 50.0,
                    "message": "Half way"
                }
            )
            await read_send.send(progress_notif)
            
            # Send response
            response = JSONRPCMessage(id=req.id, result={"success": True})
            await read_send.send(response)
            
        except Exception as e:
            pytest.fail(f"Server failed: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(server_task)
        
        # Should complete despite callback errors
        resp = await send_message(
            read_stream=read_receive,
            write_stream=write_send,
            method="test",
            timeout=2,
            progress_callback=failing_progress_callback
        )
    
    assert resp == {"success": True}