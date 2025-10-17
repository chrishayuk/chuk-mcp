#!/usr/bin/env python3
"""
E2E Ping Server - Powered by chuk-mcp
Demonstrates server-side ping/health check using chuk-mcp framework.
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
    """Create and run ping demo server."""
    capabilities = ServerCapabilities()
    server = MCPServer(
        name="ping-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Ping is handled automatically by the server protocol handler
    # No need to register a custom handler - it's built-in

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
