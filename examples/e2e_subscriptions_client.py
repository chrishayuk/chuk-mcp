#!/usr/bin/env python3
"""
E2E Subscriptions Client - Powered by chuk-mcp
Demonstrates resource subscriptions with both client and server using chuk-mcp.
"""

import anyio
from pathlib import Path
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.resources import (
    send_resources_list,
    send_resources_subscribe,
    send_resources_unsubscribe,
)


async def main():
    """Run the subscriptions demo."""
    print("=" * 60)
    print("E2E Example: Subscriptions (Client + Server powered by chuk-mcp)")
    print("=" * 60)
    print()

    # Launch the server (both powered by chuk-mcp)
    server_path = Path(__file__).parent / "e2e_subscriptions_server.py"
    server_params = StdioServerParameters(command="python", args=[str(server_path)])

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        init_result = await send_initialize(read, write)

        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check capability
        if (
            hasattr(init_result.capabilities, "resources")
            and init_result.capabilities.resources
        ):
            if hasattr(init_result.capabilities.resources, "subscribe"):
                print("✅ Server supports resource subscriptions")
                print()

        # List resources - returns typed ListResourcesResult
        result = await send_resources_list(read, write)
        print(f"📚 Available resources: {len(result.resources)}")
        for resource in result.resources:
            print(f"  • {resource.name}")
            print(f"    URI: {resource.uri}")
        print()

        # Subscribe to first resource
        uri = result.resources[0].uri
        print(f"📡 Subscribing to: {uri}")
        await send_resources_subscribe(read, write, uri)
        print("✅ Subscribed successfully")
        print("   (Server will notify on changes)")
        print()

        # Unsubscribe
        await send_resources_unsubscribe(read, write, uri)
        print("🔕 Unsubscribed from resource")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Subscriptions enable real-time resource updates")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
