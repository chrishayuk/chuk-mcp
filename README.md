# chuk-mcp

A Python client implementation for the Model Context Protocol (MCP).

[![PyPI version](https://badge.fury.io/py/chuk-mcp.svg)](https://badge.fury.io/py/chuk-mcp)
[![Python Version](https://img.shields.io/pypi/pyversions/chuk-mcp)](https://pypi.org/project/chuk-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is MCP?

The Model Context Protocol (MCP) is a standardized protocol for LLM applications to communicate with their context providers. This allows for standardized access to tools, prompts, and resources that LLMs can use during inference.

This client implementation provides a Python interface to interact with MCP servers.

## Features

- Protocol version negotiation with servers
- Resource management
- Tool execution
- Prompt retrieval
- Resilient communication with automatic retries
- Support for stdio-based transport

## Installation

```bash
pip install chuk-mcp
```

For development:

```bash
pip install chuk-mcp[dev]
```

## Usage

### Basic Connection

```python
import anyio
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.ping.send_messages import send_ping

async def main():
    # Configure the server parameters
    server_params = StdioServerParameters(
        command="path/to/mcp/server",
        args=["--some-option", "value"],
    )
    
    # Connect to the server
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Initialize the connection
        init_result = await send_initialize(read_stream, write_stream)
        if not init_result:
            print("Server initialization failed")
            return
        
        # Send a ping to verify connection
        ping_result = await send_ping(read_stream, write_stream)
        print("Ping successful" if ping_result else "Ping failed")

# Run the async function
anyio.run(main)
```

### Loading Configuration

```python
import anyio
from chuk_mcp.config import load_config
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize

async def main():
    # Load the server configuration from a JSON file
    server_params = await load_config("server_config.json", "sqlite")
    
    # Connect to the server using the configuration
    async with stdio_client(server_params) as (read_stream, write_stream):
        init_result = await send_initialize(read_stream, write_stream)
        if init_result:
            print("Connected to server:", init_result.serverInfo.name)

# Run the async function
anyio.run(main)
```

### Working with Tools

```python
import anyio
from chuk_mcp.config import load_config
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_list, send_tools_call

async def main():
    server_params = await load_config("server_config.json", "sqlite")
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Initialize the connection
        await send_initialize(read_stream, write_stream)
        
        # List available tools
        tools_response = await send_tools_list(read_stream, write_stream)
        for tool in tools_response.get("tools", []):
            print(f"Available tool: {tool['name']} - {tool['description']}")
        
        # Call a tool
        result = await send_tools_call(
            read_stream,
            write_stream,
            name="get_weather",
            arguments={"location": "San Francisco"},
        )
        print("Tool result:", result)

# Run the async function
anyio.run(main)
```

### Working with Resources

```python
import anyio
from chuk_mcp.config import load_config
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.resources.send_messages import send_resources_list, send_resources_read

async def main():
    server_params = await load_config("server_config.json", "filesystem")
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Initialize the connection
        await send_initialize(read_stream, write_stream)
        
        # List available resources
        resources_response = await send_resources_list(read_stream, write_stream)
        
        # Find and read a specific resource
        for resource in resources_response.get("resources", []):
            if resource["name"].endswith(".py"):
                content = await send_resources_read(read_stream, write_stream, resource["uri"])
                print(f"Content of {resource['name']}:")
                print(content.get("contents", [{}])[0].get("text", ""))
                break

# Run the async function
anyio.run(main)
```

## Configuration

Create a `server_config.json` file to configure your MCP servers:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "test.db"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/directory"
      ]
    }
  }
}
```

## Development

### Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
make test
```

or

```bash
pytest
```

### Building the Package

```bash
make build
```

## License

MIT

## Acknowledgements

This implementation follows the Model Context Protocol specification.