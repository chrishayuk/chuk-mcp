"""A tiny MCP server used as a stdio fixture by the integration tests.

Built on the (Rust-backed) public ``chuk_mcp.MCPServer`` and served over stdio,
so the integration suite exercises both the client and server halves of the
public API without any external binary.
"""

import asyncio

from chuk_mcp import MCPServer, ServerCapabilities


async def main() -> None:
    server = MCPServer(
        "integration-echo",
        "1.0.0",
        capabilities=ServerCapabilities(
            tools={"listChanged": True}, resources={}
        ),
    )

    async def greet(name="world"):
        return f"Hello, {name}!"

    server.register_tool(
        "greet",
        greet,
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "Greet someone by name",
    )

    async def add(a, b):
        return {"sum": a + b}

    server.register_tool(
        "add",
        add,
        {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
        "Add two numbers",
    )

    async def motd():
        return "integration message of the day"

    server.register_resource("demo://motd", motd, "motd", "MOTD", "text/plain")

    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
