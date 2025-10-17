#!/usr/bin/env python3
"""
E2E Tools Client - Powered by chuk-mcp
Demonstrates client connecting to chuk-mcp server.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call
from chuk_mcp.protocol.types.content import parse_content, TextContent


async def main():
    """Connect to tools demo server and call tools."""
    # Launch our chuk-mcp server
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_tools_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Tools (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Version: {init_result.serverInfo.version}")
        print()

        # List available tools - returns typed ListToolsResult
        tools_result = await send_tools_list(read, write)
        print(f"🔧 Available tools: {len(tools_result.tools)}")
        for tool in tools_result.tools:
            print(f"  • {tool.name}: {tool.description}")
        print()

        # Call the greet tool - returns typed ToolResult
        print("📞 Calling tool: greet")
        greet_result = await send_tools_call(
            read, write, name="greet", arguments={"name": "World"}
        )
        # Parse content into proper Pydantic types
        content = parse_content(greet_result.content[0])
        assert isinstance(content, TextContent)
        print(f"   Response: {content.text}")
        print()

        # Call the add tool - returns typed ToolResult
        print("📞 Calling tool: add")
        add_result = await send_tools_call(
            read, write, name="add", arguments={"a": 42, "b": 23}
        )
        # Parse content into proper Pydantic types
        content = parse_content(add_result.content[0])
        assert isinstance(content, TextContent)
        print(f"   Response: {content.text}")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
