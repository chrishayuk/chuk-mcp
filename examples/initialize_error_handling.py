#!/usr/bin/env python3
"""
Example: Proper Exception Handling with send_initialize()

This example demonstrates the correct way to handle errors when initializing
an MCP connection, including OAuth re-authentication scenarios.

Key Points:
1. send_initialize() raises exceptions (doesn't return None)
2. Always use try/except for error handling
3. Catch specific exceptions for different scenarios
4. OAuth 401 errors are RetryableError - trigger re-authentication
"""

import asyncio
import anyio
import logging

from chuk_mcp.protocol.types.errors import (
    RetryableError,
    NonRetryableError,
    VersionMismatchError,
)
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.initialize.send_messages import send_initialize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_successful_initialization():
    """Example: Successful MCP initialization."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Successful Initialization")
    print("=" * 70)

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def mock_server():
        """Simulate a server that responds successfully."""
        try:
            req = await write_receive.receive()
            logger.info(
                f"Server received initialize request for version {req.params.get('protocolVersion')}"
            )

            response = JSONRPCMessage(
                id=req.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"logging": {}, "tools": {}},
                    "serverInfo": {"name": "ExampleServer", "version": "1.0.0"},
                },
            )
            await read_send.send(response)

            # Consume initialized notification
            notification = await write_receive.receive()
            logger.info(f"Server received notification: {notification.method}")
        except Exception as e:
            logger.error(f"Server error: {e}")

    # Start server in background
    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        try:
            # Client initialization
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=5.0,
            )

            # Success: result is guaranteed to be InitializeResult (not None)
            print("✅ Initialization successful!")
            print(f"   Protocol Version: {result.protocolVersion}")
            print(f"   Server: {result.serverInfo.name} v{result.serverInfo.version}")
            print(f"   Capabilities: {list(result.capabilities.model_dump().keys())}")

        except Exception as e:
            print(f"❌ Initialization failed: {e}")


async def example_oauth_401_error():
    """Example: Handling OAuth 401 errors (expired tokens)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: OAuth 401 Error (Expired Token)")
    print("=" * 70)

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def mock_server():
        """Simulate a server that rejects with 401."""
        try:
            req = await write_receive.receive()
            logger.info("Server received initialize request with invalid token")

            # Simulate OAuth 401 error
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message='HTTP 401: {"error":"invalid_token","error_description":"Token expired"}',
            )
            await read_send.send(response)
        except Exception:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        try:
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=5.0,
            )
            print(f"❌ ERROR: Should have raised exception, got result: {result}")

        except (RetryableError, NonRetryableError, Exception) as e:
            # Check if this is an OAuth error
            error_msg = str(e).lower()
            is_oauth_error = any(
                pattern in error_msg
                for pattern in ["401", "invalid_token", "unauthorized", "token expired"]
            )

            if is_oauth_error:
                print("🔐 OAuth authentication error detected!")
                print(f"   Error: {e}")
                print(
                    "\n   ➡️  Action: Clear invalid tokens and trigger OAuth re-authentication"
                )
                print("   1. Delete stored tokens")
                print("   2. Delete client registration")
                print("   3. Open browser for OAuth flow")
                print("   4. Retry with fresh tokens")
            else:
                print(f"❌ Non-OAuth error: {e}")


async def example_version_mismatch():
    """Example: Handling version mismatch errors."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Version Mismatch Error")
    print("=" * 70)

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def mock_server():
        """Simulate a server with unsupported version."""
        try:
            req = await write_receive.receive()
            logger.info("Server received initialize with incompatible version")

            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32602,  # Invalid params
                message="Unsupported protocol version",
            )
            await read_send.send(response)
        except Exception:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        try:
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=5.0,
            )
            print(f"❌ ERROR: Should have raised exception, got result: {result}")

        except VersionMismatchError as e:
            print("⚠️  Version mismatch detected!")
            print(f"   Error: {e}")
            print("\n   ➡️  Action: Disconnect and inform user")
            print("   - Client and server have incompatible protocol versions")
            print("   - Update client or server to compatible version")

        except Exception as e:
            print(f"❌ Unexpected error: {e}")


async def example_timeout():
    """Example: Handling timeout errors."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Timeout Error")
    print("=" * 70)

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def mock_server():
        """Simulate a server that doesn't respond."""
        try:
            _req = await write_receive.receive()
            logger.info("Server received request but not responding...")
            # Don't send response - let it timeout
            await anyio.sleep(10.0)
        except Exception:
            pass  # Expected to be cancelled

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        try:
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=1.0,  # Short timeout
            )
            print(f"❌ ERROR: Should have raised exception, got result: {result}")

        except TimeoutError:
            print("⏱️  Timeout error detected!")
            print("   Error: Server didn't respond within 1.0 seconds")
            print("\n   ➡️  Action: Retry with longer timeout or check server status")
            print("   - Server may be overloaded")
            print("   - Network connectivity issues")
            print("   - Server may be down")


async def example_comprehensive_error_handling():
    """Example: Comprehensive error handling pattern."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Comprehensive Error Handling Pattern")
    print("=" * 70)

    read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
    write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    async def mock_server():
        """Simulate OAuth error."""
        try:
            req = await write_receive.receive()
            response = JSONRPCMessage.create_error_response(
                id=req.id,
                code=-32603,
                message='HTTP 401: {"error":"invalid_token"}',
            )
            await read_send.send(response)
        except Exception:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(mock_server)

        try:
            # Try initialization
            result = await send_initialize(
                read_stream=read_receive,
                write_stream=write_send,
                timeout=5.0,
            )

            # Success
            print(f"✅ Connected to {result.serverInfo.name}")
            return result

        except VersionMismatchError as e:
            # Version incompatibility - cannot recover
            print(f"❌ FATAL: Version mismatch - {e}")
            print("   → Disconnect and inform user")
            raise

        except TimeoutError:
            # Timeout - might be temporary
            print("⏱️  TIMEOUT: Server not responding")
            print("   → Retry with exponential backoff")
            raise

        except (RetryableError, NonRetryableError, Exception) as e:
            # Check for OAuth errors
            error_msg = str(e).lower()

            if any(p in error_msg for p in ["401", "invalid_token", "unauthorized"]):
                # OAuth error - can recover with re-authentication
                print("🔐 OAuth authentication failed")
                print("   → Clearing tokens and triggering re-authentication...")

                # In real code, you would:
                # 1. Clear stored tokens
                # 2. Delete client registration
                # 3. Trigger OAuth flow
                # 4. Retry initialization

                print("   → [Simulated] Re-authentication complete")
                print("   → Retry initialization with fresh tokens")

            else:
                # Other error - might not be recoverable
                print(f"❌ ERROR: {e}")
                print("   → Log error and disconnect")
                raise


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MCP Initialization Error Handling Examples")
    print("=" * 70)
    print("\nThese examples demonstrate the NEW behavior where send_initialize()")
    print("raises exceptions instead of returning None on errors.")
    print("\nThis enables:")
    print("  1. Automatic OAuth re-authentication")
    print("  2. Proper error recovery")
    print("  3. Better debugging with stack traces")
    print("  4. Type-safe code (no Optional checks)")

    # Run examples
    await example_successful_initialization()
    await example_oauth_401_error()
    await example_version_mismatch()
    await example_timeout()
    await example_comprehensive_error_handling()

    print("\n" + "=" * 70)
    print("Examples Complete")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  ✓ Always use try/except, never check for None")
    print("  ✓ Catch specific exceptions for different scenarios")
    print("  ✓ OAuth 401 errors can be recovered with re-authentication")
    print("  ✓ Exceptions contain full context for debugging")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
