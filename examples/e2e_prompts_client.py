#!/usr/bin/env python3
"""
E2E Prompts Client - Powered by chuk-mcp
Demonstrates client using prompt templates from chuk-mcp server.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.prompts import send_prompts_list, send_prompts_get


async def main():
    """Connect to prompts demo server and use prompt templates."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_prompts_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Prompts (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check prompts capability
        if hasattr(init_result.capabilities, "prompts"):
            print("✅ Server supports prompts")
            print()

        # List available prompts
        prompts_result = await send_prompts_list(read, write)
        print(f"📋 Available prompt templates: {len(prompts_result.prompts)}")
        for prompt in prompts_result.prompts:
            print(f"  • {prompt.name}: {prompt.description}")
            if prompt.arguments:
                print("    Arguments:")
                for arg in prompt.arguments:
                    required = " (required)" if arg.required else ""
                    print(f"      - {arg.name}: {arg.description}{required}")
        print()

        # Get specific prompt with arguments
        print("💬 Getting 'summarize_code' prompt with arguments...")
        prompt_response = await send_prompts_get(
            read,
            write,
            name="summarize_code",
            arguments={
                "code": "def factorial(n):\\n    return 1 if n <= 1 else n * factorial(n-1)",
                "language": "Python",
            },
        )

        print(
            f"   📝 Generated prompt with {len(prompt_response.messages)} message(s):"
        )
        for i, msg in enumerate(prompt_response.messages, 1):
            text = msg.content.get("text", "")
            # Show first 150 characters
            preview = text[:150] + "..." if len(text) > 150 else text
            print(f"   {i}. {msg.role}: {preview}")
        print()

        # Get another prompt
        print("💬 Getting 'explain_error' prompt...")
        error_prompt = await send_prompts_get(
            read,
            write,
            name="explain_error",
            arguments={"error_message": "TypeError: 'int' object is not subscriptable"},
        )

        if error_prompt.messages:
            text = error_prompt.messages[0].content.get("text", "")
            preview = text[:120] + "..." if len(text) > 120 else text
            print(f"   📝 {preview}")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Prompts provide reusable templates for AI interactions")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
