# chuk-mcp Examples

This directory contains comprehensive examples demonstrating all features of the chuk-mcp library.

## Quick Start Examples

Simple examples to get started quickly:

- **quickstart_minimal.py** - Minimal MCP client setup
- **quickstart_sqlite.py** - Working with SQLite MCP server
- **quickstart_resources.py** - Accessing server resources
- **quickstart_complete.py** - Multi-feature demo
- **README_EXAMPLES.md** - Detailed documentation for quick start examples

## End-to-End (E2E) Examples

Complete client-server pairs demonstrating each MCP feature using stdio transport. Each pair includes a client and server implementation:

### Core Features

- **e2e_tools** - Tool registration, discovery, and invocation
  - Server registers callable tools with schemas
  - Client discovers and calls tools

- **e2e_resources** - Resource listing and reading
  - Server exposes resources (documents, data, configs)
  - Client lists and reads resource contents

- **e2e_prompts** - Reusable prompt templates
  - Server provides parameterized prompt templates
  - Client gets prompts with arguments applied

### Advanced Features

- **e2e_roots** - File system root management
  - Server exposes available file system roots
  - Client can notify when roots change

- **e2e_sampling** - Server-initiated LLM requests
  - Server requests client to sample from LLM
  - Client handles approval and model selection

- **e2e_completion** - Autocomplete functionality
  - Server provides intelligent completions
  - Client requests completions for partial input

- **e2e_subscriptions** - Resource change notifications
  - Server notifies on resource changes
  - Client subscribes/unsubscribes to resources

- **e2e_cancellation** - Operation cancellation
  - Client can cancel long-running operations
  - Server handles cancellation notifications

- **e2e_progress** - Progress tracking
  - Server sends progress updates during operations
  - Client receives and displays progress

- **e2e_ping** - Health checks and connection monitoring
  - Client sends ping requests
  - Server responds to maintain connection

- **e2e_elicitation** - Server-initiated user input requests
  - Server requests user input during operations
  - Client handles elicitation requests from server

- **e2e_logging** - Log message handling
  - Server sends log messages to client
  - Client sets logging level on server

- **e2e_annotations** - Content metadata and prioritization
  - Server attaches annotations to content (audience, priority)
  - Client uses annotations to display/filter content

## Helper Files

- **server_helpers.py** - Shared utilities for server implementations

## Running Examples

### E2E Examples

Each E2E example is self-contained. Simply run the client:

```bash
python examples/e2e_tools_client.py
```

The client will automatically start the corresponding server.

### Quick Start Examples

Quick start examples demonstrate working with external MCP servers:

```bash
# Install external server
uv tool install mcp-server-sqlite

# Run example
python examples/quickstart_sqlite.py
```

## Example Structure

All E2E examples follow a consistent pattern:

**Client Pattern:**
```python
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["examples/e2e_xxx_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        init_result = await send_initialize(read, write)
        # Use typed send_* functions for protocol messages
```

**Server Pattern:**
```python
from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities

async def main():
    server = MCPServer(
        name="example-server",
        version="1.0.0",
        capabilities=ServerCapabilities(...)
    )

    # Register handlers
    async def handle_xxx(message, session_id):
        return server.protocol_handler.create_response(message.id, result), None

    server.protocol_handler.register_method("xxx/yyy", handle_xxx)
    await run_stdio_server(server)
```

## Coverage

The examples provide complete coverage of MCP protocol features:

- ✅ Initialization and capability negotiation
- ✅ Tools (list, call)
- ✅ Resources (list, read, subscribe/unsubscribe)
- ✅ Prompts (list, get)
- ✅ Roots (list, change notifications)
- ✅ Sampling (LLM requests from server)
- ✅ Completion (autocomplete)
- ✅ Progress tracking
- ✅ Cancellation
- ✅ Ping/health checks
- ✅ Multiple transports (stdio, HTTP, SSE)

## Testing

All examples have been tested and verified to work correctly. To test all E2E examples:

```bash
# Test all E2E examples
for example in examples/e2e_*_client.py; do
    echo "Testing $example"
    python "$example" || exit 1
done
```
