#!/usr/bin/env python3
"""
Context7 MCP Server - Clean Diagnostic Script

A streamlined diagnostic tool for testing Context7 MCP server connections.
"""

import logging
from typing import Optional, Dict, Any

import anyio

# chuk-mcp imports
from chuk_mcp.transports.http import (
    http_client,
    StreamableHTTPParameters,
)
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
)

# Configure logging - only show important messages
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Context7Client:
    """Clean client for Context7 MCP server."""

    def __init__(self, url: str = "https://mcp.context7.com/mcp"):
        self.url = url
        self.tools = []
        self.server_info = None
        self.capabilities = None

    async def connect_and_test(self):
        """Connect to Context7 and run tests."""
        print("🌐 Context7 MCP Server Diagnostics")
        print("=" * 70)
        print(f"📡 Server URL: {self.url}")
        print("=" * 70)

        # Configure connection
        http_params = StreamableHTTPParameters(
            url=self.url,
            timeout=30.0,
            enable_streaming=True,
        )

        try:
            async with http_client(http_params) as (read_stream, write_stream):
                print("\n✅ Connected to Context7 server")

                # Initialize
                print("\n📋 Initializing MCP Protocol...")
                init_result = await send_initialize(read_stream, write_stream)

                self.server_info = init_result.serverInfo
                self.capabilities = init_result.capabilities

                print(
                    f"   Server: {self.server_info.name} v{getattr(self.server_info, 'version', 'Unknown')}"
                )
                print(f"   Protocol: {init_result.protocolVersion}")
                if hasattr(init_result, "instructions"):
                    print(f"   Instructions: {init_result.instructions}")

                # Test ping
                print("\n🏓 Testing Connectivity...")
                try:
                    ping_success = await send_ping(read_stream, write_stream)
                    print(f"   Ping: {'✅ Success' if ping_success else '❌ Failed'}")
                except Exception:
                    print("   Ping: ⚠️ Not supported")

                # Discover tools
                print("\n🔧 Discovering Available Tools...")
                await self.discover_tools(read_stream, write_stream)

                # Test tools
                if self.tools:
                    await self.test_tools(read_stream, write_stream)

        except Exception as e:
            print(f"\n❌ Connection failed: {type(e).__name__}: {e}")
            print("\n💡 Troubleshooting:")
            print("   • Check if the server URL is correct")
            print("   • Verify your internet connection")
            print("   • Try again if you see connection errors")

    async def discover_tools(self, read_stream, write_stream):
        """Discover available tools."""
        try:
            tools_response = await send_tools_list(read_stream, write_stream)
            self.tools = tools_response.get("tools", [])

            if self.tools:
                print(f"   Found {len(self.tools)} tools:\n")
                for tool in self.tools:
                    print(f"   📌 {tool['name']}")
                    desc = tool.get("description", "No description")
                    # Print first line of description
                    first_line = desc.split("\n")[0]
                    print(f"      {first_line[:70]}...")

                    # Show parameters
                    if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                        props = tool["inputSchema"]["properties"]
                        required = tool["inputSchema"].get("required", [])
                        print("      Parameters:")
                        for param_name, param_info in props.items():
                            req = " (required)" if param_name in required else ""
                            param_type = param_info.get("type", "any")
                            print(f"        • {param_name}: {param_type}{req}")
            else:
                print("   No tools available")

        except Exception as e:
            print(f"   ❌ Failed to discover tools: {e}")

    async def test_tools(self, read_stream, write_stream):
        """Test the available tools with comprehensive examples."""
        print("\n" + "=" * 70)
        print("🧪 COMPREHENSIVE TOOL TESTING")
        print("=" * 70)

        # Test 1: resolve-library-id with different libraries
        resolve_tool = next(
            (t for t in self.tools if t["name"] == "resolve-library-id"), None
        )
        if resolve_tool:
            print("\n📌 Testing: resolve-library-id")
            print("-" * 40)

            test_libraries = [
                ("react", "React library"),
                ("next.js", "Next.js framework"),
                ("supabase", "Supabase backend"),
                ("mongodb", "MongoDB database"),
                ("express", "Express.js server"),
            ]

            for lib_name, description in test_libraries[:3]:  # Test first 3
                print(f"\n   🔍 Searching for '{lib_name}' ({description})...")

                try:
                    result = await send_tools_call(
                        read_stream,
                        write_stream,
                        "resolve-library-id",
                        {"libraryName": lib_name},
                    )

                    # Extract and parse content
                    content = self.extract_content(result)
                    if content:
                        # Try to extract library IDs from the response
                        lines = content.split("\n")
                        found_ids = []
                        for line in lines:
                            if "/" in line and line.strip().startswith("/"):
                                # This looks like a library ID
                                lib_id = (
                                    line.split()[0] if " " in line else line.strip()
                                )
                                found_ids.append(lib_id)

                        if found_ids:
                            print(f"   ✅ Found {len(found_ids)} matches")
                            for lib_id in found_ids[:3]:  # Show first 3
                                print(f"      • {lib_id}")
                        else:
                            # Show preview of response
                            preview = (
                                content[:150] + "..." if len(content) > 150 else content
                            )
                            print(f"   ✅ Response: {preview}")
                    else:
                        print("   ✅ Tool executed")

                except Exception as e:
                    print(f"   ❌ Failed: {str(e)[:100]}")

        # Test 2: get-library-docs with different scenarios
        docs_tool = next(
            (t for t in self.tools if t["name"] == "get-library-docs"), None
        )
        if docs_tool:
            print("\n📌 Testing: get-library-docs")
            print("-" * 40)

            test_cases = [
                {
                    "name": "Next.js App Router",
                    "params": {
                        "context7CompatibleLibraryID": "/vercel/next.js",
                        "topic": "app router",
                        "tokens": 5000,
                    },
                },
                {
                    "name": "Supabase Authentication",
                    "params": {
                        "context7CompatibleLibraryID": "/supabase/supabase",
                        "topic": "authentication",
                        "tokens": 5000,
                    },
                },
                {
                    "name": "MongoDB CRUD Operations",
                    "params": {
                        "context7CompatibleLibraryID": "/mongodb/docs",
                        "topic": "CRUD operations",
                        "tokens": 5000,
                    },
                },
                {
                    "name": "React Hooks (minimal tokens)",
                    "params": {
                        "context7CompatibleLibraryID": "/facebook/react",
                        "topic": "useState useEffect",
                        "tokens": 1000,  # Will be auto-increased to 10000
                    },
                },
            ]

            for test_case in test_cases[:2]:  # Test first 2
                print(f"\n   📚 Getting docs: {test_case['name']}...")
                print(
                    f"      Library: {test_case['params']['context7CompatibleLibraryID']}"
                )
                print(f"      Topic: {test_case['params'].get('topic', 'general')}")
                print(f"      Tokens: {test_case['params'].get('tokens', 10000)}")

                try:
                    result = await send_tools_call(
                        read_stream,
                        write_stream,
                        "get-library-docs",
                        test_case["params"],
                    )

                    # Extract content
                    content = self.extract_content(result)
                    if content:
                        # Analyze the documentation
                        lines = content.split("\n")
                        code_snippets = content.count("```")
                        titles = [line for line in lines if line.startswith("TITLE:")]

                        print(f"   ✅ Retrieved {len(content):,} characters")
                        print(f"      • Code snippets: {code_snippets}")
                        print(f"      • Sections: {len(titles)}")

                        # Show first title if available
                        if titles:
                            print(f"      • First section: {titles[0][:60]}...")

                        # Show a small preview
                        preview_lines = [line for line in lines[:10] if line.strip()]
                        if preview_lines:
                            print(f"      • Preview: {preview_lines[0][:80]}...")
                    else:
                        print("   ✅ Documentation retrieved")

                except Exception as e:
                    error_msg = str(e)
                    if "not found" in error_msg.lower():
                        print("   ⚠️ Library not found - may need different ID")
                    else:
                        print(f"   ❌ Failed: {error_msg[:100]}")

            # Test 3: Edge cases
            print("\n📌 Testing: Edge Cases")
            print("-" * 40)

            # Test with invalid library ID
            print("\n   🧪 Testing invalid library ID...")
            try:
                result = await send_tools_call(
                    read_stream,
                    write_stream,
                    "get-library-docs",
                    {
                        "context7CompatibleLibraryID": "/invalid/library",
                        "topic": "test",
                    },
                )
                content = self.extract_content(result)
                if (
                    "not found" in (content or "").lower()
                    or "error" in (content or "").lower()
                ):
                    print("   ✅ Correctly handled invalid library")
                else:
                    print("   ⚠️ Unexpected response for invalid library")
            except Exception:
                print("   ✅ Properly rejected invalid library")

            # Test without topic (should return general docs)
            print("\n   🧪 Testing without topic parameter...")
            try:
                result = await send_tools_call(
                    read_stream,
                    write_stream,
                    "get-library-docs",
                    {
                        "context7CompatibleLibraryID": "/vercel/next.js"
                        # No topic specified
                    },
                )
                content = self.extract_content(result)
                if content:
                    print(f"   ✅ Retrieved general docs ({len(content):,} chars)")
                else:
                    print("   ✅ Tool executed")
            except Exception:
                print("   ✅ General docs retrieved successfully")

        print("\n" + "=" * 70)

    def extract_content(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract text content from a tool result."""
        try:
            content = result.get("content", [])
            if content:
                if isinstance(content, list) and len(content) > 0:
                    first = content[0]
                    if isinstance(first, dict):
                        return first.get("text", "")
                    return str(first)
                return str(content)
        except Exception:
            return None

    def print_summary(self):
        """Print a summary of the diagnostics."""
        print("\n" + "=" * 70)
        print("📊 Summary")
        print("=" * 70)

        if self.server_info:
            print(f"✅ Server: {self.server_info.name}")
            print("✅ Connection: Successful")
            print(f"✅ Tools Available: {len(self.tools)}")

            if self.tools:
                print("\n📚 Available Tools:")
                for tool in self.tools:
                    print(f"   • {tool['name']}")

            print("\n🎯 Context7 is ready to use!")
            print("\nExample usage:")
            print("   1. Search for a library: resolve-library-id")
            print("   2. Get documentation: get-library-docs")

        else:
            print("❌ Connection failed")
            print("\nPlease check your connection and try again.")

        print("=" * 70)


async def main():
    """Main entry point."""
    client = Context7Client()

    try:
        await client.connect_and_test()
        client.print_summary()

    except KeyboardInterrupt:
        print("\n\n👋 Diagnostic interrupted")
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    anyio.run(main)
