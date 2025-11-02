#!/usr/bin/env python3
"""
Notion MCP Timeout Diagnostic

This script combines:
1. Direct OAuth authentication via chuk_mcp_client_oauth
2. Tool listing and execution
3. Detailed timeout and performance tracking

Goal: Diagnose why Notion MCP hits timeouts when used through chuk-mcp layers
"""

import asyncio
import json
import time
import uuid
import logging
import sys
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def parse_sse_json(lines: list[str]) -> Dict[str, Any]:
    """Parse SSE response into JSON."""
    for line in lines:
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}


class NotionMCPDiagnostic:
    """Diagnostic tool for Notion MCP timeout issues."""

    def __init__(self):
        self.server_name = "notion-mcp"
        self.server_url = "https://mcp.notion.com/mcp"
        self.session_id: Optional[str] = None
        self.oauth_handler = None
        self.tokens = None
        self.timings: Dict[str, float] = {}

    async def initialize_oauth(self):
        """Initialize OAuth authentication."""
        print("=" * 80)
        print("NOTION MCP TIMEOUT DIAGNOSTIC")
        print("=" * 80)
        print()

        try:
            # Import here to avoid dependency issues
            from chuk_mcp_client_oauth import OAuthHandler

            self.oauth_handler = OAuthHandler()
        except ImportError as e:
            print(f"❌ Failed to import chuk_mcp_client_oauth: {e}")
            print("   Make sure the library is installed:")
            print("   pip install chuk-mcp-client-oauth")
            return False

        print("🔐 Step 1: OAuth Authentication")
        print("-" * 80)

        start = time.time()
        try:
            self.tokens = await self.oauth_handler.ensure_authenticated_mcp(
                server_name=self.server_name,
                server_url=self.server_url,
                scopes=["read", "write"],
            )
            elapsed = time.time() - start
            self.timings["oauth"] = elapsed

            print(f"✅ Authenticated in {elapsed:.2f}s")
            print(f"   Token: {self.tokens.access_token[:20]}...")
            print()
            return True

        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ Authentication failed after {elapsed:.2f}s")
            print(f"   Error: {type(e).__name__}: {e}")
            return False

    async def initialize_session(self) -> bool:
        """Initialize MCP session."""
        print("📋 Step 2: Initialize MCP Session")
        print("-" * 80)

        self.session_id = str(uuid.uuid4())
        start = time.time()

        try:
            init_response = await self.oauth_handler.authenticated_request(
                server_name=self.server_name,
                server_url=self.server_url,
                url=self.server_url,
                method="POST",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"roots": {"listChanged": True}},
                        "clientInfo": {
                            "name": "notion-timeout-diagnostic",
                            "version": "1.0.0",
                        },
                    },
                },
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                timeout=120.0,  # Long timeout for slow Notion
            )

            elapsed = time.time() - start
            self.timings["initialize"] = elapsed

            # Extract session ID from response header
            self.session_id = init_response.headers.get(
                "mcp-session-id", self.session_id
            )

            print(f"✅ Session initialized in {elapsed:.2f}s")
            print(f"   Session ID: {self.session_id[:16]}...")
            print()

            # Send initialized notification
            await self.oauth_handler.authenticated_request(
                server_name=self.server_name,
                server_url=self.server_url,
                url=self.server_url,
                method="POST",
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": self.session_id,
                },
                timeout=60.0,
            )

            return True

        except Exception as e:
            elapsed = time.time() - start
            self.timings["initialize"] = elapsed
            print(f"❌ Session initialization failed after {elapsed:.2f}s")
            print(f"   Error: {type(e).__name__}: {e}")
            return False

    async def list_tools(self) -> Optional[list]:
        """List available Notion tools."""
        print("🔧 Step 3: List Available Tools")
        print("-" * 80)

        start = time.time()

        try:
            tools_response = await self.oauth_handler.authenticated_request(
                server_name=self.server_name,
                server_url=self.server_url,
                url=self.server_url,
                method="POST",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": self.session_id,
                },
                timeout=120.0,  # Long timeout
            )

            elapsed = time.time() - start
            self.timings["tools_list"] = elapsed

            # Parse SSE response
            content_type = tools_response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                data = parse_sse_json(tools_response.text.strip().splitlines())
            else:
                data = tools_response.json()

            if "result" in data and "tools" in data["result"]:
                tools = data["result"]["tools"]
                print(f"✅ Listed {len(tools)} tools in {elapsed:.2f}s")
                print()
                print("📦 Available tools (showing first 10):")
                for i, tool in enumerate(tools[:10], 1):
                    name = tool.get("name", "Unknown")
                    desc = tool.get("description", "No description")
                    print(f"   {i}. {name}")
                    if desc:
                        desc_short = desc[:70] + "..." if len(desc) > 70 else desc
                        print(f"      {desc_short}")

                if len(tools) > 10:
                    print(f"   ... and {len(tools) - 10} more")
                print()
                return tools
            else:
                print(f"❌ Unexpected response format after {elapsed:.2f}s")
                print(f"   Response keys: {list(data.keys())}")
                return None

        except Exception as e:
            elapsed = time.time() - start
            self.timings["tools_list"] = elapsed
            print(f"❌ Tool listing failed after {elapsed:.2f}s")
            print(f"   Error: {type(e).__name__}: {e}")
            return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Execute a specific tool and measure performance."""
        print(f"⚙️ Step 4: Execute Tool '{tool_name}'")
        print("-" * 80)
        print(f"Arguments: {json.dumps(arguments, indent=2)}")
        print()

        start = time.time()

        try:
            exec_response = await self.oauth_handler.authenticated_request(
                server_name=self.server_name,
                server_url=self.server_url,
                url=self.server_url,
                method="POST",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": self.session_id,
                },
                timeout=300.0,  # 5 minute timeout like in your test
            )

            elapsed = time.time() - start
            self.timings[f"tool_exec_{tool_name}"] = elapsed

            # Parse response
            content_type = exec_response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                data = parse_sse_json(exec_response.text.strip().splitlines())
            else:
                data = exec_response.json()

            print(f"✅ Tool executed in {elapsed:.2f}s")

            # Display result
            if "result" in data:
                result = data["result"]
                print(f"   Result type: {type(result).__name__}")

                if isinstance(result, dict):
                    if "content" in result:
                        content = result["content"]
                        print(f"   Content items: {len(content)}")
                        for i, item in enumerate(content[:3], 1):
                            if isinstance(item, dict):
                                print(f"   Item {i}:")
                                for key, value in item.items():
                                    if isinstance(value, str) and len(value) > 100:
                                        print(f"      {key}: {value[:100]}...")
                                    else:
                                        print(f"      {key}: {value}")
                    else:
                        print(f"   Result keys: {list(result.keys())}")
                        print(f"   Result preview: {str(result)[:200]}...")
                else:
                    print(f"   Result: {str(result)[:200]}...")

            print()
            return True

        except asyncio.TimeoutError:
            elapsed = time.time() - start
            self.timings[f"tool_exec_{tool_name}"] = elapsed
            print(f"❌ TIMEOUT after {elapsed:.2f}s")
            print(f"   Tool '{tool_name}' did not respond within 300s")
            print()
            return False

        except Exception as e:
            elapsed = time.time() - start
            self.timings[f"tool_exec_{tool_name}"] = elapsed
            print(f"❌ Tool execution failed after {elapsed:.2f}s")
            print(f"   Error: {type(e).__name__}: {e}")
            print()
            return False

    def print_summary(self):
        """Print diagnostic summary."""
        print("=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        print()
        print("⏱️ Timing Breakdown:")
        print("-" * 80)

        total_time = 0.0
        for operation, duration in self.timings.items():
            print(f"   {operation:30s}: {duration:8.2f}s")
            total_time += duration

        print("-" * 80)
        print(f"   {'TOTAL':30s}: {total_time:8.2f}s")
        print()

        print("💡 Analysis:")
        print("-" * 80)

        if "oauth" in self.timings:
            if self.timings["oauth"] > 10:
                print("   ⚠️ OAuth authentication is slow (>10s)")
            else:
                print("   ✅ OAuth authentication is reasonable")

        if "initialize" in self.timings:
            if self.timings["initialize"] > 30:
                print("   ⚠️ Session initialization is very slow (>30s)")
            elif self.timings["initialize"] > 10:
                print("   ⚠️ Session initialization is slow (>10s)")
            else:
                print("   ✅ Session initialization is reasonable")

        if "tools_list" in self.timings:
            if self.timings["tools_list"] > 30:
                print("   ⚠️ Tool listing is very slow (>30s)")
            elif self.timings["tools_list"] > 10:
                print("   ⚠️ Tool listing is slow (>10s)")
            else:
                print("   ✅ Tool listing is reasonable")

        # Check for tool execution times
        tool_exec_times = {
            k: v for k, v in self.timings.items() if k.startswith("tool_exec_")
        }
        if tool_exec_times:
            for tool_key, duration in tool_exec_times.items():
                tool_name = tool_key.replace("tool_exec_", "")
                if duration >= 300:
                    print(f"   ❌ Tool '{tool_name}' hit timeout (300s)")
                elif duration > 60:
                    print(f"   ⚠️ Tool '{tool_name}' is very slow (>{duration:.1f}s)")
                elif duration > 30:
                    print(f"   ⚠️ Tool '{tool_name}' is slow (>{duration:.1f}s)")
                else:
                    print(
                        f"   ✅ Tool '{tool_name}' completed reasonably ({duration:.1f}s)"
                    )

        print()
        print("🎯 Recommendations:")
        print("-" * 80)

        if total_time > 300:
            print("   • Consider increasing timeout values to >300s")
            print("   • Notion MCP appears to be inherently slow")
            print("   • May need retry logic with exponential backoff")
        elif total_time > 120:
            print("   • Current 120s timeout may be insufficient")
            print("   • Consider 180-300s timeout for Notion operations")
        else:
            print("   • Current timeout settings appear adequate")

        print("   • Monitor which specific operation is slowest")
        print("   • Consider caching tool lists to avoid repeated slow calls")
        print("   • Implement progress indicators for long operations")
        print()


async def main():
    """Main diagnostic routine."""
    diagnostic = NotionMCPDiagnostic()

    # Step 1: OAuth
    if not await diagnostic.initialize_oauth():
        print("❌ Diagnostic aborted: OAuth failed")
        return

    # Step 2: Initialize session
    if not await diagnostic.initialize_session():
        print("❌ Diagnostic aborted: Session initialization failed")
        diagnostic.print_summary()
        return

    # Step 3: List tools
    tools = await diagnostic.list_tools()
    if not tools:
        print("❌ Diagnostic aborted: Tool listing failed")
        diagnostic.print_summary()
        return

    # Step 4: Execute a simple tool (if available)
    # Try to find a simple read-only tool
    simple_tools = [
        "notion-search",
        "notion-fetch",
        "notion-get-comments",
        "list_databases",
        "search_pages",
        "get_page",
        "list_users",
    ]

    tool_to_test = None
    test_args = {}

    for tool in tools:
        tool_name = tool.get("name", "")

        # Try to find a simple tool
        if tool_name in simple_tools:
            tool_to_test = tool_name

            # Set up appropriate test arguments
            if tool_name == "notion-search":
                test_args = {"query": "test", "limit": 5}
            elif tool_name == "notion-fetch":
                # Skip fetch as it needs a specific URL
                continue
            elif tool_name == "notion-get-comments":
                # Skip as it needs a page ID
                continue
            elif tool_name == "list_databases":
                test_args = {}
            elif tool_name == "search_pages":
                test_args = {"query": "test", "limit": 5}
            elif tool_name == "list_users":
                test_args = {}

            break

    if tool_to_test:
        print(f"🎯 Selected tool for testing: {tool_to_test}")
        print()
        await diagnostic.execute_tool(tool_to_test, test_args)
    else:
        print("⚠️ No suitable simple tool found for execution test")
        print()

    # Print summary
    diagnostic.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
