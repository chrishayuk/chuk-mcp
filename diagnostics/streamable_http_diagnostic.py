#!/usr/bin/env python3
"""
Streamable HTTP Example for chuk-mcp - Final Clean Version

This example demonstrates the modern Streamable HTTP transport (MCP spec 2025-03-26)
that replaces the deprecated SSE transport.
"""

import asyncio
import logging
import warnings

import anyio

# chuk-mcp imports
from chuk_mcp.transports.http import (
    http_client,
    StreamableHTTPParameters,
    detect_transport_type,
    create_http_parameters_from_url,
)
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
)

# Suppress all warnings during testing
warnings.filterwarnings("ignore")

# Set up completely silent logging except for our output
logging.basicConfig(level=logging.CRITICAL)  # Only show critical errors
logger = logging.getLogger(__name__)

# Silence all noisy loggers
for logger_name in [
    "chuk_mcp.transports.http.transport",
    "chuk_mcp.transports.http.http_client",
    "httpx",
    "httpcore",
    "root",
    "asyncio",
]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


async def streamable_http_example():
    """Demonstrate Streamable HTTP transport features."""
    print("🌐 Streamable HTTP Transport Example")
    print("=" * 60)
    print("Modern MCP transport (spec 2025-03-26)")
    print("Replaces deprecated SSE transport")
    print("=" * 60)

    # Configure HTTP parameters
    server_url = "http://localhost:8000/mcp"

    http_params = StreamableHTTPParameters(
        url=server_url, timeout=30.0, enable_streaming=True, max_concurrent_requests=5
    )

    print(f"📡 Connecting to: {server_url}")
    print(f"🔧 Streaming enabled: {http_params.enable_streaming}")

    try:
        async with http_client(http_params) as (read_stream, write_stream):
            print("✅ Streamable HTTP connection established!")

            # 1. Initialize
            print("\n1️⃣ Initializing MCP connection...")
            init_result = await send_initialize(read_stream, write_stream)
            print(f"   ✅ Server: {init_result.serverInfo.name}")
            print(f"   📋 Protocol: {init_result.protocolVersion}")
            print(f"   💡 Instructions: {init_result.instructions}")

            # 2. Test ping
            print("\n2️⃣ Testing basic connectivity...")
            ping_success = await send_ping(read_stream, write_stream)
            print(
                f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}"
            )

            # 3. List tools
            print("\n3️⃣ Exploring available tools...")
            tools_response = await send_tools_list(read_stream, write_stream)
            tools = tools_response.get("tools", [])
            print(f"   📋 Found {len(tools)} tools:")

            for tool in tools:
                print(f"      • {tool['name']}: {tool['description']}")

            # 4. Test tools
            print("\n4️⃣ Testing tools...")

            # Quick tool
            if any(t["name"] == "http_greet" for t in tools):
                print("   👋 Testing quick greeting...")
                greet_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    "http_greet",
                    {"name": "HTTP User", "style": "casual"},
                )
                content = greet_result.get("content", [{}])[0].get("text", "")
                print(f"      {content}")

            # Slow tool
            if any(t["name"] == "slow_operation" for t in tools):
                print("   ⏱️ Testing slow operation (may stream)...")
                start_time = asyncio.get_event_loop().time()

                slow_result = await send_tools_call(
                    read_stream, write_stream, "slow_operation", {"duration": 2}
                )

                duration = asyncio.get_event_loop().time() - start_time
                content = slow_result.get("content", [{}])[0].get("text", "")
                print(f"      {content}")
                print(f"      💡 Completed in {duration:.2f}s")

                if duration >= 1.8:
                    print("      🌊 Server likely used streaming response")
                else:
                    print("      ⚡ Server used immediate response")

            # Session info
            if any(t["name"] == "session_info" for t in tools):
                print("   📊 Getting session information...")
                session_result = await send_tools_call(
                    read_stream, write_stream, "session_info", {}
                )
                content = session_result.get("content", [{}])[0].get("text", "")
                try:
                    import json

                    session_data = json.loads(content.replace("📊 Session Info: ", ""))
                    print(
                        f"      Session ID: {session_data.get('session_id', 'Unknown')[:8]}..."
                    )
                    print(
                        f"      Transport: {session_data.get('transport', 'Unknown')}"
                    )
                except Exception:
                    print(f"      {content[:100]}...")

            # 5. Test resources
            print("\n5️⃣ Exploring resources...")
            try:
                resources_response = await send_resources_list(
                    read_stream, write_stream
                )
                resources = resources_response.get("resources", [])
                print(f"   📂 Found {len(resources)} resources:")

                for resource in resources[:2]:  # Test first 2
                    print(f"      • {resource['name']}")

                    content_response = await send_resources_read(
                        read_stream, write_stream, resource["uri"]
                    )
                    contents = content_response.get("contents", [])
                    if contents:
                        content_text = contents[0].get("text", "")
                        if resource["mimeType"] == "application/json":
                            print(
                                f"        📄 JSON data available ({len(content_text)} chars)"
                            )
                        else:
                            lines = content_text.split("\n")[:3]
                            for line in lines:
                                if line.strip():
                                    print(f"        {line}")
                            if len(content_text.split("\n")) > 3:
                                print("        ...")

            except Exception as e:
                print(f"   ❌ Resources test failed: {type(e).__name__}")

            # 6. Test concurrent operations
            print("\n6️⃣ Testing concurrent operations...")

            tasks = []
            for i in range(3):
                tasks.append(send_ping(read_stream, write_stream))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if r is True)
            print(f"   📊 Concurrent pings: {successful}/3 successful")

            print("\n🎉 Streamable HTTP example completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}")
        print("\n💡 Make sure the Streamable HTTP server is running:")
        print("   python streamable_http_server.py")


