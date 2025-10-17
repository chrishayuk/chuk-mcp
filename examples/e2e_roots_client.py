#!/usr/bin/env python3
"""
E2E Roots Client - Powered by chuk-mcp
Demonstrates client connecting to chuk-mcp server with roots support.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.roots import (
    send_roots_list,
    send_roots_list_changed_notification,
)


async def main():
    """Connect to roots demo server."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_roots_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Roots (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check roots capability
        if (
            hasattr(init_result.capabilities, "roots")
            and init_result.capabilities.roots
        ):
            print("✅ Server supports roots capability")
            print()

            # List roots - returns typed ListRootsResult
            roots_result = await send_roots_list(read, write)

            print(f"📁 Available roots: {len(roots_result.roots)}")
            for root in roots_result.roots:
                print(f"  • {root.name}")
                print(f"    URI: {root.uri}")
            print()

            # Notify server of roots change
            await send_roots_list_changed_notification(write)
            print("📢 Sent roots list changed notification")
            print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Roots allow clients to control directory access")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
