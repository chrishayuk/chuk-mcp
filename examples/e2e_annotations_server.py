#!/usr/bin/env python3
"""
E2E Annotations Server - Powered by chuk-mcp
Demonstrates using annotations to provide metadata about content.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities, ToolsCapability
from chuk_mcp.protocol.types.content import create_annotations
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run annotations demo server."""
    capabilities = ServerCapabilities(tools=ToolsCapability())
    server = MCPServer(
        name="annotations-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register tools that use annotations
    async def handle_tools_list(message, session_id):
        """
        Handle tools/list request.

        Returns tools that demonstrate annotations usage.
        """
        tools = [
            {
                "name": "analyze_data",
                "description": "Analyze data and return results with different priority levels",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Data to analyze",
                        }
                    },
                    "required": ["data"],
                },
            }
        ]
        result = {"tools": tools}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_tools_call(message, session_id):
        """
        Handle tools/call request.

        This tool demonstrates using annotations to indicate content priority and audience.
        """
        params = message.params if hasattr(message, "params") else {}
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments", {}) if isinstance(params, dict) else {}

        if name == "analyze_data":
            data = arguments.get("data", "")

            # Return multiple content items with different annotations
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"[CRITICAL] Found security issue in: {data}",
                        "annotations": create_annotations(
                            audience=["user", "assistant"], priority=1.0
                        ).model_dump(),
                    },
                    {
                        "type": "text",
                        "text": f"Analysis summary: {len(data)} bytes processed",
                        "annotations": create_annotations(
                            audience=["assistant"], priority=0.5
                        ).model_dump(),
                    },
                    {
                        "type": "text",
                        "text": "Debug info: processing completed successfully",
                        "annotations": create_annotations(
                            audience=["assistant"], priority=0.1
                        ).model_dump(),
                    },
                ]
            }

            return server.protocol_handler.create_response(message.id, result), None

        # Unknown tool
        error = {"code": -32601, "message": f"Unknown tool: {name}"}
        return server.protocol_handler.create_error_response(message.id, error), None

    # Register protocol handlers
    server.protocol_handler.register_method("tools/list", handle_tools_list)
    server.protocol_handler.register_method("tools/call", handle_tools_call)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
