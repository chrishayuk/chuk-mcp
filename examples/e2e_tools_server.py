#!/usr/bin/env python3
"""
E2E Tools Server - Powered by chuk-mcp
Demonstrates server-side tool implementation using chuk-mcp framework.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run tools demo server."""
    capabilities = ServerCapabilities(tools={"listChanged": True})
    server = MCPServer(
        name="tools-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register tools
    async def greet(name: str) -> str:
        return f"Hello, {name}! 👋"

    server.register_tool(
        name="greet",
        handler=greet,
        schema={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Person's name"}},
            "required": ["name"],
        },
        description="Greet someone by name",
    )

    async def add(a: float, b: float) -> str:
        result = a + b
        return f"{a} + {b} = {result}"

    server.register_tool(
        name="add",
        handler=add,
        schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
        description="Add two numbers together",
    )

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
