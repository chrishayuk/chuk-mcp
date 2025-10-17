"""
Server Helper Functions for chuk-mcp E2E Examples

These helpers provide reusable patterns for implementing MCP servers.
In the future, these could be moved into chuk_mcp.server.transports module.
"""

import asyncio
import json
import sys
import logging
from typing import Optional

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

logger = logging.getLogger(__name__)


async def run_stdio_server(mcp_server: MCPServer):
    """
    Run an MCP server using stdio transport.

    This provides a clean interface for stdio-based servers, handling all the
    low-level stdin/stdout communication and delegating to the MCPServer
    for protocol handling.

    Args:
        mcp_server: The MCPServer instance with registered handlers

    Note:
        This function could be moved to chuk_mcp.transports.stdio.stdio_server
        to provide first-class server-side transport support.
    """
    # Set up async stdin reading
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    try:
        while True:
            # Read line from stdin
            line = await reader.readline()
            if not line:
                logger.debug("EOF on stdin, shutting down")
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            # Parse JSON-RPC message
            message_dict: Optional[dict] = None
            try:
                message_dict = json.loads(line_str)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON decode error: {e}")
                continue

            # Handle message with MCPServer
            try:
                json_rpc_msg = JSONRPCMessage.model_validate(message_dict)
                response_msg, _ = await mcp_server.protocol_handler.handle_message(
                    json_rpc_msg, session_id=None
                )

                # Send response if not a notification
                if response_msg:
                    response_dict = response_msg.model_dump(exclude_none=True)
                    print(json.dumps(response_dict), flush=True)

            except Exception as e:
                # Only send error responses for requests (not notifications)
                if message_dict is not None:
                    msg_id = message_dict.get("id")
                    if msg_id is not None:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {"code": -32603, "message": str(e)},
                        }
                        print(json.dumps(error_response), flush=True)

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
