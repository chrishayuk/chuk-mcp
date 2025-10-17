#!/usr/bin/env python3
"""
E2E Resources Client - Powered by chuk-mcp
Demonstrates client accessing resources from chuk-mcp server.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.resources import (
    send_resources_list,
    send_resources_read,
)


async def main():
    """Connect to resources demo server and read resources."""
    server_params = StdioServerParameters(
        command="python", args=["examples/e2e_resources_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("=" * 60)
        print("E2E Example: Resources (Client + Server powered by chuk-mcp)")
        print("=" * 60)
        print()

        # Initialize connection
        init_result = await send_initialize(read, write)
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Check resources capability
        if hasattr(init_result.capabilities, "resources"):
            print("✅ Server supports resources")
            print()

        # List available resources
        resources_result = await send_resources_list(read, write)
        print(f"📚 Available resources: {len(resources_result.resources)}")
        for resource in resources_result.resources:
            print(f"  • {resource.name}")
            print(f"    URI: {resource.uri}")
            if hasattr(resource, "description") and resource.description:
                print(f"    Description: {resource.description}")
            if hasattr(resource, "mimeType") and resource.mimeType:
                print(f"    Type: {resource.mimeType}")
        print()

        # Read first resource (API Reference)
        first_uri = resources_result.resources[0].uri
        print(f"📖 Reading resource: {first_uri}")
        read_result = await send_resources_read(read, write, first_uri)

        for content in read_result.contents:
            if hasattr(content, "text"):
                # Show first 200 characters
                text = content.text
                preview = text[:200] + "..." if len(text) > 200 else text
                print("   Content preview:")
                for line in preview.split("\n")[:8]:  # Show first 8 lines
                    print(f"   {line}")
                if len(text) > 200:
                    print(f"   ... ({len(text)} total characters)")
        print()

        # Read second resource (Config)
        second_uri = resources_result.resources[1].uri
        print(f"📖 Reading resource: {second_uri}")
        config_result = await send_resources_read(read, write, second_uri)

        for content in config_result.contents:
            if hasattr(content, "text"):
                print("   Full content:")
                for line in content.text.split("\n"):
                    print(f"   {line}")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Resources provide access to server data and documents")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
