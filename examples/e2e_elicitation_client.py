#!/usr/bin/env python3
"""
E2E Elicitation Client - Powered by chuk-mcp
Demonstrates client handling elicitation requests from server.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize, send_tools_list, send_tools_call


async def main():
    """Test elicitation capability."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_elicitation_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        print("🔗 Initializing connection...")
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to {init_result.serverInfo.name}")
        print()

        # List available tools
        print("🔧 Listing available tools...")
        tools_result = await send_tools_list(read, write)
        for tool in tools_result.tools:
            print(f"  • {tool.name}: {tool.description}")
        print()

        # Call tool that requires elicitation
        print("📝 Calling create_account tool...")
        print(
            "   (In a real implementation, the client would handle elicitation/create requests)"
        )
        result = await send_tools_call(read, write, "create_account", {})

        # Display result
        for content_item in result.content:
            if content_item.get("type") == "text":
                print(f"\n{content_item.get('text')}")

        print("\n✅ Elicitation example completed!")


if __name__ == "__main__":
    anyio.run(main)
