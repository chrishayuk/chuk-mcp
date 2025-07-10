# chuk-mcp

A comprehensive Python client implementation for the **Model Context Protocol (MCP)** - the open standard for connecting AI assistants to external data and tools.

[![PyPI version](https://badge.fury.io/py/chuk-mcp.svg)](https://badge.fury.io/py/chuk-mcp)
[![Python Version](https://img.shields.io/pypi/pyversions/chuk-mcp)](https://pypi.org/project/chuk-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## 🎯 Project Overview

**chuk-mcp** is a complete Model Context Protocol (MCP) implementation providing both client and server capabilities with a modern, layered architecture. It supports multiple transport protocols, maintains backward compatibility, and implements cutting-edge features including browser-native operation and structured tool outputs.

## What is the Model Context Protocol?

The **Model Context Protocol (MCP)** is an open standard that enables AI applications to securely access external data and tools. Instead of every AI app building custom integrations, MCP provides a universal interface for:

- **🔧 Tools**: Functions AI can call (APIs, file operations, calculations)
- **📄 Resources**: Data sources AI can read (files, databases, web content)  
- **💬 Prompts**: Reusable prompt templates with parameters
- **🎯 Real-time Data**: Live information that changes frequently

**Key Benefits:**
- **Standardized**: One protocol for all integrations
- **Secure**: User-controlled access to sensitive data
- **Extensible**: Easy to add new capabilities
- **Language-Agnostic**: Works across different programming languages

## Why Use This Client?

`chuk-mcp` is a production-ready Python implementation that provides:

✅ **Comprehensive MCP Protocol Support** - Core features including tools, resources, prompts, with advanced features like sampling and completion  
✅ **Browser-Native Operation** - First-of-kind Pyodide/WebAssembly compatibility  
✅ **Type Safety** - Full type annotations with optional Pydantic integration or graceful fallback  
✅ **Robust Error Handling** - Automatic retries, connection recovery, and detailed error reporting  
✅ **Multi-Transport Architecture** - stdio, HTTP, SSE with extensible interface  
✅ **Version-Aware Features** - Automatic protocol negotiation and graceful degradation  
✅ **Smart Fallback System** - Works with or without dependencies  
✅ **Production Ready** - Battle-tested with proper logging, monitoring, and performance optimization  
✅ **UV Optimized** - First-class support for modern Python packaging with UV

## 🏗️ Architecture Overview

### Layer Structure
```
┌─────────────────────────────────────────┐
│              CLI & Demo Layer           │ ← __main__.py, demos
├─────────────────────────────────────────┤
│             Client/Server API           │ ← High-level abstractions
├─────────────────────────────────────────┤
│            Protocol Layer               │ ← Messages, types, features
├─────────────────────────────────────────┤
│            Transport Layer              │ ← stdio, HTTP, SSE
├─────────────────────────────────────────┤
│             Base Layer                  │ ← Pydantic fallback, config
└─────────────────────────────────────────┘
```

**Benefits of This Architecture:**
- **🔌 Pluggable Transports**: Easy to add HTTP, WebSocket, or other transports
- **♻️ Reusable Protocol Layer**: Can be used by servers, proxies, or other tools
- **🧪 Testable Components**: Each layer can be tested independently
- **📦 Clean Dependencies**: Minimal coupling between layers
- **⚡ Smart Validation**: Optional Pydantic with intelligent fallback

```
chuk_mcp/
├── protocol/           # 🏗️ Shared protocol layer
│   ├── types/         #    Type definitions and validation
│   ├── messages/      #    Feature-organized messaging
│   └── mcp_pydantic_base.py  # Type system foundation with fallback
├── transports/        # 🚀 Transport implementations  
│   ├── stdio/         #    Process-based communication
│   ├── http/          #    Modern streamable HTTP
│   └── sse/           #    Legacy Server-Sent Events
├── client/            # 🔧 High-level client API
└── server/            # 🏭 Server framework
```

## 🚀 Key Features

### ✅ **Comprehensive MCP Protocol Support**
- **Protocol Versions**: 2025-06-18 (current), 2025-03-26, 2024-11-05
- **Core Features**: Tools, Resources, Prompts, Logging, Progress, Cancellation
- **Advanced Features**: Sampling, Completion, Roots, Elicitation (version-dependent)
- **Structured Output**: NEW in 2025-06-18 - tools can return structured data + schemas
- **Version Negotiation**: Automatic protocol version detection and fallback

### 🌐 **Multi-Transport Architecture**
- **stdio**: Process-based communication (always available)
- **HTTP**: Modern Streamable HTTP (replaces SSE)
- **SSE**: Server-Sent Events (deprecated but supported for compatibility)
- **Extensible**: Clean transport interface for future protocols

### 🧠 **Smart Fallback System**
- **Pydantic Detection**: Auto-detects and uses Pydantic if available
- **Fallback Mode**: Complete validation system when Pydantic unavailable
- **Browser Compatible**: Works in Pyodide/WebAssembly environments
- **Zero Dependencies**: Core functionality works with stdlib only

## Installation

### Quick Start with UV (Recommended)

[UV](https://github.com/astral-sh/uv) is the fastest Python package manager. Choose your installation based on your needs:

```bash
# 🚀 Minimal installation (uses lightweight fallback validation)
uv add chuk-mcp

# 🔧 With Pydantic validation (recommended for production)
uv add chuk-mcp[pydantic]

# 🌟 Full features (Pydantic + HTTP transport + all extras)
uv add chuk-mcp[full]

# 🛠️ Development installation (includes testing and examples)
uv add chuk-mcp[dev]
```

### Traditional Installation

```bash
# Using pip (if UV not available)
pip install chuk-mcp

# With Pydantic support
pip install chuk-mcp[pydantic]

# Full features
pip install chuk-mcp[full]
```

### Installation Options Explained

| Option | Dependencies | Use Case | Performance |
|--------|-------------|----------|-------------|
| `chuk-mcp` | Core only | Minimal deployments, testing | Fast startup, lightweight validation |
| `chuk-mcp[pydantic]` | + Pydantic | Production use, type safety | Enhanced validation, better errors |
| `chuk-mcp[full]` | + All features | Maximum functionality | Full feature set |
| `chuk-mcp[dev]` | + Dev tools | Development, testing | All tools included |

> **💡 Performance Note:** The lightweight fallback validation is ~20x slower than Pydantic (0.010ms vs 0.000ms per operation) but still excellent for most use cases. Use `[pydantic]` for high-throughput applications.

### Verify Installation

```bash
# Quick test with UV
uv run python -c "import chuk_mcp; print('✅ chuk-mcp installed successfully')"

# Or test full functionality
uv run --with chuk-mcp[pydantic] python -c "
from chuk_mcp.protocol.mcp_pydantic_base import PYDANTIC_AVAILABLE
print(f'✅ Pydantic available: {PYDANTIC_AVAILABLE}')
"
```

## Protocol Compliance

`chuk-mcp` provides comprehensive compliance with the MCP specification across multiple protocol versions:

### 📋 Supported Protocol Versions
- **Latest**: `2025-06-18` (primary support)
- **Stable**: `2025-03-26` (full compatibility)
- **Legacy**: `2024-11-05` (backward compatibility)

### 📊 Protocol Compliance Matrix

| Feature Category | 2024-11-05 | 2025-03-26 | 2025-06-18 | Implementation Status |
|-----------------|------------|------------|------------|---------------------|
| **Core Operations** | | | | |
| Tools (list/call) | ✅ | ✅ | ✅ | ✅ Complete |
| Resources (list/read/subscribe) | ✅ | ✅ | ✅ | ✅ Complete |
| Prompts (list/get) | ✅ | ✅ | ✅ | ✅ Complete |
| **Transport** | | | | |
| Stdio | ✅ | ✅ | ✅ | ✅ Complete |
| SSE | ✅ | ⚠️ Deprecated | ❌ Removed | ✅ Legacy Support |
| HTTP Streaming | ❌ | ✅ | ✅ | ✅ Complete |
| **Advanced Features** | | | | |
| Sampling | ✅ | ✅ | ✅ | ✅ Complete |
| Completion | ✅ | ✅ | ✅ | ✅ Complete |
| Roots | ✅ | ✅ | ✅ | ✅ Complete |
| Elicitation | ❌ | ❌ | ✅ | ✅ Complete |
| **Quality Features** | | | | |
| Progress Tracking | ✅ | ✅ | ✅ | ✅ Complete |
| Cancellation | ✅ | ✅ | ✅ | ✅ Complete |
| Notifications | ✅ | ✅ | ✅ | ✅ Complete |
| Batching | ✅ | ✅ | ❌ Deprecated | ✅ Legacy Support |

## Quick Start

### Simple Demo

```python
import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize

async def main():
    # Demo with minimal echo server (no external dependencies)
    server_params = StdioServerParameters(
        command="python",
        args=["-c", """
import json, sys
init = json.loads(input())
response = {
    "id": init["id"], 
    "result": {
        "serverInfo": {"name": "Demo", "version": "1.0"}, 
        "protocolVersion": "2025-06-18", 
        "capabilities": {}
    }
}
print(json.dumps(response))
        """]
    )
    
    async with stdio_client(server_params) as (read, write):
        result = await send_initialize(read, write)
        print(f"✅ Connected to {result.serverInfo.name}")

if __name__ == "__main__":
    anyio.run(main)
```

Run with UV:
```bash
uv run --with chuk-mcp[pydantic] python demo.py
```

### Basic Usage with Real Server

```python
import anyio
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize

async def main():
    # Configure connection to an MCP server
    server_params = StdioServerParameters(
        command="uvx",  # Use uvx to run Python tools
        args=["mcp-server-sqlite", "--db-path", "example.db"]
    )
    
    # Connect and initialize
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Initialize the MCP session
        init_result = await send_initialize(read_stream, write_stream)
        
        if init_result:
            print(f"✅ Connected to {init_result.serverInfo.name}")
            print(f"📋 Protocol version: {init_result.protocolVersion}")
        else:
            print("❌ Failed to initialize connection")

anyio.run(main)
```

### Using the CLI

Test server connectivity instantly:

```bash
# Test with quickstart demo
uv run examples/quickstart.py

# Run comprehensive demos
uv run examples/e2e_smoke_test_example.py --demo all

# Test specific server configurations
uv run examples/e2e_smoke_test_example.py --smoke
```

## 🎯 Innovation Highlights

### 1. **Browser-Native MCP** 🌐
- **Pyodide Compatible**: Runs completely in browser via WebAssembly
- **Zero Network Dependencies**: Works offline in browser
- **Progressive Enhancement**: Uses Pydantic when available, fallback otherwise
- **First-of-Kind**: First browser-native MCP implementation

### 2. **Version-Aware Features** 🔄
- **Automatic Adaptation**: Features enable/disable based on protocol version
- **Graceful Degradation**: Older servers work with newer clients
- **Forward Compatibility**: Ready for future MCP versions

### 3. **Transport Abstraction** 🚀
```python
# Same API across all transports
async with stdio_client(stdio_params) as streams:
    response = await send_message(*streams, "ping")

async with http_client(http_params) as streams:  
    response = await send_message(*streams, "ping")  # Same API!
```

## 🆕 Latest Features

### Structured Tool Output (2025-06-18)
Tools can now return both human-readable text and machine-processable structured data:

```python
# NEW in 2025-06-18: Tools return structured data + schemas
result = await tool_call("analyze_text", {"text": "Hello world"})

# Text summary for humans
print(result.content[0].text)  # "Analyzed 2 words, positive sentiment"

# Structured data for machines  
data = result.structuredContent[0].data
sentiment_score = data["sentiment"]["score"]  # 0.85
word_count = data["statistics"]["word_count"]  # 2
```

This enables AI assistants to process tool outputs programmatically while still providing clear summaries for users.

## Core Concepts

### 🔧 Tools - Functions AI Can Call

Tools are functions that AI can execute on your behalf. Examples include file operations, API calls, calculations, or any custom logic.

```python
from chuk_mcp.protocol.messages import send_tools_list, send_tools_call

async def explore_tools(read_stream, write_stream):
    # List available tools
    tools_response = await send_tools_list(read_stream, write_stream)
    
    for tool in tools_response.get("tools", []):
        print(f"🔧 {tool['name']}: {tool['description']}")
    
    # Call a specific tool
    result = await send_tools_call(
        read_stream, write_stream,
        name="execute_sql",
        arguments={"query": "SELECT COUNT(*) FROM users"}
    )
    
    print(f"📊 Query result: {result}")
```

### 📄 Resources - Data AI Can Access

Resources are data sources like files, database records, API responses, or any URI-addressable content.

```python
from chuk_mcp.protocol.messages import send_resources_list, send_resources_read

async def explore_resources(read_stream, write_stream):
    # Discover available resources
    resources_response = await send_resources_list(read_stream, write_stream)
    
    for resource in resources_response.get("resources", []):
        print(f"📄 {resource['name']} ({resource.get('mimeType', 'unknown')})")
        print(f"   URI: {resource['uri']}")
    
    # Read specific resource content
    if resources_response.get("resources"):
        first_resource = resources_response["resources"][0]
        content = await send_resources_read(read_stream, write_stream, first_resource["uri"])
        
        for item in content.get("contents", []):
            if "text" in item:
                print(f"📖 Content preview: {item['text'][:200]}...")
```

### 💬 Prompts - Reusable Templates

Prompts are parameterized templates that help generate consistent, high-quality AI interactions.

```python
from chuk_mcp.protocol.messages import send_prompts_list, send_prompts_get

async def use_prompts(read_stream, write_stream):
    # List available prompt templates
    prompts_response = await send_prompts_list(read_stream, write_stream)
    
    for prompt in prompts_response.get("prompts", []):
        print(f"💬 {prompt['name']}: {prompt['description']}")
    
    # Get a prompt with custom arguments
    prompt_result = await send_prompts_get(
        read_stream, write_stream,
        name="analyze_data",
        arguments={"dataset": "sales_2024", "metric": "revenue"}
    )
    
    # The result contains formatted messages ready for AI
    for message in prompt_result.get("messages", []):
        print(f"🤖 {message['role']}: {message['content']}")
```

## Configuration

### Server Configuration

Create a `server_config.json` file to define your MCP servers:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "database.db"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    },
    "github": {
      "command": "uvx",
      "args": ["mcp-server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "python": {
      "command": "uv",
      "args": ["run", "--with", "mcp-server-python", "mcp-server-python"],
      "env": {
        "PYTHONPATH": "/custom/python/path"
      }
    }
  }
}
```

### Configuration Loading

```python
from chuk_mcp.transports.stdio import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize

async def connect_configured_server():
    # Load server configuration
    server_params = StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "database.db"]
    )
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        init_result = await send_initialize(read_stream, write_stream)
        print(f"Connected to configured server: {init_result.serverInfo.name}")
```

## Advanced Features

### 🎯 Intelligent Sampling

Let servers request AI to generate content on their behalf (with user approval):

```python
from chuk_mcp.protocol.messages.sampling import (
    send_sampling_create_message, 
    create_sampling_message
)

async def ai_content_generation(read_stream, write_stream):
    # Server can request AI to generate content
    messages = [
        create_sampling_message("user", "Explain quantum computing in simple terms")
    ]
    
    result = await send_sampling_create_message(
        read_stream, write_stream,
        messages=messages,
        max_tokens=1000,
        temperature=0.7
    )
    
    print(f"🤖 AI Generated: {result['content']['text']}")
```

### 🎯 Argument Completion

Provide intelligent autocompletion for tool arguments:

```python
from chuk_mcp.protocol.messages.completion import (
    send_completion_complete, 
    create_resource_reference, 
    create_argument_info
)

async def smart_completion(read_stream, write_stream):
    # Get completion suggestions for a resource argument
    response = await send_completion_complete(
        read_stream, write_stream,
        ref=create_resource_reference("file:///project/data/"),
        argument=create_argument_info("filename", "sales_202")
    )
    
    completions = response.get("completion", {}).get("values", [])
    print(f"💡 Suggestions: {completions}")
```

### 🔄 Multi-Server Orchestration

Connect to multiple servers simultaneously:

```python
from chuk_mcp.transports.stdio import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_tools_list

async def multi_server_task():
    """Process data using multiple MCP servers."""
    
    servers = [
        StdioServerParameters(command="uvx", args=["mcp-server-sqlite", "--db-path", "data.db"]),
        StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/data"]),
    ]
    
    for i, server_params in enumerate(servers):
        async with stdio_client(server_params) as (read_stream, write_stream):
            print(f"Processing with server {i+1}")
            
            # Each server can have different capabilities
            tools = await send_tools_list(read_stream, write_stream)
            print(f"  Available tools: {len(tools.get('tools', []))}")
```

### 📡 Real-time Subscriptions

Subscribe to resource changes for live updates:

```python
from chuk_mcp.protocol.messages.resources import send_resources_subscribe

async def live_monitoring(read_stream, write_stream):
    # Subscribe to file changes
    success = await send_resources_subscribe(
        read_stream, write_stream,
        uri="file:///project/logs/app.log"
    )
    
    if success:
        print("📡 Subscribed to log file changes")
        
        # Handle notifications in your message loop
        # (implementation depends on your notification handling)
```

## Error Handling & Resilience

`chuk-mcp` provides robust error handling with automatic retries:

```python
from chuk_mcp.protocol.messages import RetryableError, NonRetryableError
from chuk_mcp.protocol.messages import send_tools_call

async def resilient_operations(read_stream, write_stream):
    try:
        # Operations automatically retry on transient failures
        result = await send_tools_call(
            read_stream, write_stream,
            name="network_operation",
            arguments={"url": "https://api.example.com/data"},
            timeout=30.0,  # Extended timeout for slow operations
            retries=5      # More retries for critical operations
        )
        
    except RetryableError as e:
        print(f"⚠️ Transient error after retries: {e}")
        # Handle gracefully - maybe try alternative approach
        
    except NonRetryableError as e:
        print(f"❌ Permanent error: {e}")
        # Handle definitively - operation cannot succeed
        
    except Exception as e:
        print(f"🚨 Unexpected error: {e}")
        # Handle unknown errors
```

## 🧪 Testing & Demos

### Comprehensive Test Suite
1. **Working Smoke Tests**: Full E2E validation with real servers
2. **Pyodide Browser Demo**: Live browser testing environment  
3. **Tools Demo**: Structured output feature showcase
4. **Performance Tests**: Throughput and latency benchmarks

### Demo Applications
- **CLI Tools**: Ready-to-use command-line utilities
- **Interactive Explorer**: Hands-on tool testing
- **Protocol Validator**: Real-time MCP compliance checking
- **Browser Demo**: WebAssembly-based MCP in the browser

### Testing & Validation

```bash
# Quick validation
uv run examples/quickstart.py

# Run comprehensive tests
uv run examples/e2e_smoke_test_example.py --demo all

# Validate installation scenarios
uv run diagnostics/installation_scenarios_diagnostic.py

# Test specific functionality
uv run examples/e2e_smoke_test_example.py --smoke

# Performance benchmarks
uv run examples/e2e_smoke_test_example.py --performance
```

## Available MCP Servers

The MCP ecosystem includes servers for popular services:

### 🚀 Install with UV (Recommended)

```bash
# Popular Python servers
uv tool install mcp-server-sqlite
uv tool install mcp-server-github
uv tool install mcp-server-postgres

# Or run directly without installation
uv run --with mcp-server-sqlite mcp-server-sqlite --db-path data.db
```

### 🟢 Node.js Servers

```bash
# Use npx for Node.js servers
npx -y @modelcontextprotocol/server-filesystem /path/to/files
npx -y @modelcontextprotocol/server-brave-search
```

### 📁 Available Servers

- **📁 Filesystem**: `@modelcontextprotocol/server-filesystem` 
- **🗄️ SQLite**: `mcp-server-sqlite` 
- **🐙 GitHub**: `mcp-server-github`
- **☁️ Google Drive**: `mcp-server-gdrive`
- **🔍 Web Search**: `mcp-server-brave-search`
- **📊 PostgreSQL**: `mcp-server-postgres`
- **📈 Analytics**: Various data analytics servers
- **🔧 Custom**: Build your own with the MCP SDK

Find more at: [MCP Servers Directory](https://github.com/modelcontextprotocol/servers)

## Building MCP Servers

Want to create your own MCP server? Check out:

- **Python**: [`mcp` package](https://pypi.org/project/mcp/)
- **TypeScript**: [`@modelcontextprotocol/sdk`](https://www.npmjs.com/package/@modelcontextprotocol/sdk)
- **Specification**: [MCP Protocol Documentation](https://spec.modelcontextprotocol.io/)

## Performance & Monitoring

`chuk-mcp` includes built-in performance monitoring:

```python
import logging

# Enable detailed logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Performance is optimized for:
# - Concurrent server connections
# - Efficient message routing  
# - Minimal memory allocation
# - Fast JSON serialization
```

### 📈 Performance Characteristics

**Benchmarks (from smoke tests):**
- **Connection Setup**: ~200ms (fast)
- **Request Throughput**: >50 req/sec concurrent
- **Memory Usage**: Minimal footprint
- **Browser Performance**: <2s load time, instant operations

**Performance Highlights:**
- **🚀 Fast Startup**: < 1 second connection time
- **⚡ High Throughput**: 50+ requests/second per connection
- **🔄 Concurrent Operations**: Full async/await support
- **💾 Memory Efficient**: Minimal overhead per connection

### Installation Performance Matrix

| Installation | Startup Time | Validation Speed | Memory Usage | Dependencies |
|-------------|-------------|------------------|--------------|--------------|
| `chuk-mcp` | < 0.5s | 0.010ms/op | 15MB | Core only |
| `chuk-mcp[pydantic]` | < 1.0s | 0.000ms/op | 25MB | + Pydantic |
| `chuk-mcp[full]` | < 1.5s | 0.000ms/op | 35MB | All features |

## Intelligent Dependency Management

`chuk-mcp` includes intelligent dependency handling with graceful fallbacks:

```python
# Check validation backend
from chuk_mcp.protocol.mcp_pydantic_base import PYDANTIC_AVAILABLE

if PYDANTIC_AVAILABLE:
    print("✅ Using Pydantic for enhanced validation")
    print("   • Better error messages")
    print("   • Faster validation (Rust-based)")
    print("   • Advanced type coercion")
else:
    print("📦 Using lightweight fallback validation")
    print("   • Pure Python implementation")
    print("   • No external dependencies")
    print("   • ~20x slower but still fast")

# Force fallback mode for testing
import os
os.environ["MCP_FORCE_FALLBACK"] = "1"
```

## Development

### Setup with UV

```bash
git clone https://github.com/chrishayuk/chuk-mcp
cd chuk-mcp

# Install with development dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
```

### Traditional Setup

```bash
# Alternative setup with pip
pip install -e ".[dev]"
```

### Development Features

```bash
# Test with fallback validation
UV_MCP_FORCE_FALLBACK=1 uv run examples/quickstart.py

# Test with different Python versions
uv run --python 3.11 examples/quickstart.py
uv run --python 3.12 examples/quickstart.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Ensure all tests pass with `uv run diagnostics/installation_scenarios_diagnostic.py`
5. Submit a pull request

## UV Integration Features

### Project Templates

```bash
# Start a new MCP client project
uv init my-mcp-client
cd my-mcp-client

# Add chuk-mcp with dependencies
uv add chuk-mcp[pydantic]

# Add development tools
uv add --dev pytest black isort

# Create example
cat > main.py << 'EOF'
import anyio
from chuk_mcp import stdio_client, StdioServerParameters

async def main():
    # Your MCP client code here
    pass

if __name__ == "__main__":
    anyio.run(main)
EOF
```

### UV Scripts

Add to your `pyproject.toml`:

```toml
[tool.uv]
dev-dependencies = [
    "chuk-mcp[dev]",
]

[project.scripts]
mcp-client = "my_mcp_client:main"

[tool.uv.scripts]
test-mcp = "uv run examples/quickstart.py"
validate = "uv run diagnostics/installation_scenarios_diagnostic.py"
```

## 🎖️ Production Readiness

### ✅ **Enterprise Features**
- **Error Recovery**: Comprehensive error handling and retry logic
- **Logging**: Structured logging with configurable levels  
- **Monitoring**: Built-in health checks and metrics
- **Security**: Input validation and safe subprocess handling

### ✅ **Deployment Options**
- **Standalone**: Direct process execution
- **Containerized**: Docker-ready with minimal dependencies
- **Browser**: Progressive Web App deployment via Pyodide
- **Cloud**: Stateless operation suitable for serverless

### ✅ **Maintenance**
- **Documentation**: Comprehensive examples and type hints
- **Testing**: 100% working test coverage with real scenarios
- **Migration Support**: Clear upgrade paths for new features

## 🚀 Future Roadmap

### Near Term
- **Additional Transports**: WebSocket, gRPC support
- **Enhanced Tooling**: Visual debugger, protocol inspector
- **Performance**: Further optimization for high-throughput scenarios

### Long Term  
- **Protocol Extensions**: Custom capability negotiation
- **Distributed MCP**: Multi-server orchestration
- **Visual Builder**: GUI for MCP server development

## Support & Community

- **📖 Documentation**: [Full API Documentation](https://docs.example.com)
- **🐛 Issues**: [GitHub Issues](https://github.com/chrishayuk/chuk-mcp/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/chrishayuk/chuk-mcp/discussions)
- **📧 Email**: For private inquiries
- **🚀 UV**: [UV Package Manager](https://github.com/astral-sh/uv)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io/) specification
- Inspired by the official [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- Thanks to the MCP community for feedback and contributions
- Special thanks to the [UV](https://github.com/astral-sh/uv) team for making Python package management fast and reliable

---

## 🏆 Summary

**chuk-mcp** represents a **production-ready, comprehensive MCP implementation** that:

- ✅ **Implements comprehensive MCP protocol features** including latest 2025-06-18 capabilities
- ✅ **Provides clean, modern APIs** with intelligent fallback systems  
- ✅ **Supports multiple transports** with a unified interface
- ✅ **Works everywhere** - server, desktop, and browser environments
- ✅ **Delivers enterprise-grade reliability** with comprehensive error handling
- ✅ **Enables innovation** through structured outputs and extensible architecture

This implementation sets a new standard for MCP libraries, being both **immediately practical** for production use and **forward-looking** for next-generation MCP applications.