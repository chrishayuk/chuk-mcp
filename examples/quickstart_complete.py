#!/usr/bin/env python3
"""
Complete Example: Multi-Feature Demo
This example is from the README Quick Start section.

Prerequisites:
  uv tool install mcp-server-sqlite
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call
from chuk_mcp.protocol.messages.resources import send_resources_list
from chuk_mcp.protocol.messages.prompts import send_prompts_list
from chuk_mcp.protocol.types.content import parse_content, TextContent


async def full_demo():
    server_params = StdioServerParameters(
        command="uvx", args=["mcp-server-sqlite", "--db-path", "demo.db"]
    )

    async with stdio_client(server_params) as (read, write):
        # 1. Initialize
        print("1. Initializing...")
        init = await send_initialize(read, write)
        print(f"   ✅ {init.serverInfo.name} v{init.serverInfo.version}")

        # 2. Discover tools
        print("2. Discovering tools...")
        tools_result = await send_tools_list(read, write)
        print(f"   ✅ {len(tools_result.tools)} tools available")

        # 3. Call a tool
        print("3. Calling tool...")
        result = await send_tools_call(
            read,
            write,
            name="read_query",
            arguments={"query": "SELECT sqlite_version()"},
        )
        # Parse content
        content = parse_content(result.content[0])
        assert isinstance(content, TextContent)
        print(f"   ✅ Result: {content.text}")

        # 4. List resources
        print("4. Listing resources...")
        resources_result = await send_resources_list(read, write)
        print(f"   ✅ {len(resources_result.resources)} resources")

        # 5. List prompts
        print("5. Listing prompts...")
        prompts_result = await send_prompts_list(read, write)
        print(f"   ✅ {len(prompts_result.prompts)} prompts")


if __name__ == "__main__":
    anyio.run(full_demo)
