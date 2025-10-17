#!/usr/bin/env python3
"""
E2E Subscriptions Server - Powered by chuk-mcp
Demonstrates server-side resource subscriptions using chuk-mcp framework.
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
    """Create and run subscriptions demo server."""
    capabilities = ServerCapabilities(
        resources={"subscribe": True, "listChanged": True}
    )
    server = MCPServer(
        name="subscriptions-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Track active subscriptions
    subscriptions = set()

    # Register resource handlers
    async def handle_resources_list(message, session_id):
        """
        Handle resources/list request.

        Returns list of available resources that can be subscribed to.
        """
        resources = [
            {
                "uri": "file:///logs/app.log",
                "name": "Application Log",
                "mimeType": "text/plain",
            },
            {
                "uri": "file:///data/metrics.json",
                "name": "System Metrics",
                "mimeType": "application/json",
            },
        ]
        result = {"resources": resources}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_resources_subscribe(message, session_id):
        """
        Handle resources/subscribe request.

        Adds URI to active subscriptions for change notifications.
        """
        params = message.params if hasattr(message, "params") else {}
        uri = params.get("uri") if isinstance(params, dict) else None

        if uri:
            subscriptions.add(uri)

        return server.protocol_handler.create_response(message.id, {}), None

    async def handle_resources_unsubscribe(message, session_id):
        """
        Handle resources/unsubscribe request.

        Removes URI from active subscriptions.
        """
        params = message.params if hasattr(message, "params") else {}
        uri = params.get("uri") if isinstance(params, dict) else None

        if uri and uri in subscriptions:
            subscriptions.remove(uri)

        return server.protocol_handler.create_response(message.id, {}), None

    # Register protocol handlers
    server.protocol_handler.register_method("resources/list", handle_resources_list)
    server.protocol_handler.register_method(
        "resources/subscribe", handle_resources_subscribe
    )
    server.protocol_handler.register_method(
        "resources/unsubscribe", handle_resources_unsubscribe
    )

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
