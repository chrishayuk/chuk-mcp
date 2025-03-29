# chuk_mcp/__main__.py
import anyio
import logging
import sys

# config
from chuk_mcp.config import load_config

# mcp
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.ping.send_messages import send_ping
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_list
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)


async def main():
    """Stripped-down script to initialize the server and send a ping."""
    config_path = "server_config.json"
    server_name = "sqlite"

    server_params = await load_config(config_path, server_name)

    async with stdio_client(server_params) as (read_stream, write_stream):
        init_result = await send_initialize(read_stream, write_stream)
        if not init_result:
            print("Server initialization failed")
            return

        print("We're connected!!!")

        result = await send_ping(read_stream, write_stream)
        print("Ping successful" if result else "Ping failed")

        result = await send_tools_list(read_stream, write_stream)
        print(result)


def run():
    """Synchronous wrapper for our async main()."""
    anyio.run(main)
