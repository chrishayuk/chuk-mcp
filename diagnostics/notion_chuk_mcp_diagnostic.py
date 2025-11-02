#!/usr/bin/env python3
"""
Notion via chuk-mcp Layer Diagnostic

This script tests Notion MCP through the chuk-mcp ToolManager layer,
similar to the Monday.com diagnostic, to identify where timeouts occur.
"""

import asyncio
import logging
import sys
import time
import json
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def test_notion_via_toolmanager():
    """Test Notion MCP through ToolManager to diagnose timeout issues."""

    print("=" * 80)
    print("NOTION MCP VIA CHUK-MCP TOOLMANAGER DIAGNOSTIC")
    print("=" * 80)
    print()

    # Check if ToolManager is available
    try:
        from mcp_cli.tools.manager import ToolManager
    except ImportError as e:
        print(f"❌ Failed to import ToolManager: {e}")
        print("   This diagnostic requires the mcp_cli package")
        return

    # Configuration
    notion_config = {
        "type": "http",
        "url": "https://mcp.notion.com/mcp",
        "transport": {
            "type": "streamable_http",
            "enable_streaming": True,
            "timeout": 300.0,  # 5 minutes like your Monday test
            "max_retries": 0,
        },
        "oauth": {"provider": "notion", "scopes": ["read", "write"]},
    }

    print("🔧 Configuration:")
    print("-" * 80)
    print(f"Server URL: {notion_config['url']}")
    print(f"Transport Type: {notion_config['transport']['type']}")
    print(f"Timeout: {notion_config['transport']['timeout']}s")
    print(f"Max Retries: {notion_config['transport']['max_retries']}")
    print(f"Streaming Enabled: {notion_config['transport']['enable_streaming']}")
    print(f"OAuth Provider: {notion_config['oauth']['provider']}")
    print()

    # Create ToolManager
    print("📦 Step 1: Create ToolManager")
    print("-" * 80)

    start_total = time.time()

    try:
        # Create with explicit config
        tm = ToolManager(
            servers={"notion": notion_config},
            tool_timeout=300.0,  # Match transport timeout
        )

        print("✅ ToolManager created")
        print(f"   ToolManager.tool_timeout: {tm.tool_timeout}s")
        print()

    except Exception as e:
        print("❌ ToolManager creation failed")
        print(f"   Error: {type(e).__name__}: {e}")
        return

    # Initialize
    print("🔐 Step 2: Initialize ToolManager (includes OAuth)")
    print("-" * 80)
    print("This step will:")
    print("  1. Authenticate via OAuth")
    print("  2. Initialize MCP session")
    print("  3. List available tools")
    print()

    init_start = time.time()

    try:
        success = await tm.initialize()
        init_elapsed = time.time() - init_start

        if not success:
            print(f"❌ Initialization failed after {init_elapsed:.2f}s")
            return

        print(f"✅ Initialized successfully in {init_elapsed:.2f}s")
        print(f"   Effective timeout: {tm._effective_timeout}s")
        print(f"   Effective max_retries: {tm._effective_max_retries}")

        # Check registered tools
        if hasattr(tm, "registry"):
            registry_size = (
                len(tm.registry) if hasattr(tm.registry, "__len__") else "unknown"
            )
            print(f"   Registry size: {registry_size} tools")

            # Try to get sample tools
            if hasattr(tm.registry, "items"):
                sample_tools = list(tm.registry.keys())[:5]
                if sample_tools:
                    print(f"   Sample tools: {sample_tools}")

        print()

    except asyncio.TimeoutError:
        init_elapsed = time.time() - init_start
        print(f"❌ TIMEOUT during initialization after {init_elapsed:.2f}s")
        print()
        return

    except Exception as e:
        init_elapsed = time.time() - init_start
        print(f"❌ Initialization failed after {init_elapsed:.2f}s")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return

    # List available tools (if not already done)
    print("📋 Step 3: Verify Tool Availability")
    print("-" * 80)

    try:
        # Try to get tool list
        if hasattr(tm, "list_tools"):
            tools = await tm.list_tools()
            print(f"✅ Found {len(tools)} tools")

            # Display sample
            print("\n📦 Sample tools (first 10):")
            for i, tool_info in enumerate(list(tools.items())[:10], 1):
                tool_key, tool_data = tool_info
                if isinstance(tool_data, dict):
                    name = tool_data.get("name", tool_key)
                    desc = tool_data.get("description", "No description")
                    print(f"   {i}. {name}")
                    if desc:
                        desc_short = desc[:70] + "..." if len(desc) > 70 else desc
                        print(f"      {desc_short}")
                else:
                    print(f"   {i}. {tool_key}")

            if len(tools) > 10:
                print(f"   ... and {len(tools) - 10} more")
            print()

            # Select a tool to test
            simple_tool_names = [
                "list_databases",
                "search_pages",
                "list_users",
                "get_page",
            ]

            tool_to_test: Optional[str] = None
            test_args = {}

            for tool_name in simple_tool_names:
                # Check if tool exists in registry
                for tool_key in tools.keys():
                    if tool_name in str(tool_key).lower():
                        tool_to_test = tool_name
                        if tool_name == "list_databases":
                            test_args = {}
                        elif tool_name == "search_pages":
                            test_args = {"query": "test", "limit": 5}
                        elif tool_name == "list_users":
                            test_args = {}
                        break
                if tool_to_test:
                    break

            if not tool_to_test:
                # Just use the first available tool
                first_tool = list(tools.keys())[0] if tools else None
                if first_tool:
                    tool_to_test = (
                        str(first_tool).split(":")[-1]
                        if ":" in str(first_tool)
                        else str(first_tool)
                    )
                    test_args = {}

        else:
            # Fallback: just try to execute a known tool
            tool_to_test = "list_databases"
            test_args = {}
            print("⚠️ Cannot list tools via tm.list_tools()")
            print(f"   Will attempt to execute '{tool_to_test}' directly")
            print()

    except Exception as e:
        print(f"⚠️ Error checking tool availability: {type(e).__name__}: {e}")
        print("   Will attempt tool execution anyway")
        tool_to_test = "list_databases"
        test_args = {}
        print()

    # Execute tool
    if tool_to_test:
        print(f"⚙️ Step 4: Execute Tool '{tool_to_test}'")
        print("-" * 80)
        print(f"Arguments: {json.dumps(test_args, indent=2)}")
        print("⏱️ Starting execution...")
        print()

        exec_start = time.time()

        try:
            result = await tm.execute_tool(tool_to_test, test_args)
            exec_elapsed = time.time() - exec_start

            print()
            print("=" * 80)
            print("EXECUTION RESULT")
            print("=" * 80)
            print(f"⏱️ Elapsed time: {exec_elapsed:.2f}s")
            print(
                f"✅ Success: {result.success if hasattr(result, 'success') else 'Unknown'}"
            )

            if hasattr(result, "success") and not result.success:
                print(
                    f"❌ Error: {result.error if hasattr(result, 'error') else 'Unknown'}"
                )
                print()

                # Analyze error
                if hasattr(result, "error"):
                    error_str = str(result.error)
                    print("🔍 ERROR ANALYSIS:")

                    if "timed out after" in error_str:
                        import re

                        timeout_match = re.search(
                            r"timed out after ([\d.]+)s", error_str
                        )
                        if timeout_match:
                            print(f"   🔍 Timeout value: {timeout_match.group(1)}s")

                    if "failed after" in error_str:
                        import re

                        retry_match = re.search(
                            r"failed after (\d+) attempts", error_str
                        )
                        if retry_match:
                            print(f"   🔍 Retry attempts: {retry_match.group(1)}")

                    if (
                        "execution_failed" in error_str
                        or "available.*false" in error_str
                    ):
                        print("   🔍 Error indicates wrapper/retry logic involved")

            elif hasattr(result, "content"):
                print("\n📄 Result preview:")
                content_str = str(result.content)
                if len(content_str) > 500:
                    print(f"   {content_str[:500]}...")
                    print(f"   ... ({len(content_str)} total chars)")
                else:
                    print(f"   {content_str}")

        except asyncio.TimeoutError:
            exec_elapsed = time.time() - exec_start
            print()
            print("=" * 80)
            print(f"⚠️ TIMEOUT EXCEPTION after {exec_elapsed:.2f}s")
            print("=" * 80)

        except Exception as e:
            exec_elapsed = time.time() - exec_start
            print()
            print("=" * 80)
            print(f"❌ EXCEPTION after {exec_elapsed:.2f}s")
            print("=" * 80)
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {e}")
            import traceback

            traceback.print_exc()

    # Cleanup
    print()
    print("🧹 Cleaning up...")
    try:
        await tm.close()
        print("✅ ToolManager closed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {type(e).__name__}: {e}")

    # Summary
    total_elapsed = time.time() - start_total
    print()
    print("=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"⏱️ Total elapsed time: {total_elapsed:.2f}s")
    print(f"⏱️ Initialization time: {init_elapsed:.2f}s")
    if tool_to_test:
        print(f"⏱️ Tool execution time: {exec_elapsed:.2f}s")
    print()

    print("💡 ANALYSIS:")
    print("-" * 80)

    if init_elapsed > 120:
        print("⚠️ Initialization is VERY slow (>120s)")
        print("   This includes OAuth + MCP session setup + tool listing")
        print("   Consider breaking these steps apart to identify bottleneck")
    elif init_elapsed > 60:
        print("⚠️ Initialization is slow (>60s)")
    else:
        print("✅ Initialization time is reasonable")

    if tool_to_test:
        if exec_elapsed >= 300:
            print("❌ Tool execution hit timeout (300s)")
            print("   Notion MCP appears to be extremely slow")
            print("   Recommendations:")
            print("   • Increase timeout to 600s+")
            print("   • Implement exponential backoff retry")
            print("   • Consider if Notion API itself is slow")
        elif exec_elapsed > 120:
            print(f"⚠️ Tool execution is very slow ({exec_elapsed:.1f}s)")
            print("   May need higher timeout values")
        elif exec_elapsed > 60:
            print(f"⚠️ Tool execution is slow ({exec_elapsed:.1f}s)")
        else:
            print(f"✅ Tool execution time is reasonable ({exec_elapsed:.1f}s)")

    print()
    print("✅ Diagnostic complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_notion_via_toolmanager())
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
