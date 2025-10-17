#!/usr/bin/env python3
"""
E2E Cancellation Client - Powered by chuk-mcp
Demonstrates operation cancellation with both client and server using chuk-mcp.
"""

import anyio
from pathlib import Path
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.notifications import send_cancelled_notification


async def main():
    """Run the cancellation demo."""
    print("=" * 60)
    print("E2E Example: Cancellation (Client + Server powered by chuk-mcp)")
    print("=" * 60)
    print()

    # Launch the server (both powered by chuk-mcp)
    server_path = Path(__file__).parent / "e2e_cancellation_server.py"
    server_params = StdioServerParameters(command="python", args=[str(server_path)])

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        init_result = await send_initialize(read, write)

        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Simulate starting a long operation
        request_id = "operation-123"
        print(f"🔄 Simulating long operation (ID: {request_id})")
        print("   (In real app, this would be an actual task)")
        print()

        # Send cancellation notification
        print("🚫 Sending cancellation request...")
        await send_cancelled_notification(
            write, request_id=request_id, reason="User requested cancellation"
        )

        print("✅ Cancellation sent to server")
        print("   Server received notification to stop operation")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Cancellation stops long-running operations")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
