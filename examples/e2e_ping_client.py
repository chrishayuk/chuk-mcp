#!/usr/bin/env python3
"""
E2E Ping Client - Powered by chuk-mcp
Demonstrates client health checks using chuk-mcp ping functionality.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize, send_ping


async def main():
    """Connect to ping demo server and perform health checks."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_ping_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Ping (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Perform health checks
        print("🏓 Performing health checks...")
        print()

        for i in range(5):
            success = await send_ping(read, write)
            status = "✅ PONG" if success else "❌ FAILED"
            print(f"   Ping {i + 1}: {status}")
            await anyio.sleep(0.5)  # Small delay between pings

        print()
        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Ping enables health checks and connection monitoring")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
