# chuk-mcp Examples

All examples in this directory are **tested and verified working**.

## 🌟 End-to-End (E2E) Examples - **NEW!**

**Both client AND server powered by chuk-mcp!** These examples demonstrate the full MCP protocol with chuk-mcp implementing both sides.

### Why E2E Examples?

- ✅ **Complete protocol demonstration** - See both sides working together
- ✅ **No external dependencies** - Pure chuk-mcp, no npm/uvx servers needed
- ✅ **Clean architecture** - Uses transport helpers and proper patterns
- ✅ **Educational** - Shows best practices for client and server
- ✅ **Testable** - Easy to modify and experiment

### Architecture

**Server Side:**
```python
# All servers use the clean run_stdio_server() helper
from server_helpers import run_stdio_server

server = MCPServer(name="my-server", capabilities=...)
server.register_tool(...)  # or register_method for custom handlers
await run_stdio_server(server)  # ← Transport layer handled here
```

**Client Side:**
```python
# Clients use stdio_client transport
from chuk_mcp import stdio_client

async with stdio_client(params) as (read, write):
    await send_initialize(read, write)
    # Use protocol methods...
```

### Available E2E Examples

| Example | Feature | Description |
|---------|---------|-------------|
| `e2e_tools_*` | 🔧 Tools | Tool registration with clean MCPServer API |
| `e2e_resources_*` | 📚 Resources | Resource listing and reading |
| `e2e_prompts_*` | 💬 Prompts | Reusable prompt templates |
| `e2e_roots_*` | 📁 Roots | Custom protocol handlers for roots |
| `e2e_sampling_*` | 🎯 Sampling | Sampling protocol implementation |
| `e2e_completion_*` | 💡 Completion | Smart autocomplete functionality |
| `e2e_subscriptions_*` | 📡 Subscriptions | Resource subscription and updates |
| `e2e_cancellation_*` | 🚫 Cancellation | Cancel operations gracefully |
| `e2e_progress_*` | 📊 Progress | Track long-running operations |
| `e2e_ping_*` | 🏓 Ping | Health checks and monitoring |

Each E2E example consists of:
- `e2e_*_server.py` - MCP server using `MCPServer` + `run_stdio_server()`
- `e2e_*_client.py` - MCP client using `stdio_client` transport
- `server_helpers.py` - Reusable transport helper (shows future `stdio_server`)

**Run an E2E example:**
```bash
# Tools example
uv run examples/e2e_tools_client.py

# Roots example
uv run examples/e2e_roots_client.py

# Sampling example
uv run examples/e2e_sampling_client.py

# Subscriptions example
uv run examples/e2e_subscriptions_client.py

# Completion example
uv run examples/e2e_completion_client.py

# Progress example
uv run examples/e2e_progress_client.py

# Cancellation example
uv run examples/e2e_cancellation_client.py
```

The client automatically launches the server, so you only need to run the client!

### Key Files

- **`server_helpers.py`** - Contains `run_stdio_server()` helper
  - Clean stdio transport for servers
  - Handles all JSON-RPC I/O
  - Delegates to MCPServer for protocol handling
  - Shows what a future `chuk_mcp.transports.stdio.stdio_server` should look like

---

## Quick Start Examples

These examples match the README Quick Start section and demonstrate core functionality:

### 1. Minimal Demo (`quickstart_minimal.py`)
**No external dependencies required** - perfect for testing your installation.

```bash
uv run python examples/quickstart_minimal.py
```

Expected output:
```
✅ Connected to Demo
```

### 2. SQLite Database Tools (`quickstart_sqlite.py`)
Real-world example with database tools.

```bash
# First install the SQLite MCP server
uv tool install mcp-server-sqlite

# Run the example
uv run python examples/quickstart_sqlite.py
```

### 3. File Resources (`quickstart_resources.py`)
Access files through the resources API.

```bash
# Requires Node.js for the filesystem server
uv run python examples/quickstart_resources.py
```

### 4. Complete Multi-Feature Demo (`quickstart_complete.py`)
Demonstrates all core MCP features together.

```bash
uv run python examples/quickstart_complete.py
```

## Feature Examples

Comprehensive examples demonstrating each MCP feature. See the **Feature Guide** section in the main README.

### Core Features (External Server Required)

| Example | Feature | Description |
|---------|---------|-------------|
| `feature_resources.py` | 📄 Resources | Read data from resources (requires SQLite server) |
| `feature_prompts.py` | 💬 Prompts | Use prompt templates (requires SQLite server) |

### Advanced Features

| Example | Feature | Description |
|---------|---------|-------------|
| `feature_transports.py` | 🌐 Transports | Transport selection guide |
| `feature_multi_server.py` | 🔄 Multi-Server | Orchestrate multiple servers |

**Note:** For pure chuk-mcp examples that don't require external servers, see the **E2E Examples** above.

Run any feature example:
```bash
uv run python examples/feature_resources.py
uv run python examples/feature_prompts.py
uv run python examples/feature_multi_server.py
uv run python examples/feature_transports.py
```

## Complete Examples

### Full E2E Testing (`e2e_smoke_test_example.py`)
Comprehensive test suite with real servers.

```bash
# Run all demos
uv run examples/e2e_smoke_test_example.py --demo all

# Quick smoke test
uv run examples/e2e_smoke_test_example.py --smoke
```

### Interactive Quickstart (`quickstart.py`)
Step-by-step walkthrough with a built-in test server.

```bash
uv run examples/quickstart.py
```

## Installation Options

```bash
# Minimal installation (for basic examples)
uv add chuk-mcp

# With Pydantic (recommended for production)
uv add chuk-mcp[pydantic]

# Full features
uv add chuk-mcp[full]
```

## Troubleshooting

**Import errors?**
```bash
# Ensure you're in the project directory
cd /path/to/chuk-mcp

# Install in development mode
uv sync
```

**Server not found?**
```bash
# Check if MCP servers are installed
uv tool list

# Install missing servers
uv tool install mcp-server-sqlite
```

**Permission denied?**
```bash
# Make examples executable
chmod +x examples/*.py
```

## Creating Your Own Examples

Use these examples as templates:

1. Copy a relevant example
2. Modify for your use case
3. Test with `uv run python your_example.py`
4. Share or integrate into your project

## Need Help?

- Check the main [README](../README.md)
- Review the [documentation](https://github.com/chrishayuk/chuk-mcp)
- Open an [issue](https://github.com/chrishayuk/chuk-mcp/issues)
