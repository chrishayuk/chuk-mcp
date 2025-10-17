#!/usr/bin/env python3
"""
E2E Progress Server - Powered by chuk-mcp
Demonstrates server-side progress tracking using chuk-mcp framework.
"""

import asyncio
import logging
import sys
import json
from typing import Optional
import anyio

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.protocol.messages.notifications import send_progress_notification

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def run_progress_server(mcp_server: MCPServer):
    """
    Run progress demo server with stdio transport.

    Custom version that sends progress notifications during tool execution.
    Uses chuk-mcp send_progress_notification helper function.
    """
    # Set up async stdin reading
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    # Create memory stream for sending progress notifications
    write_send, write_recv = anyio.create_memory_object_stream(100)

    # Helper to send notifications to stdout (non-blocking)
    def send_notification_to_stdout(notification: JSONRPCMessage):
        """Send notification immediately to stdout."""
        notification_dict = notification.model_dump(exclude_none=True)
        print(json.dumps(notification_dict), flush=True)

    # Set up callback for send_progress_notification to actually write
    async def write_progress(notification):
        """Intercept and write progress notifications."""
        send_notification_to_stdout(notification)

    try:
        while True:
            # Read line from stdin
            line = await reader.readline()
            if not line:
                logging.debug("EOF on stdin, shutting down")
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            # Parse JSON-RPC message
            message_dict: Optional[dict] = None
            try:
                message_dict = json.loads(line_str)
            except json.JSONDecodeError as e:
                logging.debug(f"JSON decode error: {e}")
                continue

            # Handle message with MCPServer
            try:
                json_rpc_msg = JSONRPCMessage.model_validate(message_dict)

                # Special handling for tools/call to send progress notifications
                if (
                    hasattr(json_rpc_msg, "method")
                    and json_rpc_msg.method == "tools/call"
                ):
                    # Use send_progress_notification helper - proper chuk-mcp message function
                    await send_progress_notification(
                        write_send,
                        progress_token="progress-123",
                        progress=250,
                        total=1000,
                    )
                    # Write notification from stream
                    notification = await write_recv.receive()
                    send_notification_to_stdout(notification)
                    await asyncio.sleep(0.2)

                    await send_progress_notification(
                        write_send,
                        progress_token="progress-123",
                        progress=500,
                        total=1000,
                    )
                    notification = await write_recv.receive()
                    send_notification_to_stdout(notification)
                    await asyncio.sleep(0.2)

                    await send_progress_notification(
                        write_send,
                        progress_token="progress-123",
                        progress=750,
                        total=1000,
                    )
                    notification = await write_recv.receive()
                    send_notification_to_stdout(notification)
                    await asyncio.sleep(0.2)

                # Handle message normally
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
        logging.error(f"Server error: {e}")
        raise


async def main():
    """Create and run progress demo server."""
    capabilities = ServerCapabilities(tools={})
    server = MCPServer(
        name="progress-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register tool
    async def process_dataset(dataset: str) -> str:
        """Process a dataset with progress tracking."""
        return f"Dataset '{dataset}' processed successfully. 1000 rows analyzed."

    server.register_tool(
        name="process_dataset",
        handler=process_dataset,
        schema={
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "Dataset to process"}
            },
            "required": ["dataset"],
        },
        description="Process a large dataset with progress tracking",
    )

    # Run server with progress support
    await run_progress_server(server)


if __name__ == "__main__":
    asyncio.run(main())
