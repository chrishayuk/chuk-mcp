#!/usr/bin/env python3
"""
E2E Logging Server - Powered by chuk-mcp
Demonstrates server-side logging capability using chuk-mcp framework.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import (
    ServerCapabilities,
    LoggingCapability,
    ToolsCapability,
)
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run logging demo server."""
    capabilities = ServerCapabilities(
        logging=LoggingCapability(), tools=ToolsCapability()
    )
    server = MCPServer(
        name="logging-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Track current log level
    current_log_level = "info"

    # Register logging/setLevel handler
    async def handle_logging_set_level(message, session_id):
        """
        Handle logging/setLevel request.

        Client requests server to change its logging level.
        """
        nonlocal current_log_level
        params = message.params if hasattr(message, "params") else {}
        level = params.get("level") if isinstance(params, dict) else "info"

        current_log_level = level
        # In a real implementation, this would configure the server's logging
        # logging.getLogger().setLevel(getattr(logging, level.upper()))

        result = {}
        return server.protocol_handler.create_response(message.id, result), None

    # Register tools that demonstrate logging
    async def handle_tools_list(message, session_id):
        """Handle tools/list request."""
        tools = [
            {
                "name": "process_data",
                "description": "Process data and send log messages to client",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Data to process",
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

        This tool sends log messages to demonstrate logging capability.
        """
        params = message.params if hasattr(message, "params") else {}
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments", {}) if isinstance(params, dict) else {}

        if name == "process_data":
            data = arguments.get("data", "")

            # In a real implementation, the server would send notifications/message
            # to the client with log entries at various levels
            # For this demo, we describe what would happen

            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Processed data: {data}\n\nCurrent log level: {current_log_level}\n\nNote: In a real implementation, the server would send notifications/message with:\n- level: 'debug'|'info'|'warning'|'error'\n- logger: name of the logger\n- data: log message content",
                    }
                ]
            }

            return server.protocol_handler.create_response(message.id, result), None

        # Unknown tool
        error = {"code": -32601, "message": f"Unknown tool: {name}"}
        return server.protocol_handler.create_error_response(message.id, error), None

    # Register protocol handlers
    server.protocol_handler.register_method(
        "logging/setLevel", handle_logging_set_level
    )
    server.protocol_handler.register_method("tools/list", handle_tools_list)
    server.protocol_handler.register_method("tools/call", handle_tools_call)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
