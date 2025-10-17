#!/usr/bin/env python3
"""
E2E Elicitation Server - Powered by chuk-mcp
Demonstrates server requesting user input using elicitation capability.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities, ToolsCapability
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run elicitation demo server."""
    capabilities = ServerCapabilities(tools=ToolsCapability())
    server = MCPServer(
        name="elicitation-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register tools that demonstrate elicitation
    async def handle_tools_list(message, session_id):
        """
        Handle tools/list request.

        Returns tools that use elicitation to gather user input.
        """
        tools = [
            {
                "name": "create_account",
                "description": "Create a user account by requesting information from the user",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            }
        ]
        result = {"tools": tools}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_tools_call(message, session_id):
        """
        Handle tools/call request.

        This tool demonstrates using elicitation to request user input.
        """
        params = message.params if hasattr(message, "params") else {}
        name = params.get("name") if isinstance(params, dict) else None

        if name == "create_account":
            # Create elicitation request for user information
            # In a real implementation, we would:
            # 1. Send the elicitation request to the client
            # 2. Wait for the client's response
            # 3. Process the user's input
            # For this demo, we simulate the response
            simulated_response = {
                "data": {"username": "demo_user"},
                "cancelled": False,
            }

            # Create success result
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Account created successfully for user: {simulated_response['data']['username']}\n\nNote: In a real implementation, the server would send an elicitation/create request and wait for user input.",
                    }
                ]
            }

            return server.protocol_handler.create_response(message.id, result), None

        # Unknown tool
        error = {
            "code": -32601,
            "message": f"Unknown tool: {name}",
        }
        return server.protocol_handler.create_error_response(message.id, error), None

    # Register protocol handlers
    server.protocol_handler.register_method("tools/list", handle_tools_list)
    server.protocol_handler.register_method("tools/call", handle_tools_call)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
