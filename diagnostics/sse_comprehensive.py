#!/usr/bin/env python3
"""
Comprehensive SSE Server Test

Tests the SSE transport against an existing SSE MCP server.
This verifies that the chuk-mcp SSE transport works correctly
with real SSE servers implementing the deprecated specification.

Usage:
    # Start your SSE server first:
    python proper_sse_server.py

    # Then run this test:
    python comprehensive_sse_test.py
"""

import asyncio
import logging
import sys

import anyio

# chuk-mcp imports
from chuk_mcp.transports.sse import sse_client, SSEParameters
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SSEServerTester:
    """Comprehensive tester for SSE MCP servers."""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.test_results = {}

    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🧪 Comprehensive SSE MCP Server Test Suite")
        print("=" * 60)
        print(f"Testing server: {self.server_url}")
        print("=" * 60)

        # Configure SSE parameters
        sse_params = SSEParameters(
            url=self.server_url,
            timeout=30.0,
        )

        try:
            async with sse_client(sse_params) as (read_stream, write_stream):
                print("✅ SSE connection established!")

                # Run test suite
                await self._test_initialization(read_stream, write_stream)
                await self._test_basic_operations(read_stream, write_stream)
                await self._test_tools(read_stream, write_stream)
                await self._test_resources(read_stream, write_stream)
                await self._test_prompts(read_stream, write_stream)
                await self._test_concurrent_operations(read_stream, write_stream)

                # Print summary
                self._print_test_summary()

        except Exception as e:
            print(f"❌ Failed to connect to SSE server: {e}")
            print("\n💡 Make sure your SSE server is running:")
            print("   python proper_sse_server.py")
            return False

        return True

    async def _test_initialization(self, read_stream, write_stream):
        """Test MCP initialization sequence."""
        print("\n1️⃣ Testing Initialization")
        print("-" * 30)

        try:
            init_result = await asyncio.wait_for(
                send_initialize(read_stream, write_stream), timeout=10.0
            )

            self.test_results["initialization"] = True
            print(f"✅ Server: {init_result.serverInfo.name}")
            print(f"✅ Version: {init_result.serverInfo.version}")
            print(f"✅ Protocol: {init_result.protocolVersion}")

            if hasattr(init_result, "instructions") and init_result.instructions:
                print(f"💡 Instructions: {init_result.instructions}")

            # Fix: Convert Pydantic model to dict before calling .keys()
            if hasattr(init_result.capabilities, "model_dump"):
                capabilities_dict = init_result.capabilities.model_dump()
            else:
                capabilities_dict = dict(init_result.capabilities)
            print(f"🔧 Capabilities: {', '.join(capabilities_dict.keys())}")

        except Exception as e:
            self.test_results["initialization"] = False
            print(f"❌ Initialization failed: {e}")

    async def _test_basic_operations(self, read_stream, write_stream):
        """Test basic MCP operations."""
        print("\n2️⃣ Testing Basic Operations")
        print("-" * 30)

        # Test ping
        try:
            ping_result = await asyncio.wait_for(
                send_ping(read_stream, write_stream), timeout=5.0
            )
            self.test_results["ping"] = ping_result
            print(f"✅ Ping: {'Success' if ping_result else 'Failed'}")
        except Exception as e:
            self.test_results["ping"] = False
            print(f"❌ Ping failed: {e}")

    async def _test_tools(self, read_stream, write_stream):
        """Test tools functionality."""
        print("\n3️⃣ Testing Tools")
        print("-" * 30)

        try:
            # List tools
            tools_response = await asyncio.wait_for(
                send_tools_list(read_stream, write_stream), timeout=10.0
            )

            tools = tools_response.get("tools", [])
            self.test_results["tools_list"] = len(tools) > 0

            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   • {tool['name']}: {tool['description']}")

            # Test tool calls
            tool_call_results = {}

            for tool in tools[:3]:  # Test first 3 tools
                tool_name = tool["name"]
                try:
                    print(f"\n🔧 Testing tool: {tool_name}")

                    # Prepare arguments based on tool
                    if tool_name == "sse_greet":
                        args = {"name": "Test User", "message": "Hello"}
                    elif tool_name == "sse_counter":
                        args = {"increment": 5}
                    elif tool_name == "session_info":
                        args = {}
                    else:
                        args = {}

                    result = await asyncio.wait_for(
                        send_tools_call(read_stream, write_stream, tool_name, args),
                        timeout=10.0,
                    )

                    tool_call_results[tool_name] = True
                    content = result.get("content", [{}])[0].get("text", "No content")
                    print(f"   ✅ Result: {content[:100]}...")

                except Exception as e:
                    tool_call_results[tool_name] = False
                    print(f"   ❌ Failed: {e}")

            self.test_results["tool_calls"] = tool_call_results

        except Exception as e:
            self.test_results["tools_list"] = False
            print(f"❌ Tools test failed: {e}")

    async def _test_resources(self, read_stream, write_stream):
        """Test resources functionality."""
        print("\n4️⃣ Testing Resources")
        print("-" * 30)

        try:
            # List resources
            resources_response = await asyncio.wait_for(
                send_resources_list(read_stream, write_stream), timeout=10.0
            )

            resources = resources_response.get("resources", [])
            self.test_results["resources_list"] = len(resources) > 0

            print(f"✅ Found {len(resources)} resources:")
            for resource in resources:
                print(f"   • {resource['name']}: {resource['description']}")
                print(f"     URI: {resource['uri']}")

            # Test reading resources
            for resource in resources[:2]:  # Test first 2 resources
                try:
                    uri = resource["uri"]
                    print(f"\n📖 Reading resource: {uri}")

                    content_response = await asyncio.wait_for(
                        send_resources_read(read_stream, write_stream, uri),
                        timeout=10.0,
                    )

                    contents = content_response.get("contents", [])
                    if contents:
                        content_text = contents[0].get("text", "No text content")
                        print(f"   ✅ Content preview: {content_text[:100]}...")

                except Exception as e:
                    print(f"   ❌ Failed to read resource {uri}: {e}")

        except Exception as e:
            self.test_results["resources_list"] = False
            print(f"❌ Resources test failed: {e}")

    async def _test_prompts(self, read_stream, write_stream):
        """Test prompts functionality."""
        print("\n5️⃣ Testing Prompts")
        print("-" * 30)

        try:
            # List prompts
            prompts_response = await asyncio.wait_for(
                send_prompts_list(read_stream, write_stream), timeout=10.0
            )

            prompts = prompts_response.get("prompts", [])
            self.test_results["prompts_list"] = len(prompts) > 0

            print(f"✅ Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"   • {prompt['name']}: {prompt['description']}")

            # Test getting prompts would go here if server supports prompts/get

        except Exception as e:
            self.test_results["prompts_list"] = False
            print(f"❌ Prompts test failed: {e}")

    async def _test_concurrent_operations(self, read_stream, write_stream):
        """Test concurrent operations."""
        print("\n6️⃣ Testing Concurrent Operations")
        print("-" * 30)

        try:
            # Run multiple operations concurrently
            tasks = []

            # Multiple pings
            for i in range(3):
                tasks.append(send_ping(read_stream, write_stream))

            # Tools list
            tasks.append(send_tools_list(read_stream, write_stream))

            # Run concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if not isinstance(r, Exception))
            total = len(results)

            self.test_results["concurrent"] = successful == total
            print(f"✅ Concurrent operations: {successful}/{total} successful")

            if successful < total:
                print("   Some operations failed:")
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"   ❌ Task {i}: {result}")

        except Exception as e:
            self.test_results["concurrent"] = False
            print(f"❌ Concurrent operations test failed: {e}")

    def _print_test_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        total_tests = 0
        passed_tests = 0

        # Count main test categories
        main_tests = [
            "initialization",
            "ping",
            "tools_list",
            "resources_list",
            "prompts_list",
            "concurrent",
        ]

        for test_name in main_tests:
            result = self.test_results.get(test_name, False)
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<20} {status}")
            total_tests += 1
            if result:
                passed_tests += 1

        # Tool call details
        tool_calls = self.test_results.get("tool_calls", {})
        if tool_calls:
            print("\nTool Call Details:")
            for tool_name, result in tool_calls.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"  {tool_name:<18} {status}")

        print("\n" + "=" * 60)
        print(f"Overall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! SSE transport is working perfectly!")
        elif passed_tests >= total_tests * 0.8:
            print("✅ Most tests passed. SSE transport is working well!")
        else:
            print("⚠️ Some tests failed. Check server implementation.")

        print("=" * 60)


async def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://localhost:8000"

    tester = SSEServerTester(server_url)

    try:
        success = await tester.run_all_tests()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("🌊 chuk-mcp SSE Transport Test Suite")
    print("Testing against existing SSE MCP server")
    print("\nUsage:")
    print("  python comprehensive_sse_test.py [server_url]")
    print("  Default: http://localhost:8000")
    print("\nMake sure your SSE server is running first!")
    print("-" * 50)

    anyio.run(main)