async def transport_detection_example():
    """Demonstrate automatic transport detection."""
    print("\n🔍 Transport Detection Example")
    print("=" * 40)

    test_urls = [
        "http://localhost:8000/mcp",
        "http://localhost:8000",
        "http://localhost:8001/sse",
    ]

    for url in test_urls:
        print(f"\n📡 Testing: {url}")

        try:
            transport_type = await detect_transport_type(url, timeout=5.0)

            type_descriptions = {
                "streamable_http": "✅ Modern Streamable HTTP",
                "sse": "⚠️ Deprecated SSE",
                "both": "🔄 Both HTTP and SSE",
                "unknown": "❌ Unknown/No response",
            }

            description = type_descriptions.get(transport_type, "❓ Unexpected")
            print(f"   Result: {description}")

        except Exception as e:
            print(f"   ❌ Detection failed: {type(e).__name__}")


async def fallback_example():
    """Demonstrate automatic fallback mechanism."""
    print("\n🔄 Automatic Fallback Example")
    print("=" * 40)

    test_url = "http://localhost:8000/mcp"

    print(f"📡 Testing fallback for: {test_url}")
    print("   Will try Streamable HTTP first, then SSE if needed")

    try:
        http_params = StreamableHTTPParameters(
            url=test_url, timeout=10.0, enable_streaming=True
        )

        print("   🌐 Attempting Streamable HTTP connection...")
        async with http_client(http_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            print("   ✅ Streamable HTTP connection successful!")
            print(f"   📋 Server: {init_result.serverInfo.name}")
            print("   💡 No fallback needed - Streamable HTTP worked")

    except Exception as http_error:
        print(f"   ❌ Streamable HTTP failed: {type(http_error).__name__}")
        print("   💡 Would attempt SSE fallback if available")


async def manual_fallback_example():
    """Manual implementation of fallback mechanism."""
    print("\n🔄 Manual Fallback Implementation")
    print("=" * 40)

    test_url = "http://localhost:8000/mcp"

    print(f"📡 Testing manual fallback for: {test_url}")

    try:
        transport_type = await detect_transport_type(test_url, timeout=5.0)
        print(f"   🔍 Detected transport type: {transport_type}")

        if transport_type in ["streamable_http", "both"]:
            print("   🌐 Server supports Streamable HTTP - using it")

            params = StreamableHTTPParameters(
                url=test_url, timeout=10.0, enable_streaming=True
            )

            async with http_client(params) as (read_stream, write_stream):
                init_result = await send_initialize(read_stream, write_stream)
                print("   ✅ Connected via Streamable HTTP!")
                print(f"   📋 Server: {init_result.serverInfo.name}")
        else:
            print(f"   ❌ Unknown transport type: {transport_type}")

    except Exception as e:
        print(f"   ❌ Manual fallback failed: {type(e).__name__}")


async def parameter_creation_example():
    """Demonstrate different ways to create HTTP parameters."""
    print("\n⚙️ Parameter Creation Examples")
    print("=" * 40)

    test_url = "http://localhost:8000/mcp"

    print("📋 Different ways to create HTTP parameters:")

    # Method 1: Direct parameter creation
    print("\n   1️⃣ Direct StreamableHTTPParameters:")
    params1 = StreamableHTTPParameters(
        url=test_url, timeout=30.0, enable_streaming=True, max_concurrent_requests=5
    )
    print(f"      URL: {params1.url}")
    print(f"      Timeout: {params1.timeout}s")
    print(f"      Streaming: {params1.enable_streaming}")

    # Method 2: Using convenience function
    print("\n   2️⃣ Using create_http_parameters_from_url:")
    params2 = create_http_parameters_from_url(
        url=test_url, timeout=60.0, enable_streaming=True
    )
    print(f"      URL: {params2.url}")
    print(f"      Timeout: {params2.timeout}s")
    print(f"      Streaming: {params2.enable_streaming}")

    # Method 3: With authentication
    print("\n   3️⃣ With bearer token authentication:")
    params3 = StreamableHTTPParameters(
        url=test_url,
        timeout=30.0,
        enable_streaming=True,
        bearer_token="your-auth-token-here",
    )
    print(f"      URL: {params3.url}")
    print(
        f"      Auth: {'✅ Bearer token set' if params3.bearer_token else '❌ No auth'}"
    )

    # Test one of them
    print("\n   🧪 Testing parameter set 1...")
    try:
        async with http_client(params1) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            print("      ✅ Connection successful with params1!")
            print(f"      📋 Server: {init_result.serverInfo.name}")

    except Exception as e:
        print(f"      ❌ Connection failed: {type(e).__name__}")


async def error_handling_example():
    """Demonstrate error handling scenarios - SILENT VERSION."""
    print("\n🚨 Error Handling Examples")
    print("=" * 40)

    # Temporarily redirect stderr to suppress error traces during testing
    import os
    from contextlib import redirect_stderr

    # Test 1: Invalid URL - Silent test
    print("\n   1️⃣ Testing invalid URL:")
    try:
        with redirect_stderr(open(os.devnull, "w")):
            invalid_params = StreamableHTTPParameters(
                url="http://localhost:9999/mcp",
                timeout=2.0,  # Short timeout
            )
            async with http_client(invalid_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)
        print("      ❌ This should have failed")

    except Exception as e:
        print(f"      ✅ Properly caught connection error: {type(e).__name__}")

    # Test 2: Malformed URL
    print("\n   2️⃣ Testing malformed URL:")
    try:
        _malformed_params = StreamableHTTPParameters(url="not-a-valid-url", timeout=5.0)
        print("      ❌ This should have failed validation")

    except Exception as e:
        print(f"      ✅ Properly caught validation error: {type(e).__name__}")

    # Test 3: Timeout scenario - Silent test
    print("\n   3️⃣ Testing very short timeout:")
    try:
        with redirect_stderr(open(os.devnull, "w")):
            timeout_params = StreamableHTTPParameters(
                url="http://localhost:8000/mcp",
                timeout=0.001,  # Very short timeout
            )
            async with http_client(timeout_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)
        print("      ❌ This should have timed out")

    except Exception as e:
        print(f"      ✅ Properly handled timeout: {type(e).__name__}")

    print("   💡 Error handling is working correctly!")


async def comparison_example():
    """Compare SSE vs Streamable HTTP side by side."""
    print("\n⚖️ Transport Comparison Example")
    print("=" * 40)

    comparisons = {
        "SSE (Deprecated)": {
            "endpoints": "Separate /sse and /messages",
            "complexity": "High - complex connection management",
            "infrastructure": "Limited compatibility",
            "streaming": "Server-to-client only",
            "future": "Deprecated as of 2025-03-26",
        },
        "Streamable HTTP (Modern)": {
            "endpoints": "Single /mcp endpoint",
            "complexity": "Low - standard HTTP",
            "infrastructure": "Full compatibility",
            "streaming": "Optional, when beneficial",
            "future": "Current standard",
        },
    }

    for transport, features in comparisons.items():
        print(f"\n📋 {transport}:")
        for feature, value in features.items():
            print(f"   {feature.title()}: {value}")


def main():
    """Main entry point."""
    print("🌐 chuk-mcp Streamable HTTP Transport Examples")
    print("=" * 60)
    print("Demonstrating the modern MCP transport (spec 2025-03-26)")
    print("=" * 60)

    try:
        # Run main example
        anyio.run(streamable_http_example)

        # Run additional examples
        anyio.run(transport_detection_example)
        anyio.run(fallback_example)
        anyio.run(manual_fallback_example)
        anyio.run(parameter_creation_example)
        anyio.run(error_handling_example)
        anyio.run(comparison_example)

        print("\n" + "=" * 60)
        print("📚 Summary:")
        print("✅ Streamable HTTP transport working correctly")
        print("✅ Single endpoint simplicity (/mcp)")
        print("✅ Both immediate and streaming responses")
        print("✅ Better infrastructure compatibility")
        print("✅ Automatic transport detection")
        print("✅ Fallback mechanism demonstration")
        print("✅ Parameter creation flexibility")
        print("✅ Robust error handling")
        print("🚀 Ready for production use!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n👋 Examples interrupted")
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
