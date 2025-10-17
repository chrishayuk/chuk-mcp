#!/usr/bin/env python3
"""
E2E Completion Server - Powered by chuk-mcp
Demonstrates server-side completion/autocomplete using chuk-mcp framework.
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
    """Create and run completion demo server."""
    capabilities = ServerCapabilities(completion={})
    server = MCPServer(
        name="completion-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register completion handler
    async def handle_completion_complete(message, session_id):
        """
        Handle completion/complete request.

        Provides intelligent autocomplete suggestions based on partial input.
        """
        # Access params - message is already a Pydantic model
        params = message.params if hasattr(message, "params") else {}
        arg = params.get("argument", {}) if isinstance(params, dict) else {}
        partial = arg.get("value", "")

        # Simulate intelligent completions for file names
        all_options = [
            "sales_2024_q1.csv",
            "sales_2024_q2.csv",
            "sales_2024_q3.csv",
            "sales_2023_annual.csv",
            "customers.json",
            "products.json",
        ]

        # Filter based on partial input
        matches = [opt for opt in all_options if opt.startswith(partial)]

        # Return completion result
        result = {
            "completion": {
                "values": matches[:5],  # Top 5 matches
                "total": len(matches),
                "hasMore": len(matches) > 5,
            }
        }

        return server.protocol_handler.create_response(message.id, result), None

    # Register protocol handler
    server.protocol_handler.register_method(
        "completion/complete", handle_completion_complete
    )

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
