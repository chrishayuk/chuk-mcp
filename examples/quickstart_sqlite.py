#!/usr/bin/env python3
"""
Real-World Example: SQLite Database Tools
This example is from the README Quick Start section.

Prerequisites:
  uv tool install mcp-server-sqlite
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call
from chuk_mcp.protocol.types.content import parse_content, TextContent


async def main():
    # Connect to SQLite MCP server
    server_params = StdioServerParameters(
        command="uvx", args=["mcp-server-sqlite", "--db-path", "example.db"]
    )

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        result = await send_initialize(read, write)
        print(f"Connected: {result.serverInfo.name}")

        # List available tools - returns typed ListToolsResult
        tools_result = await send_tools_list(read, write)
        print(f"Available tools: {len(tools_result.tools)}")
        for tool in tools_result.tools:
            print(f"  • {tool.name}: {tool.description}")

        # Execute a query - returns typed ToolResult
        result = await send_tools_call(
            read, write, name="read_query", arguments={"query": "SELECT 1 as test"}
        )
        # Parse content into proper types
        content = parse_content(result.content[0])
        assert isinstance(content, TextContent)
        print(f"Query result: {content.text}")


if __name__ == "__main__":
    anyio.run(main)
