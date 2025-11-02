#!/usr/bin/env python3
"""
Notion via chuk-mcp Transport Layer Diagnostic

This script tests Notion MCP using chuk-mcp's HTTP transport layer
to see if the transport adds overhead or timeout issues.
"""

import asyncio
import logging
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # INFO level for cleaner output
    format="%(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def test_notion_via_chuk_transport():
    """Test Notion MCP using chuk-mcp transport layers."""

    print("=" * 80)
    print("NOTION MCP VIA CHUK-MCP TRANSPORT LAYER DIAGNOSTIC")
    print("=" * 80)
    print()

    # Import chuk-mcp components
    try:
        from chuk_mcp.transports.http import (
            http_client,
            StreamableHTTPParameters,
        )
        from chuk_mcp.protocol.messages import (
            send_initialize,
            send_tools_list,
            send_tools_call,
        )
    except ImportError as e:
        print(f"❌ Failed to import chuk-mcp components: {e}")
        return

    # Import OAuth handler
    try:
        from chuk_mcp_client_oauth import OAuthHandler
    except ImportError as e:
        print(f"❌ Failed to import OAuth handler: {e}")
        print("   Install with: pip install chuk-mcp-client-oauth")
        return

    server_name = "notion-mcp"
    server_url = "https://mcp.notion.com/mcp"

    print("🔧 Configuration:")
    print("-" * 80)
    print(f"Server: {server_name}")
    print(f"URL: {server_url}")
    print("Transport: chuk-mcp StreamableHTTP")
    print("Timeout: 300.0s")
    print()

    timings = {}
    start_total = time.time()

    # Step 1: OAuth
    print("🔐 Step 1: OAuth Authentication")
    print("-" * 80)

    oauth_start = time.time()
    try:
        oauth_handler = OAuthHandler()
        tokens = await oauth_handler.ensure_authenticated_mcp(
            server_name=server_name, server_url=server_url, scopes=["read", "write"]
        )
        oauth_elapsed = time.time() - oauth_start
        timings["oauth"] = oauth_elapsed

        print(f"✅ OAuth completed in {oauth_elapsed:.2f}s")
        print(f"   Token: {tokens.access_token[:20]}...")
        print()

    except Exception as e:
        oauth_elapsed = time.time() - oauth_start
        timings["oauth"] = oauth_elapsed
        print(f"❌ OAuth failed after {oauth_elapsed:.2f}s")
        print(f"   Error: {type(e).__name__}: {e}")
        return

    # Step 2: Create HTTP transport with chuk-mcp
    print("📡 Step 2: Create chuk-mcp HTTP Transport")
    print("-" * 80)

    transport_start = time.time()
    try:
        http_params = StreamableHTTPParameters(
            url=server_url,
            timeout=300.0,
            enable_streaming=True,
            bearer_token=tokens.access_token,  # Use OAuth token
        )

        print("✅ Transport configured")
        print(f"   URL: {http_params.url}")
        print(f"   Timeout: {http_params.timeout}s")
        print(f"   Streaming: {http_params.enable_streaming}")
        print(
            f"   Auth: {'Bearer token set' if http_params.bearer_token else 'No auth'}"
        )
        print()

    except Exception as e:
        transport_elapsed = time.time() - transport_start
        print(f"❌ Transport config failed after {transport_elapsed:.2f}s")
        print(f"   Error: {type(e).__name__}: {e}")
        return

    # Step 3: Connect and initialize
    print("🔌 Step 3: Connect and Initialize MCP Session")
    print("-" * 80)

    init_start = time.time()
    try:
        async with http_client(http_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            init_elapsed = time.time() - init_start
            timings["initialize"] = init_elapsed

            print(f"✅ Session initialized in {init_elapsed:.2f}s")
            print(f"   Server: {init_result.serverInfo.name}")
            print(f"   Protocol: {init_result.protocolVersion}")
            print()

            # Step 4: List tools
            print("🔧 Step 4: List Available Tools")
            print("-" * 80)

            tools_start = time.time()
            try:
                tools_response = await send_tools_list(read_stream, write_stream)
                tools_elapsed = time.time() - tools_start
                timings["tools_list"] = tools_elapsed

                # tools_response is a ListToolsResult Pydantic model
                tools = tools_response.tools if hasattr(tools_response, "tools") else []
                print(f"✅ Listed {len(tools)} tools in {tools_elapsed:.2f}s")
                print()
                print("📦 Available tools (first 10):")
                for i, tool in enumerate(tools[:10], 1):
                    # Tool is a Pydantic model
                    name = tool.name if hasattr(tool, "name") else "Unknown"
                    desc = (
                        tool.description
                        if hasattr(tool, "description")
                        else "No description"
                    )
                    print(f"   {i}. {name}")
                    if desc:
                        desc_short = desc[:70] + "..." if len(desc) > 70 else desc
                        print(f"      {desc_short}")

                if len(tools) > 10:
                    print(f"   ... and {len(tools) - 10} more")
                print()

            except asyncio.TimeoutError:
                tools_elapsed = time.time() - tools_start
                timings["tools_list"] = tools_elapsed
                print(f"❌ TIMEOUT listing tools after {tools_elapsed:.2f}s")
                return

            except Exception as e:
                tools_elapsed = time.time() - tools_start
                timings["tools_list"] = tools_elapsed
                print(f"❌ Tool listing failed after {tools_elapsed:.2f}s")
                print(f"   Error: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
                return

            # Step 5: Execute a tool
            print("⚙️ Step 5: Execute Tool 'notion-search'")
            print("-" * 80)

            exec_start = time.time()
            try:
                tool_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    "notion-search",
                    {"query": "test", "limit": 5},
                )
                exec_elapsed = time.time() - exec_start
                timings["tool_exec"] = exec_elapsed

                print(f"✅ Tool executed in {exec_elapsed:.2f}s")

                # Display result (tool_result is a ToolResult Pydantic model)
                content = tool_result.content if hasattr(tool_result, "content") else []
                if content:
                    print(f"   Result items: {len(content)}")
                    for i, item in enumerate(content[:3], 1):
                        # item is a content model
                        if hasattr(item, "type"):
                            print(f"   Item {i}: type={item.type}")
                            if hasattr(item, "text") and item.text:
                                text_preview = (
                                    item.text[:100] + "..."
                                    if len(item.text) > 100
                                    else item.text
                                )
                                print(f"      text: {text_preview}")
                print()

            except asyncio.TimeoutError:
                exec_elapsed = time.time() - exec_start
                timings["tool_exec"] = exec_elapsed
                print(f"❌ TIMEOUT executing tool after {exec_elapsed:.2f}s")
                print()

            except Exception as e:
                exec_elapsed = time.time() - exec_start
                timings["tool_exec"] = exec_elapsed
                print(f"❌ Tool execution failed after {exec_elapsed:.2f}s")
                print(f"   Error: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
                print()

    except asyncio.TimeoutError:
        init_elapsed = time.time() - init_start
        timings["initialize"] = init_elapsed
        print(f"❌ TIMEOUT during initialization after {init_elapsed:.2f}s")
        print()

    except Exception as e:
        init_elapsed = time.time() - init_start
        print(f"❌ Connection/initialization failed after {init_elapsed:.2f}s")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        print()

    # Summary
    total_elapsed = time.time() - start_total

    print("=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print()
    print("⏱️ Timing Breakdown:")
    print("-" * 80)

    for operation, duration in timings.items():
        print(f"   {operation:30s}: {duration:8.2f}s")

    print("-" * 80)
    print(f"   {'TOTAL':30s}: {total_elapsed:8.2f}s")
    print()

    print("💡 Analysis:")
    print("-" * 80)

    if "oauth" in timings and "initialize" in timings and "tools_list" in timings:
        # Compare with direct approach
        print("   Comparison with direct OAuth approach:")
        print("     Direct OAuth init: ~10-11s")
        print(f"     chuk-mcp init: {timings['initialize']:.2f}s")

        overhead = timings["initialize"] - 10.5
        if overhead > 5:
            print(f"     ⚠️ chuk-mcp adds ~{overhead:.1f}s overhead")
        elif overhead > 2:
            print(f"     ⚠️ chuk-mcp adds ~{overhead:.1f}s overhead")
        else:
            print(f"     ✅ chuk-mcp overhead is minimal ({overhead:.1f}s)")

        print()
        print("     Direct tool list: ~10s")
        print(f"     chuk-mcp tool list: {timings['tools_list']:.2f}s")

        overhead = timings["tools_list"] - 10.0
        if overhead > 5:
            print(f"     ⚠️ chuk-mcp adds ~{overhead:.1f}s overhead")
        elif overhead > 2:
            print(f"     ⚠️ chuk-mcp adds ~{overhead:.1f}s overhead")
        else:
            print(f"     ✅ chuk-mcp overhead is minimal ({overhead:.1f}s)")

    if "tool_exec" in timings:
        print()
        if timings["tool_exec"] >= 300:
            print("   ❌ Tool execution hit timeout")
        elif timings["tool_exec"] > 60:
            print(f"   ⚠️ Tool execution is slow ({timings['tool_exec']:.1f}s)")
        else:
            print(f"   ✅ Tool execution is reasonable ({timings['tool_exec']:.1f}s)")

    print()
    print("🎯 Recommendations:")
    print("-" * 80)

    if total_elapsed > 300:
        print("   • Increase timeout to >600s")
    elif total_elapsed > 120:
        print("   • Current 300s timeout seems adequate")
    else:
        print("   • Current timeout settings are fine")

    print("   • Cache tool lists (changes infrequently)")
    print("   • Consider connection pooling for repeated calls")
    print("   • Monitor Notion API status for slowdowns")
    print()

    print("✅ Diagnostic complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_notion_via_chuk_transport())
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
