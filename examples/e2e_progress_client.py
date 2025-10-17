#!/usr/bin/env python3
"""
E2E Progress Client - Powered by chuk-mcp
Demonstrates progress tracking with both client and server using chuk-mcp.
"""

import anyio
from pathlib import Path
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.json_rpc_message import create_request
from chuk_mcp.protocol.messages.tools import ToolResult
from chuk_mcp.protocol.types.tools import CallToolParams
from chuk_mcp.protocol.types.content import parse_content, TextContent


async def call_tool_with_progress_tracking(read, write, name: str, arguments: dict):
    """
    Call a tool and track progress notifications.

    Uses chuk-mcp message types and helper functions for all communication.
    Manually listens for progress notifications during tool execution.
    """
    # Track progress updates
    progress_updates = []

    async def on_progress(token, progress, total, message):
        """Handle progress notification."""
        percentage = int((progress / total) * 100) if total else 0
        print(f"   📊 Progress: {percentage}% ({progress}/{total})")
        progress_updates.append((progress, total))

    # Create properly typed tool call params using chuk-mcp types
    tool_params = CallToolParams(name=name, arguments=arguments)
    request_id = "progress-call-1"

    # Send tool call request using create_request (could use send_tools_call but
    # we need to listen for progress notifications which requires manual handling)
    request = create_request(
        method="tools/call",
        params=tool_params.model_dump(exclude_none=True),
        id=request_id,
    )
    await write.send(request)

    # Listen for progress notifications and response
    result = None
    while result is None:
        message = await read.receive()

        # Check if it's a progress notification
        if hasattr(message, "method") and message.method == "notifications/progress":
            # Extract params from notification
            params = getattr(message, "params", {})
            await on_progress(
                params.get("progressToken")
                if isinstance(params, dict)
                else getattr(params, "progressToken", None),
                params.get("progress", 0)
                if isinstance(params, dict)
                else getattr(params, "progress", 0),
                params.get("total")
                if isinstance(params, dict)
                else getattr(params, "total", None),
                params.get("message")
                if isinstance(params, dict)
                else getattr(params, "message", None),
            )
            continue

        # Check if it's the response
        if hasattr(message, "id") and message.id == request_id:
            if hasattr(message, "result"):
                result = message.result
            else:
                result = message.model_dump().get("result")

    # Parse into ToolResult type for type safety
    return ToolResult.model_validate(result) if result else None


async def main():
    """Run the progress demo."""
    print("=" * 60)
    print("E2E Example: Progress (Client + Server powered by chuk-mcp)")
    print("=" * 60)
    print()

    # Launch the server (both powered by chuk-mcp)
    server_path = Path(__file__).parent / "e2e_progress_server.py"
    server_params = StdioServerParameters(command="python", args=[str(server_path)])

    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        init_result = await send_initialize(read, write)

        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Protocol version: {init_result.protocolVersion}")
        print()

        # Call long-running tool with progress tracking
        print("🔄 Starting long operation...")
        print("   Listening for progress updates:")
        print()

        result: ToolResult = await call_tool_with_progress_tracking(
            read, write, name="process_dataset", arguments={"dataset": "sales_data.csv"}
        )

        print()
        print("✅ Operation complete!")
        # Parse content into proper Pydantic types
        content = parse_content(result.content[0])
        assert isinstance(content, TextContent)
        print(f"   {content.text}")
        print()

        print("=" * 60)
        print("✅ E2E Test Complete!")
        print("   Both client and server powered by chuk-mcp")
        print("   💡 Server sent real-time progress notifications!")
        print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
