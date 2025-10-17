#!/usr/bin/env python3
"""
Minimal Demo - No External Dependencies Required
This example is from the README Quick Start section.
"""

import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize


async def main():
    # Create a minimal echo server inline
    server_params = StdioServerParameters(
        command="python",
        args=[
            "-c",
            """
import json, sys
init = json.loads(input())
resp = {
  "id": init["id"],
  "result": {
    "serverInfo": {"name": "Demo", "version": "1.0"},
    "protocolVersion": "2025-06-18",
    "capabilities": {}
  }
}
print(json.dumps(resp))
""",
        ],
    )

    async with stdio_client(server_params) as (read, write):
        result = await send_initialize(read, write)
        print(f"✅ Connected to {result.serverInfo.name}")


if __name__ == "__main__":
    anyio.run(main)
