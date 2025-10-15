#!/usr/bin/env python3
"""
Proper SSE Transport Test

This test uses the actual SSE transport instead of trying to manually
debug the protocol. It should work with your async SSE server.
"""

import asyncio
import logging
import sys

import anyio

# chuk-mcp imports
from chuk_mcp.transports.sse import sse_client, SSEParameters
from chuk_mcp.protocol.messages import send_initialize, send_ping

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_sse_transport():
    """Test the actual SSE transport implementation."""
    print("🌊 Testing SSE Transport Implementation")
    print("=" * 50)

    # Configure SSE parameters
    sse_params = SSEParameters(
        url="http://localhost:8000",
        timeout=30.0,  # Give it time for async responses
    )

    print(f"📡 Connecting to SSE server: {sse_params.url}")

    try:
        # Use the actual transport - this should handle everything correctly
        async with sse_client(sse_params) as (read_stream, write_stream):
            print("✅ SSE transport connection successful!")

            # Test 1: Initialize
            print("\n1️⃣ Testing initialization...")
            try:
                # Add timeout to avoid hanging forever
                init_result = await asyncio.wait_for(
                    send_initialize(read_stream, write_stream), timeout=20.0
                )
                print("✅ Initialization successful!")
                print(f"   Server: {init_result.serverInfo.name}")
                print(f"   Version: {init_result.serverInfo.version}")
                print(f"   Protocol: {init_result.protocolVersion}")

            except asyncio.TimeoutError:
                print("❌ Initialization timed out after 20 seconds")
                print(
                    "   This suggests the server isn't sending responses back via SSE"
                )
                return False
            except Exception as e:
                print(f"❌ Initialization failed: {e}")
                return False

            # Test 2: Ping
            print("\n2️⃣ Testing ping...")
            try:
                ping_result = await asyncio.wait_for(
                    send_ping(read_stream, write_stream), timeout=10.0
                )
                print(f"✅ Ping: {'Success' if ping_result else 'Failed'}")

            except asyncio.TimeoutError:
                print("❌ Ping timed out after 10 seconds")
                return False
            except Exception as e:
                print(f"❌ Ping failed: {e}")
                return False

            print("\n🎉 SSE transport test completed successfully!")
            return True

    except Exception as e:
        print(f"❌ SSE transport connection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_with_detailed_logging():
    """Test with very detailed logging to see exactly what's happening."""
    print("\n🔍 Testing with detailed logging...")
    print("=" * 50)

    # Enable debug logging for our transport
    sse_logger = logging.getLogger("chuk_mcp.transports.sse")
    sse_logger.setLevel(logging.DEBUG)

    # Also enable debug for httpx to see HTTP traffic
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.INFO)

    return await test_sse_transport()


def main():
    """Run the SSE transport tests."""
    print("🧪 SSE Transport Integration Test")
    print("=" * 60)
    print("This test verifies that the SSE transport correctly handles")
    print("async responses from your SSE server.")
    print("=" * 60)

    try:
        # Run the test
        success = anyio.run(test_with_detailed_logging)

        if success:
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! SSE transport is working correctly!")
            print("✅ The transport properly handles async SSE responses")
            print("✅ Your server implementation is compatible")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ TEST FAILED")
            print("💡 Possible issues:")
            print("   1. Server not sending responses back via SSE")
            print("   2. Response format not matching expected JSON-RPC")
            print("   3. Session ID mismatch between request and response")
            print("=" * 60)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
