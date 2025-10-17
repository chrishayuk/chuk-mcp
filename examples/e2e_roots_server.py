#!/usr/bin/env python3
"""
E2E Roots Server - Powered by chuk-mcp
Demonstrates server-side roots implementation using chuk-mcp framework.
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
    """Create and run roots demo server."""
    capabilities = ServerCapabilities(roots={"listChanged": True})
    server = MCPServer(
        name="roots-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register roots handlers
    async def handle_roots_list(message, session_id):
        """
        Handle roots/list request.

        Returns list of directory roots that client allows server to access.
        """
        roots = [
            {"uri": "file:///home/user/projects", "name": "Projects Directory"},
            {"uri": "file:///home/user/documents", "name": "Documents Directory"},
            {"uri": "file:///tmp", "name": "Temporary Files"},
        ]
        result = {"roots": roots}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_roots_list_changed(message, session_id):
        """
        Handle notifications/roots/listChanged notification.

        Sent by client when available roots have changed.
        """
        # Notifications don't require a response
        return None, None

    # Register protocol handlers
    server.protocol_handler.register_method("roots/list", handle_roots_list)
    server.protocol_handler.register_method(
        "notifications/roots/listChanged", handle_roots_list_changed
    )

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
