#!/usr/bin/env python3
"""
E2E Annotations Client - Powered by chuk-mcp
Demonstrates client handling content with annotations.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize, send_tools_list, send_tools_call


async def main():
    """Test annotations with tool results."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_annotations_server.py"]
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

        # Call tool that returns annotated content
        print("📊 Calling analyze_data tool...")
        result = await send_tools_call(
            read, write, "analyze_data", {"data": "sensitive_data"}
        )

        # Display result with annotations
        print("\n📋 Results with annotations:\n")
        for i, content_item in enumerate(result.content, 1):
            if content_item.get("type") == "text":
                text = content_item.get("text")
                annotations = content_item.get("annotations", {})

                print(f"{i}. {text}")
                if annotations:
                    audience = annotations.get("audience", [])
                    priority = annotations.get("priority")
                    print(f"   📌 Audience: {', '.join(audience)}")
                    print(f"   ⭐ Priority: {priority}")
                print()

        print("✅ Annotations example completed!")
        print(
            "\n💡 Annotations help clients understand:\n"
            "   • Who the content is for (audience: user/assistant)\n"
            "   • How important it is (priority: 0.0-1.0)"
        )


if __name__ == "__main__":
    anyio.run(main)
