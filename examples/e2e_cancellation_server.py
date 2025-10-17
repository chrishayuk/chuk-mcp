#!/usr/bin/env python3
"""
E2E Cancellation Server - Powered by chuk-mcp
Demonstrates server-side operation cancellation using chuk-mcp framework.
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
    """Create and run cancellation demo server."""
    capabilities = ServerCapabilities()
    server = MCPServer(
        name="cancellation-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register cancellation handler
    async def handle_cancelled(message, session_id):
        """
        Handle notifications/cancelled notification.

        Sent by client to request cancellation of a long-running operation.
        """
        # Extract cancellation info (not used in this demo, but would be in production)
        # params = message.params if hasattr(message, "params") else {}
        # request_id = params.get("requestId") if isinstance(params, dict) else None
        # reason = params.get("reason", "No reason provided") if isinstance(params, dict) else "No reason provided"

        # In a real server, this would stop the operation with the given request_id
        # For demo, we just acknowledge it
        # Notifications don't require a response
        return None, None

    # Register protocol handler
    server.protocol_handler.register_method("notifications/cancelled", handle_cancelled)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
