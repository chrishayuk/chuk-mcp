#!/usr/bin/env python3
"""
Working with Resources (File Access)
This example is from the README Quick Start section.

Note: This example demonstrates the resources API, but requires a server
that implements resources support. The filesystem server uses tools instead.

For a working example with filesystem server, see the tools example.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.resources import (
    send_resources_list,
    send_resources_read,
)


async def main():
    """
    This example shows the resources API pattern.

    Note: @modelcontextprotocol/server-filesystem uses tools instead of resources.
    To test resources, you need a server that implements the resources capability.

    Check server capabilities with:
        init_result.capabilities.resources
    """
    # Example server parameters - adjust for your server
    server_params = StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "example.db"],  # SQLite has resources
    )

    async with stdio_client(server_params) as (read, write):
        # Initialize
        init_result = await send_initialize(read, write)

        # Check if server supports resources
        if not hasattr(init_result.capabilities, "resources"):
            print("⚠️  Server does not support resources capability")
            print("    The filesystem server uses tools instead.")
            print("    Try: uv run examples/README_example_2_sqlite.py")
            return

        # List resources - returns typed ListResourcesResult
        result = await send_resources_list(read, write)
        print(f"Found {len(result.resources)} resources")

        for resource in result.resources:
            print(f"  • {resource.name}")
            print(f"    URI: {resource.uri}")

        # Read a specific file - returns typed ReadResourceResult
        if result.resources:
            uri = result.resources[0].uri
            read_result = await send_resources_read(read, write, uri)
            # Access typed content directly
            content = read_result.contents[0]
            if hasattr(content, "text"):
                print(f"\nContent preview: {content.text[:100]}...")


if __name__ == "__main__":
    anyio.run(main)
