#!/usr/bin/env python3
"""
E2E Sampling Client - Powered by chuk-mcp
Demonstrates client connecting to chuk-mcp server with sampling support.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.sampling import sample_text


async def main():
    """Connect to sampling demo server."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_sampling_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Sampling (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check sampling capability
        if hasattr(init_result.capabilities, "sampling"):
            print("✅ Server supports sampling capability")
            print()

            # Request AI to generate content using the helper function
            print("🤖 Server requesting AI to generate content...")

            # Use sample_text helper for simple text sampling
            result = await sample_text(
                read,
                write,
                prompt="Explain quantum computing in simple terms",
                max_tokens=1000,
                model_hint="claude",
                temperature=0.7,
            )

            print("📝 AI Generated Response:")
            # Access content properly from the CreateMessageResult type
            if hasattr(result.content, "text"):
                print(f"   {result.content.text}")
            print()
            print(f"📊 Model: {result.model}")
            print(f"🔢 Stop Reason: {result.stopReason or 'N/A'}")
            print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Sampling allows servers to request AI assistance")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
