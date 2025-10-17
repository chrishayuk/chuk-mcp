#!/usr/bin/env python3
"""
E2E Completion Client - Powered by chuk-mcp
Demonstrates smart autocomplete with both client and server using chuk-mcp.
"""

import anyio
from pathlib import Path
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.completions import complete_resource_argument


async def main():
    """Run the completion demo."""
    print("=" * 60)
    print("E2E Example: Completion (Client + Server powered by chuk-mcp)")
    print("=" * 60)
    print()

    # Launch the server (both powered by chuk-mcp)
    server_path = Path(__file__).parent / "e2e_completion_server.py"
    server_params = StdioServerParameters(command="python", args=[str(server_path)])

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        init_result = await send_initialize(read, write)

        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check capability
        if hasattr(init_result.capabilities, "completion"):
            print("✅ Server supports completion")
            print()

        # Get completions for partial input using the helper function
        print("💡 Getting completions for 'sales_2024':")
        result = await complete_resource_argument(
            read,
            write,
            resource_uri="file:///data/",
            argument_name="filename",
            argument_value="sales_2024",
        )

        # Access completion values directly from CompletionResult
        for completion in result.values:
            print(f"  • {completion}")
        print()

        # Try another partial match
        print("💡 Getting completions for 'sales_202':")
        result = await complete_resource_argument(
            read,
            write,
            resource_uri="file:///data/",
            argument_name="filename",
            argument_value="sales_202",
        )

        # Access completion values directly from CompletionResult
        for completion in result.values:
            print(f"  • {completion}")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Completion enables intelligent autocomplete")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
