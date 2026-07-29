# chuk-mcp

[![PyPI version](https://img.shields.io/pypi/v/chuk-mcp.svg)](https://pypi.org/project/chuk-mcp)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/chuk-mcp)](https://pypi.org/project/chuk-mcp)
[![Python Version](https://img.shields.io/pypi/pyversions/chuk-mcp.svg)](https://pypi.org/project/chuk-mcp)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**A lean, production-minded Python implementation of the Model Context Protocol (MCP).**

**Brings first-class MCP protocol support to Python — lightweight, async, and spec-accurate from day one.**

**Requires Python 3.11+**

`chuk-mcp` gives you a clean, typed, transport-agnostic implementation for both **MCP clients and servers**. It focuses on the protocol surface (messages, types, versioning, transports) and leaves orchestration, UIs, and agent frameworks to other layers.

> ✳️ **What this is**: a **protocol compliance library** with ergonomic helpers for clients and servers.
>
> ⛔ **What this isn't**: a chatbot runtime, workflow engine, or an opinionated application framework.

## Architecture: Where chuk-mcp Fits

### Stack Overview

```
┌──────────────────────────────────────┐
│   Your AI Application                │
│   (Claude, GPT, custom agents)       │
└────────────┬─────────────────────────┘
             │ MCP Protocol
             ▼
┌──────────────────────────────────────┐
│   chuk-mcp Client                    │  ← You are here
│   • Protocol compliance              │
│   • Transport (stdio/Streamable HTTP)│
│   • Type-safe messages               │
│   • Capability negotiation           │
└────────────┬─────────────────────────┘
             │ MCP Protocol
             ▼
┌──────────────────────────────────────┐
│   chuk-mcp Server (optional)         │
│   • Protocol handlers                │
│   • Tool/Resource registration       │
│   • Session management               │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│   Your Tools & Resources             │
│   (databases, APIs, files, etc)      │
└──────────────────────────────────────┘
```

**chuk-mcp provides the protocol layer** — connect AI applications to tools and data sources using the standard MCP protocol.

### Internal Architecture

The library itself is organized in layers that you can use at different levels of abstraction:

```
┌─────────────────────────────────────────┐
│              CLI & Demo Layer           │  __main__.py, demos/
├─────────────────────────────────────────┤
│             Client/Server API           │  High-level abstractions
├─────────────────────────────────────────┤
│            Protocol Layer               │  Messages, types, features
├─────────────────────────────────────────┤
│            Transport Layer              │  stdio, Streamable HTTP
├─────────────────────────────────────────┤
│             Base Layer                  │  Pydantic fallback, config
└─────────────────────────────────────────┘
```

**Layer Details:**

| Layer | Purpose | Usage |
|-------|---------|-------|
| **CLI & Demo** | Built-in utilities and demonstrations | Optional — use protocol layer directly |
| **Client/Server API** | High-level abstractions for client-server interactions | Optional — can use protocol layer directly |
| **Protocol Layer** | Message definitions, type-safe request/response handling, capability negotiation | Core — implements MCP spec |
| **Transport Layer** | Pluggable transport implementations (stdio, Streamable HTTP) | Choose based on deployment |
| **Base Layer** | Pydantic fallback, shared config, type adapters | Foundation — automatic |

Most users work with the **Protocol Layer** (`send_*` functions) and **Transport Layer** (stdio/HTTP clients), optionally using the **Client/Server API** for higher-level abstractions.

---

## Table of Contents

* [Why chuk‑mcp?](#why-chuk-mcp)
* [Protocol Performance](#protocol-performance)
* [At a Glance](#at-a-glance)
* [Install](#install)
* [Quick Start](#quick-start)
* [Core Concepts](#core-concepts)
  * [Tools](#tools)
  * [Resources](#resources)
  * [Prompts](#prompts)
  * [Roots (optional)](#roots-optional)
  * [Sampling & Completion (optional)](#sampling--completion-optional)
* [Transports](#transports)
* [Configuration Examples](#configuration-examples)
* [Examples & Feature Demonstrations](#examples--feature-demonstrations)
* [Versioning & Compatibility](#versioning--compatibility)
* [Comparison with Official MCP SDK](#comparison-with-official-mcp-sdk)
* [Design Goals & Non‑Goals](#design-goals--non-goals)
* [Scaling & Concurrency](#scaling--concurrency)
* [FAQ](#faq)
* [Contributing](#contributing)
* [Feature Showcase](#feature-showcase)
* [Ecosystem](#ecosystem)
* [License](#license)

---

## Why chuk-mcp?

* **Protocol-first**: Focuses on MCP messages, types, and capability negotiation — [spec.modelcontextprotocol.io](https://spec.modelcontextprotocol.io)
* **Client + Server**: Full support for building both MCP clients and servers
* **Typed**: Full type hints; optional Pydantic models when available
* **Transport-agnostic**: stdio by default, Streamable HTTP (NDJSON) for remote servers, easily extensible
* **Async-first**: Built on AnyIO; integrate with `anyio.run(...)` or your existing loop
* **Small & focused**: No heavy orchestration or agent assumptions
* **Clean protocol layer**: Errors fail fast without retries — bring your own error handling strategy
* **Production-minded**: Clear errors, structured logging hooks, composable with retry/caching layers
* **⚡ High-performance**: Protocol overhead in the 2-5ms range; optional fast JSON for 4x faster serialization. See [Protocol Performance](#protocol-performance) for detailed benchmarks

---

## Protocol Performance

`chuk-mcp` is designed to keep MCP protocol overhead in the **2-5 ms** range, so the cost of using tools is dominated by the tools themselves, not the protocol.

**Why it's fast:**
- Zero heavy dependencies (AnyIO core only)
- Async-native stdio & NDJSON HTTP
- No tool execution inside the library
- Optional orjson fast path (`[fast-json]`)

> 💡 For concurrency & capacity numbers, see [Scaling & Concurrency](#scaling--concurrency).

### ⚡ Latency Benchmarks

Protocol overhead (typical measurements on modern hardware):
- **Initialize → Tool List:** 2-3 ms
- **Tool Call Round Trip:** < 5 ms overhead (beyond actual tool execution time)
- **Streaming:** Near-zero overhead due to NDJSON chunk boundaries

*Benchmarks run on macOS (Darwin 24.6.0), Python 3.11 — see `benchmarks/PERFORMANCE_REPORT.md` for exact environment and commands.*

### 🚀 JSON Serialization (Optional Fast Path)

Install with `[fast-json]` for **~4x faster JSON operations** using orjson:
- **Serialization:** ~6x faster
- **Deserialization:** ~2x faster
- **Round-trip:** ~4x faster

```bash
pip install "chuk-mcp[fast-json]"  # Automatic with graceful fallback
```

*Benchmark numbers from `benchmarks/json_performance.py` comparing orjson vs stdlib json on realistic MCP messages.*

### 🎯 Ideal Use Cases

This makes chuk-mcp perfect for:
- **High-frequency tool calls** — minimal overhead per request
- **Real-time agents** — sub-5ms protocol latency
- **Streaming UIs** — near-zero NDJSON chunk overhead
- **Tool processors** — fast enough to be transparent
- **WASM/edge environments** — minimal footprint
- **Production workloads** — proven at scale (see [Scaling & Concurrency](#scaling--concurrency))

---

## At a Glance

**Try it now:**

```bash
# Install an example MCP server
uv tool install mcp-server-sqlite

# Run the quick-start example
uv run python examples/quickstart_sqlite.py
```

### Hello World

A minimal working MCP server in ~10 lines:

```python
# hello_mcp.py
import anyio
from chuk_mcp.server import MCPServer, run_stdio_server
from chuk_mcp.protocol.types import ServerCapabilities, ToolCapabilities

async def main():
    server = MCPServer("hello", "1.0", ServerCapabilities(tools=ToolCapabilities()))

    async def handle_tools_list(message, session_id):
        return server.protocol_handler.create_response(
            message.id,
            {"tools": [{"name": "hello", "description": "Say hi", "inputSchema": {"type": "object"}}]}
        ), None

    server.protocol_handler.register_method("tools/list", handle_tools_list)
    await run_stdio_server(server)

anyio.run(main)
```

**Run it:** `uv run python hello_mcp.py` — or connect any MCP client via stdio!

---

**Stdio (local processes):**

```python
# Connect to an MCP server via stdio and list tools
import anyio
from chuk_mcp import StdioServerParameters, stdio_client
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_list

async def main():
    params = StdioServerParameters(command="uvx", args=["mcp-server-sqlite", "--db-path", "example.db"])
    async with stdio_client(params) as (read, write):
        init = await send_initialize(read, write)
        tools = await send_tools_list(read, write)
        print("Server:", init.serverInfo.name)
        print("Tools:", [t.name for t in tools.tools])

anyio.run(main)
```

**Streamable HTTP (remote servers):**

```python
# Local dev (plain HTTP)
import anyio
from chuk_mcp.transports.http import http_client, HttpClientParameters
from chuk_mcp.protocol.messages import send_initialize

async def main():
    params = HttpClientParameters(
        url="http://localhost:8989/mcp",
        timeout_s=30,
        headers={"Authorization": "Bearer <token>"}
    )
    async with http_client(params) as (read, write):
        init = await send_initialize(read, write)
        print("Connected:", init.serverInfo.name)

anyio.run(main)

# Production (TLS)
async def main_secure():
    params = HttpClientParameters(
        url="https://mcp.example.com/mcp",
        timeout_s=30,
        headers={"Authorization": "Bearer <token>"}
    )
    async with http_client(params) as (read, write):
        init = await send_initialize(read, write)
        print("Connected:", init.serverInfo.name)

anyio.run(main_secure)
```

---

## Install

### With `uv` (recommended)

```bash
uv add chuk-mcp                           # core (Python 3.11+ required)
uv add "chuk-mcp[pydantic]"               # add typed Pydantic models (Pydantic v2 only)
uv add "chuk-mcp[http]"                   # add Streamable HTTP transport extras
uv add "chuk-mcp[fast-json]"              # add fast JSON (orjson - 4x faster!)
uv add "chuk-mcp[full]"                   # full install with all features
```

### With `pip`

```bash
pip install "chuk-mcp"
pip install "chuk-mcp[pydantic]"          # Pydantic v2 only
pip install "chuk-mcp[http]"              # httpx>=0.28 for Streamable HTTP
pip install "chuk-mcp[fast-json]"         # orjson>=3.10 for 4x faster JSON
pip install "chuk-mcp[full]"              # all features (recommended for production)
```

> **Performance tip:** Install `[fast-json]` for **4x faster JSON operations** (6.5x serialization, 2.4x deserialization)
>
> *(Requires `pydantic>=2.11.1,<3`, `httpx>=0.28.1,<1`, and `orjson>=3.10.0,<4` for extras.)*

**Python versions:** Requires Python 3.11+; see badge for tested versions.

Verify:

```bash
python -c "import chuk_mcp; print('✅ chuk-mcp ready')"
```

---

## Quick Start

### Minimal initialize (inline demo server)

```python
import anyio
from chuk_mcp import StdioServerParameters, stdio_client
from chuk_mcp.protocol.messages import send_initialize

async def main():
    params = StdioServerParameters(
        command="python",
        args=["-c", "import json,sys; req=json.loads(sys.stdin.readline()); print(json.dumps({\"id\":req['id'],\"result\":{\"serverInfo\":{\"name\":\"Demo\",\"version\":\"1.0\"},\"protocolVersion\":\"<negotiated-by-client>\",\"capabilities\":{}}}))"]
    )
    async with stdio_client(params) as (read, write):
        res = await send_initialize(read, write)
        print("Connected:", res.serverInfo.name)

anyio.run(main)
```

> **Note:** Protocol version is negotiated during `initialize`; avoid hard-coding.

> **Windows users:** Windows cmd/PowerShell may buffer stdio differently. Use `uv run` or WSL for local development if you encounter deadlocks.

**Run it:**

```bash
uv run python examples/quickstart_minimal.py
```

### Real server (SQLite example with capability check)

```python
import anyio
from chuk_mcp import StdioServerParameters, stdio_client
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_call, send_tools_list

async def main():
    params = StdioServerParameters(command="uvx", args=["mcp-server-sqlite", "--db-path", "example.db"])
    async with stdio_client(params) as (read, write):
        # Initialize and check capabilities
        init = await send_initialize(read, write)

        # Capability-gated behavior
        if hasattr(init.capabilities, 'tools'):
            tools = await send_tools_list(read, write)
            print("Tools:", [t.name for t in tools.tools])
            result = await send_tools_call(read, write, name="read_query", arguments={"query": "SELECT 1 as x"})
            print("Result:", result.content)
        else:
            print("Server does not support tools")

anyio.run(main)
```

**Run it:**

```bash
# Install SQLite server
uv tool install mcp-server-sqlite

# Run example
uv run python examples/quickstart_sqlite.py
```

### Minimal server (protocol layer)

Build your own MCP server using the same protocol layer. See [`examples/e2e_*_server.py`](examples/) for complete working servers:

```python
# Conceptual example — for a runnable server, see examples/e2e_*_server.py
import anyio
from chuk_mcp.server import MCPServer, run_stdio_server
from chuk_mcp.protocol.types import ServerCapabilities, ToolCapabilities

async def main():
    server = MCPServer(
        name="demo-server",
        version="0.1.0",
        capabilities=ServerCapabilities(tools=ToolCapabilities())
    )

    # Register handlers using the protocol layer
    async def handle_tools_list(message, session_id):
        # Return (response, notifications). Second value is reserved for
        # optional out-of-band notifications; use None if not sending any.
        return server.protocol_handler.create_response(
            message.id,
            {"tools": [{
                "name": "greet",
                "description": "Say hello",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"]
                }
            }]}
        ), None

    server.protocol_handler.register_method("tools/list", handle_tools_list)
    await run_stdio_server(server)

anyio.run(main)
```

**Pair it with a client:**

```bash
# See examples/ for complete client-server pairs
uv run python examples/e2e_tools_client.py
```

> The examples above use stdio. Swap the transport to talk to remote servers (see **Transports**).

---

## Core Concepts

### Tools

Discover and call server-exposed functions.

```python
from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call

# list
tools = await send_tools_list(read, write)
for t in tools.tools:
    print(t.name, "-", t.description)

# call
call = await send_tools_call(read, write, name="greet", arguments={"name": "World"})
print(call.content)
```

**See full example:** [`examples/e2e_tools_client.py`](examples/e2e_tools_client.py)

### Resources

List/read (and optionally subscribe to) data sources.

```python
from chuk_mcp.protocol.messages.resources import send_resources_list, send_resources_read

resources = await send_resources_list(read, write)
if resources.resources:
    uri = resources.resources[0].uri
    data = await send_resources_read(read, write, uri)
    print(data.contents)
```

**See full examples:**

* [`examples/e2e_resources_client.py`](examples/e2e_resources_client.py)
* [`examples/e2e_subscriptions_client.py`](examples/e2e_subscriptions_client.py)

### Prompts

Parameterized, reusable prompt templates.

```python
from chuk_mcp.protocol.messages.prompts import send_prompts_list, send_prompts_get

prompts = await send_prompts_list(read, write)
if prompts.prompts:
    got = await send_prompts_get(read, write, name=prompts.prompts[0].name, arguments={})
    for m in got.messages:
        print(m.role, m.content)
```

**See full example:** [`examples/e2e_prompts_client.py`](examples/e2e_prompts_client.py)

### Roots (optional)

Advertise directories the client authorizes the server to access.

```python
from chuk_mcp.protocol.messages.roots import send_roots_list
roots = await send_roots_list(read, write)  # if supported
```

**See full example:** [`examples/e2e_roots_client.py`](examples/e2e_roots_client.py)

### Sampling & Completion (optional)

Some servers can ask the client to sample text or provide completion for arguments. These are opt-in and capability-gated.

**See full examples:**

* [`examples/e2e_sampling_client.py`](examples/e2e_sampling_client.py)
* [`examples/e2e_completion_client.py`](examples/e2e_completion_client.py)

---

## Transports

`chuk-mcp` cleanly separates **protocol** from **transport**, so you can use the same protocol handlers with any transport layer:

* **Stdio** — ideal for local child-process servers
* **Streamable HTTP** — speak to remote servers over HTTP (chunked/NDJSON)
* **SSE (Server-Sent Events)** — for browser/IDE integrations with one-way server push
* **Extensible** — implement your own transport by adapting the simple `(read, write)` async interface

> **Note:** chuk-mcp is fully async (AnyIO). Use `anyio.run(...)` or integrate into your event loop.

> **Note:** Protocol **capabilities** are negotiated during `initialize`, independent of transport. You choose the transport (stdio or Streamable HTTP) based on deployment/runtime needs.

> **Thread-safety:** Client instances are not thread-safe across event loops. See [FAQ](#is-it-thread-safe) for details.

> **Streamable HTTP** uses chunked NDJSON. Configure `HttpClientParameters(timeout_s=30, headers={"Authorization": "Bearer ..."})`. Clients stream NDJSON with backpressure. For large payloads, prefer NDJSON chunks over base64 blobs to avoid memory spikes.

> **Framing:** Streamable HTTP uses NDJSON (one JSON object per line). Servers should flush after each object; proxies must not buffer indefinitely.

> **Compression:** Enable gzip at the proxy to reduce large content streams. MCP payloads compress well.

> **Protocol Layer Design:** The protocol layer is intentionally **clean and minimal** — errors are raised immediately without retries. This design keeps the protocol layer focused on message transport and compliance with the MCP specification. For production use cases requiring retry logic, error handling, rate limiting, or caching, use [chuk-tool-processor](https://pypi.org/project/chuk-tool-processor/) which provides composable wrappers for retries with exponential backoff, rate limiting, and caching. This separation of concerns allows you to choose the right retry strategy for your specific application needs.

> **Security:** When exposing Streamable HTTP, terminate TLS at a proxy and require auth (e.g., bearer tokens). For private CAs, configure your client's trust store (e.g., `SSL_CERT_FILE=/path/ca.pem`, `REQUESTS_CA_BUNDLE`, or `SSL_CERT_DIR`). The protocol layer is transport-agnostic and does not impose auth.

---

## Configuration Examples

### JSON config (client decides how to spawn/connect)

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "database.db"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

### Loading config in code

```python
from chuk_mcp import StdioServerParameters, stdio_client
from chuk_mcp.protocol.messages import send_initialize

params = StdioServerParameters(command="uvx", args=["mcp-server-sqlite", "--db-path", "database.db"])
async with stdio_client(params) as (read, write):
    init = await send_initialize(read, write)
    print("Connected to", init.serverInfo.name)
```

---

## Examples & Feature Demonstrations

The [`examples/`](examples/) directory contains comprehensive, working demonstrations of all MCP features:

### Quick Start Examples

* [`quickstart_minimal.py`](examples/quickstart_minimal.py) — Minimal MCP client setup
* [`quickstart_sqlite.py`](examples/quickstart_sqlite.py) — Working with SQLite MCP server
* [`quickstart_resources.py`](examples/quickstart_resources.py) — Accessing server resources
* [`quickstart_complete.py`](examples/quickstart_complete.py) — Multi-feature demo

### End-to-End (E2E) Examples

Complete **client-server pairs** built with pure chuk-mcp, demonstrating both client and server implementation for each MCP feature:

**Core Features:**

* [`e2e_tools_client.py`](examples/e2e_tools_client.py) — Tool registration, discovery, and invocation
* [`e2e_resources_client.py`](examples/e2e_resources_client.py) — Resource listing and reading
* [`e2e_prompts_client.py`](examples/e2e_prompts_client.py) — Reusable prompt templates

**Advanced Features:**

* [`e2e_roots_client.py`](examples/e2e_roots_client.py) — File system root management
* [`e2e_sampling_client.py`](examples/e2e_sampling_client.py) — Server-initiated LLM requests
* [`e2e_completion_client.py`](examples/e2e_completion_client.py) — Autocomplete functionality
* [`e2e_subscriptions_client.py`](examples/e2e_subscriptions_client.py) — Resource change notifications
* [`e2e_cancellation_client.py`](examples/e2e_cancellation_client.py) — Operation cancellation
* [`e2e_progress_client.py`](examples/e2e_progress_client.py) — Progress tracking
* [`e2e_logging_client.py`](examples/e2e_logging_client.py) — Log message handling
* [`e2e_elicitation_client.py`](examples/e2e_elicitation_client.py) — User input requests
* [`e2e_annotations_client.py`](examples/e2e_annotations_client.py) — Content metadata

**Error Handling:**

* [`initialize_error_handling.py`](examples/initialize_error_handling.py) — Comprehensive error handling patterns (OAuth 401, version mismatch, timeout, etc.)

**Running Examples:**

Many E2E examples are self-contained with their own **protocol-level server** built using pure chuk-mcp. Where relevant, the client starts the corresponding demo server:

```bash
# Run any example directly - the client will start its server
uv run python examples/e2e_tools_client.py

# Test all E2E examples
for example in examples/e2e_*_client.py; do
    echo "Testing $example"
    uv run python "$example" || exit 1
done
```

> **Note:** Where relevant, examples include a corresponding `e2e_*_server.py` showing a minimal server built with the same protocol layer.

See [`examples/README.md`](examples/README.md) for detailed documentation of all examples.

---

## Versioning & Compatibility

* `chuk-mcp` follows the MCP spec revisions and negotiates capabilities at **initialize**.
* Newer features are **capability-gated** and degrade gracefully with older servers.
* Optional typing/validation uses **Pydantic if available**, otherwise a lightweight fallback.

### 📋 Supported Protocol Versions (as of v0.10.x)

| Version | Status | Support Policy |
|---------|--------|----------------|
| `2026-07-28` | In progress | Not yet in a release — see [ROADMAP.md](ROADMAP.md) |
| `2025-06-18` | Latest shipped | Primary support, all features |
| `2025-03-26` | Stable | Full compatibility, maintained |
| `2024-11-05` | Legacy | Backward compatibility, deprecation TBD |

**Tested Platforms:** Linux, macOS, Windows (Python 3.11+)

> **Support Policy:** Latest and Stable versions receive full support. Legacy
> versions are retained for at least the twelve-month window the MCP
> [feature lifecycle policy](https://modelcontextprotocol.io/community/feature-lifecycle)
> defines. See [changelog](CHANGELOG.md) for migration guidance.

> **`2026-07-28`** is a breaking revision of MCP — stateless requests, no
> `initialize` handshake, no protocol sessions, multi round-trip results. Support
> is being built in the Rust core (`chuk-mcp-rs`) and is **not** in a published
> release yet; nothing in this README describes it. When it lands, legacy servers
> keep working with no configuration change: era is detected per endpoint and the
> default is `auto`. [ROADMAP.md](ROADMAP.md) tracks progress and
> [docs/design/mcp-2026-migration.md](docs/design/mcp-2026-migration.md) records
> the compatibility contract.

### 📊 Client Feature Support Matrix

| Feature Category | 2024-11-05 | 2025-03-26 | 2025-06-18 | Implementation Status |
|-----------------|------------|------------|------------|---------------------|
| **Core Operations** | | | | |
| Tools (list/call) | ✅ | ✅ | ✅ | ✅ Complete |
| Resources (list/read/subscribe) | ✅ | ✅ | ✅ | ✅ Complete |
| Prompts (list/get) | ✅ | ✅ | ✅ | ✅ Complete |
| **Transport** | | | | |
| Stdio | ✅ | ✅ | ✅ | ✅ Complete |
| Streamable HTTP | – | ✅ | ✅ | ✅ Complete |
| **Advanced Features** | | | | |
| Sampling | ✅ | ✅ | ✅ | ✅ Complete |
| Completion | ✅ | ✅ | ✅ | ✅ Complete |
| Roots | ✅ | ✅ | ✅ | ✅ Complete |
| Elicitation | ❌ | ❌ | ✅ | ✅ Complete |
| **Quality Features** | | | | |
| Progress Tracking | ✅ | ✅ | ✅ | ✅ Complete |
| Cancellation | ✅ | ✅ | ✅ | ✅ Complete |
| Notifications | ✅ | ✅ | ✅ | ✅ Complete |
| Logging | ✅ | ✅ | ✅ | ✅ Complete |
| Annotations | ✅ | ✅ | ✅ | ✅ Complete |

Features degrade gracefully when interacting with older servers.

> See the [changelog](CHANGELOG.md) for exact spec versions supported and any deprecations.

### Versioning Policy

This project follows [Semantic Versioning](https://semver.org/) for public APIs under `chuk_mcp.*`:
- **Major** (X.0.0): Breaking changes to public APIs
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, backward compatible

### Breaking Changes & Migration

#### v0.7.2: Exception Handling Changes

**What Changed**: `send_initialize()` and `send_initialize_with_client_tracking()` now **always raise exceptions** instead of returning `None` on errors.

**Why**: This enables proper error handling, automatic OAuth re-authentication in downstream tools (like mcp-cli), and follows Python best practices.

**Migration Guide**:

**Before (v0.7.1 and earlier)**:
```python
result = await send_initialize(read, write)
if result is None:
    logging.error("Initialization failed")
    return
# Use result
print(f"Connected to {result.serverInfo.name}")
```

**After (v0.7.2+)**:
```python
try:
    result = await send_initialize(read, write)
    # Success - result is guaranteed to be InitializeResult (not None)
    print(f"Connected to {result.serverInfo.name}")
except RetryableError as e:
    # Handle retryable errors (e.g., 401 authentication)
    logging.error(f"Retryable error: {e}")
except VersionMismatchError as e:
    # Handle version incompatibility
    logging.error(f"Version mismatch: {e}")
except TimeoutError as e:
    # Handle timeout
    logging.error(f"Timeout: {e}")
except Exception as e:
    # Handle other errors
    logging.error(f"Error: {e}")
```

**Return Type Changes**:
- `send_initialize()`: `Optional[InitializeResult]` → `InitializeResult`
- `send_initialize_with_client_tracking()`: `Optional[InitializeResult]` → `InitializeResult`

**Benefits**:
- ✅ Automatic OAuth re-authentication in mcp-cli
- ✅ Proper error propagation and debugging
- ✅ Type safety (no `Optional` checks needed)
- ✅ Full exception context with stack traces

**See Also**:
- [`EXCEPTION_HANDLING_FIX.md`](EXCEPTION_HANDLING_FIX.md) - Detailed technical documentation
- [`examples/initialize_error_handling.py`](examples/initialize_error_handling.py) - Complete error handling examples
- [`tests/mcp/messages/test_initialize_exceptions.py`](tests/mcp/messages/test_initialize_exceptions.py) - Test suite

---

## Comparison with Official MCP SDK

| Feature | chuk-mcp | Official MCP Python SDK |
|---------|----------|------------------------|
| **Philosophy** | Protocol compliance library | Full framework |
| **Scope** | Client + Server, protocol-focused | Client + Server framework |
| **Typing** | Optional Pydantic (fallback available) | Pydantic required |
| **Transports** | stdio, SSE, Streamable HTTP (pluggable) | stdio, SSE, Streamable HTTP |
| **Browser/WASM** | Pyodide-compatible | Varies / not a primary target |
| **Dependencies** | Minimal (anyio core) | Heavier stack |
| **Server Framework** | Lightweight helpers | Opinionated server structure |
| **API Style** | Explicit send_* functions | Higher-level abstractions |
| **Target Use Case** | Protocol integration, custom clients/servers | Full MCP applications |
| **Orchestration** | External (you choose) | Built-in patterns |
| **Learning Curve** | Low (protocol-level) | Medium (framework concepts) |

**When to choose chuk-mcp:**
- Building custom MCP clients or servers
- Need transport flexibility (Streamable HTTP)
- Want minimal dependencies
- Prefer protocol-level control
- Running in constrained environments (WASM, edge functions)
- Need to integrate MCP into existing applications

> **Real-world example:** [chuk-mcp-server](https://pypi.org/project/chuk-mcp-server/) uses chuk-mcp as its protocol compliance layer

**When to choose official SDK:**
- Building full MCP servers quickly with opinionated patterns
- Want framework abstractions out of the box
- Primarily using stdio transport
- Prefer higher-level APIs

---

## Design Goals & Non-Goals

**Goals**

* Be the **simplest way** to implement MCP in Python (client or server)
* Keep the API **small, explicit, and typed**
* Make **transports pluggable** and protocol logic reusable
* Support both **client and server** use cases with lightweight abstractions

**Non‑Goals**

* Competing with full agent frameworks / IDEs
* Baking in opinionated application structure or workflow engines
* Shipping heavyweight dependencies by default
* Providing high-level orchestration (that's your application layer)

---

## Scaling & Concurrency

`chuk-mcp` handles hundreds of concurrent connections efficiently with minimal resource usage:

### Concurrency Benchmarks

**Tested Performance** (see `benchmarks/PERFORMANCE_REPORT.md` for full details):
- **700+ concurrent connections** tested successfully (stopped at timeout, not capacity limit)
- **252+ connections/sec** throughput for rapid connection churn
- **~34KB memory per connection** with linear scaling
- **Zero memory leaks** verified over 200+ iterations

**Production Capacity Estimates:**
- Small scale (< 100 agents): 512MB RAM, 1 core
- Medium scale (100-1,000 agents): 1-2GB RAM, 2-4 cores
- Large scale (1,000-10,000 agents): 4-8GB RAM, 8+ cores
- Enterprise scale (10,000+ agents): Load balancing recommended

### Best Practices

**Pattern: Create all → Initialize all (Sequential)**
```python
# RECOMMENDED: Fastest pattern for multiple agents
agent1 = create_agent(mcp_config1)
agent2 = create_agent(mcp_config2)
agent3 = create_agent(mcp_config3)

# Then initialize
await agent1.initialize_tools()
await agent2.initialize_tools()
await agent3.initialize_tools()
```

**Pattern: Interleaved (Also Supported)**
```python
# WORKS: Fixed in v0.8.1 with lazy stream initialization
agent1 = create_agent(mcp_config1)
await agent1.initialize_tools()

agent2 = create_agent(mcp_config2)
await agent2.initialize_tools()

agent3 = create_agent(mcp_config3)  # No longer hangs!
await agent3.initialize_tools()
```

**Important:** Always use `StdioClient` as an async context manager:
```python
# CORRECT: Streams initialized in async context
async with StdioClient(params) as client:
    # Use client here
    pass

# INCORRECT: Don't access streams before __aenter__
client = StdioClient(params)
client.get_streams()  # ❌ Raises RuntimeError
```

### Monitoring Recommendations

For production deployments, monitor these metrics:
- **Active Connections**: Track concurrent client count
- **Memory Growth**: Should remain flat over time (~0.034MB per connection)
- **File Descriptors**: Monitor via `lsof` or `/proc/<pid>/fd`
- **Connection Success Rate**: Should maintain 100%

See [`benchmarks/PERFORMANCE_REPORT.md`](benchmarks/PERFORMANCE_REPORT.md) for detailed performance analysis and production deployment guidelines.

---

## FAQ

**Q: Does this include a server framework?**

A: **Yes**, at the protocol layer. `chuk-mcp` provides typed messages and helpers usable on both clients and servers, but it's **not** an opinionated server framework—you bring your own app structure/orchestration.

**Q: Is Pydantic required?**

A: No. If installed (Pydantic v2 only), you'll get richer types and validation. If not, the library uses a lightweight fallback with dict-based models.

**Q: Which transport should I use?**

A: Use **stdio** for local dev and child processes. Use **Streamable HTTP** for remote servers behind TLS with auth.

**Q: Where can I find more examples?**

A: See the [`examples/`](examples/) directory for comprehensive demonstrations of all MCP features, including both quick-start examples and full end-to-end client-server pairs. For a real-world server implementation, see [chuk-mcp-server](https://pypi.org/project/chuk-mcp-server/) which uses chuk-mcp as its protocol library.

**Q: How do I test my implementation?**

A: Run `make test` or `uv run pytest` to run the test suite. Use `make examples` (if present) to test all E2E examples. See the [Contributing](#contributing) section for details.

**Q: Is this production-ready?**

A: Yes. chuk-mcp is used in production environments. It includes error handling, type safety, and follows MCP protocol specifications. See the test coverage reports for confidence metrics.

**Q: Is it thread-safe?**

A: Client instances are not thread-safe across event loops. Share a client within a single async loop; use separate instances per loop/thread.

**Q: What's not included?**

A: Auth, TLS termination, persistence, and orchestration are app concerns—bring your own. chuk-mcp provides protocol compliance only. For browser/WASM frontends with CORS and TLS, terminate TLS at the proxy and set `Access-Control-Allow-Origin` to your frontend origin; avoid `*` with credentials.

**Q: How do I add retry logic and rate limiting?**

A: Use [chuk-tool-processor](https://pypi.org/project/chuk-tool-processor/) which provides composable wrappers for retries (with exponential backoff), rate limiting, and caching. chuk-mcp focuses on protocol compliance; chuk-tool-processor handles execution concerns.

**Q: What are common errors and how do I handle them?**

A: Common exceptions and recommended actions:

| Error Type | JSON-RPC Code | Action |
|------------|---------------|--------|
| **Parse error** | -32700 | Fix JSON syntax in request |
| **Invalid request** | -32600 | Check required fields (jsonrpc, method, id) |
| **Method not found** | -32601 | Verify method name and server capabilities |
| **Invalid params** | -32602 | Validate parameter types and required fields |
| **Internal error** | -32603 | Check server logs, retry operation |
| **Authentication error (401)** | -32603 | Re-authenticate (automatic in mcp-cli) |
| **Request cancelled** | -32800 | Handle cancellation gracefully |
| **Content too large** | -32801 | Reduce payload size or use streaming |
| **Connection/Transport** | varies | Check network, verify server is running |

**Note:** When using HTTP-based transports (SSE or Streamable HTTP), transport-layer errors (network failures, TLS issues, authentication problems) will appear as HTTP status codes before reaching the MCP protocol layer. However, once the transport is established, all MCP protocol errors follow the JSON-RPC error code system shown above.

All protocol errors inherit from base exception classes and are **always raised** (never return `None`). See examples for error handling patterns.

**Exception Handling Best Practices:**

```python
from chuk_mcp.protocol.types.errors import (
    RetryableError,
    NonRetryableError,
    VersionMismatchError
)
from chuk_mcp.protocol.messages import send_initialize

try:
    # Initialize connection
    result = await send_initialize(read, write)
    # Success - result is guaranteed to be InitializeResult (not None)
    print(f"Connected to {result.serverInfo.name}")

except VersionMismatchError as e:
    # Protocol version incompatibility - cannot recover
    logging.error(f"Version mismatch: {e}")
    # Disconnect and inform user

except RetryableError as e:
    # Retryable errors (e.g., 401 authentication failures)
    if "401" in str(e).lower() or "unauthorized" in str(e).lower():
        # Trigger OAuth re-authentication
        # In mcp-cli, this happens automatically
        logging.info("Re-authenticating...")
    else:
        # Other retryable errors - implement retry logic
        logging.warning(f"Retryable error: {e}")

except TimeoutError as e:
    # Server didn't respond in time
    logging.error(f"Timeout: {e}")
    # Retry with longer timeout or check server status

except NonRetryableError as e:
    # Non-retryable errors - log and fail
    logging.error(f"Fatal error: {e}")

except Exception as e:
    # Other unexpected errors
    logging.error(f"Unexpected error: {e}")
```

See [`examples/initialize_error_handling.py`](examples/initialize_error_handling.py) for comprehensive error handling demonstrations.

---

## Contributing

PRs welcome! Please:

1. Open a small, focused issue first (optional but helpful).
2. Add tests and type hints for new functionality.
3. Keep public APIs minimal and consistent.
4. Run the linters and test suite before submitting.

*PRs must maintain ≥85% coverage; enforced in CI along with `mypy` type checks and `ruff` linting.*

```bash
# Clone and setup
git clone <repository-url>
# or install from PyPI: pip install chuk-mcp
cd chuk-mcp
uv sync

# Install pre-commit hooks (optional)
pre-commit install

# Run examples
uv run python examples/quickstart_minimal.py

# Run tests
uv run pytest

# Type checking
uv run mypy src/chuk_mcp

# Or use the Makefile (if present)
make test
make typecheck
make lint
make examples
```

> **Bug reports / feature requests:** Issue templates available in `.github/`

> **Code of Conduct:** Contributors expected to follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)

### Security

If you believe you've found a security issue, please report it by opening a security advisory in the GitHub repository rather than opening a public issue.

---

## Feature Showcase

This section provides detailed code snippets demonstrating MCP features. All examples are production-ready with full type safety.

### 🔧 Tools — Calling Functions

Tools are functions that AI can invoke:

```python
from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call
from chuk_mcp.protocol.types.content import parse_content, TextContent

# List all available tools — returns typed ListToolsResult
tools_result = await send_tools_list(read, write)
print(f"📋 Available tools: {len(tools_result.tools)}")

for tool in tools_result.tools:
    print(f"  • {tool.name}: {tool.description}")

# Call a tool — returns typed ToolResult
result = await send_tools_call(
    read, write,
    name="greet",
    arguments={"name": "World"}
)

# Parse content with type safety
content = parse_content(result.content[0])
assert isinstance(content, TextContent)
print(f"✅ Result: {content.text}")
```

**Full example:** `uv run python examples/e2e_tools_client.py`

### 📄 Resources — Reading Data

Resources provide access to data sources (files, databases, APIs):

```python
from chuk_mcp.protocol.messages.resources import send_resources_list, send_resources_read

# List available resources — returns typed ListResourcesResult
resources_result = await send_resources_list(read, write)
print(f"📚 Found {len(resources_result.resources)} resources")

for resource in resources_result.resources:
    print(f"  • {resource.name}")
    print(f"    URI: {resource.uri}")

# Read a resource — returns typed ReadResourceResult
if resources_result.resources:
    uri = resources_result.resources[0].uri
    read_result = await send_resources_read(read, write, uri)

    for content in read_result.contents:
        if hasattr(content, 'text'):
            print(f"📖 Content: {content.text[:200]}...")
```

**Full example:** `uv run python examples/e2e_resources_client.py`

### 📡 Resource Subscriptions — Live Updates

Subscribe to resources for real-time change notifications:

```python
from chuk_mcp.protocol.messages.resources import (
    send_resources_subscribe,
    send_resources_unsubscribe
)

# Subscribe to a resource
uri = "file:///logs/app.log"
success = await send_resources_subscribe(read, write, uri)

if success:
    print(f"✅ Subscribed to {uri}")
    print("📡 Listening for changes...")

    # In a real app, handle notifications in a loop
    # Notifications arrive as messages from the server

    # Unsubscribe when done
    await send_resources_unsubscribe(read, write, uri)
    print("🔕 Unsubscribed")
```

**Full example:** `uv run python examples/e2e_subscriptions_client.py`

### 💬 Prompts — Template Management

Prompts are reusable templates with parameters:

```python
from chuk_mcp.protocol.messages.prompts import send_prompts_list, send_prompts_get

# List available prompts — returns typed ListPromptsResult
prompts_result = await send_prompts_list(read, write)
print(f"💬 Available prompts: {len(prompts_result.prompts)}")

for prompt in prompts_result.prompts:
    print(f"  • {prompt.name}: {prompt.description}")
    if hasattr(prompt, 'arguments') and prompt.arguments:
        args = [a.name for a in prompt.arguments]
        print(f"    Arguments: {', '.join(args)}")

# Get a prompt with arguments — returns typed GetPromptResult
prompt_result = await send_prompts_get(
    read, write,
    name="code_review",
    arguments={"file": "main.py", "language": "python"}
)

# Use the formatted messages
for message in prompt_result.messages:
    print(f"🤖 {message.role}: {message.content}")
```

**Full example:** `uv run python examples/e2e_prompts_client.py`

### 🎯 Sampling — AI Content Generation

Let servers request AI to generate content on their behalf (requires user approval):

```python
from chuk_mcp.protocol.messages.sampling import sample_text

# Check if server supports sampling
if hasattr(init_result.capabilities, 'sampling'):
    print("✅ Server supports sampling")

    # Server requests AI to generate content using helper
    result = await sample_text(
        read, write,
        prompt="Explain quantum computing in simple terms",
        max_tokens=1000,
        model_hint="claude",
        temperature=0.7
    )

    # Access typed response
    if hasattr(result.content, 'text'):
        print(f"🤖 AI Generated: {result.content.text}")

    print(f"📊 Model: {result.model}")
    print(f"🔢 Stop Reason: {result.stopReason or 'N/A'}")
```

**Use Case:** Servers can use sampling to generate code, documentation, or analysis based on data they have access to.

**Full example:** `uv run python examples/e2e_sampling_client.py`

### 📁 Roots — Directory Access Control

Roots define which directories the client allows servers to access.

```python
from chuk_mcp.protocol.messages.roots import (
    send_roots_list,
    send_roots_list_changed_notification
)

# Check if server supports roots
if hasattr(init_result.capabilities, 'roots'):
    print("✅ Server supports roots capability")

    # List current roots — returns typed ListRootsResult
    roots_result = await send_roots_list(read, write)

    print(f"📁 Available roots: {len(roots_result.roots)}")
    for root in roots_result.roots:
        print(f"  • {root.name}: {root.uri}")

    # Notify server when roots change
    await send_roots_list_changed_notification(write)
    print("📢 Notified server of roots change")
```

**Use Case:** Control which directories AI can access, enabling secure sandboxed operations.

**Full example:** `uv run python examples/e2e_roots_client.py`

### 🎭 Elicitation — User Input Requests

Elicitation allows servers to request structured input from users:

```python
from chuk_mcp.protocol.messages.elicitation import send_elicitation_request

# Server requests user input
response = await send_elicitation_request(
    read, write,
    prompt="Enter API credentials",
    fields=[
        {"name": "api_key", "type": "text", "required": True},
        {"name": "region", "type": "select", "options": ["us", "eu", "asia"]}
    ]
)

# Access user's input
print(f"User provided: {response.values}")
```

**Use Case:** Interactive workflows, OAuth flows, confirmation dialogs.

**Full example:** `uv run python examples/e2e_elicitation_client.py`

### 💡 Completion — Smart Autocomplete

Get intelligent suggestions for tool arguments:

```python
from chuk_mcp.protocol.messages.completions import (
    send_completion_complete,
    create_argument_info
)

# Get completions for a file path argument — returns typed CompletionResult
response = await send_completion_complete(
    read, write,
    ref={"type": "ref/resource", "uri": "file:///data/"},
    argument=create_argument_info(
        name="filename",
        value="sales_202"  # Partial input
    )
)

# Show suggestions
print("💡 Suggestions for 'sales_202':")
for value in response.completion.values:
    print(f"  • {value}")
```

**Full example:** `uv run python examples/e2e_completion_client.py`

### 📊 Progress Tracking

Monitor long-running operations with progress updates:

```python
from chuk_mcp.protocol.messages.tools import send_tools_call

# Call a long-running tool
# Progress notifications will be sent automatically
print("🔄 Starting long operation...")

result = await send_tools_call(
    read, write,
    name="process_large_dataset",
    arguments={"dataset": "sales_data.csv"}
)

print("✅ Operation complete")
# Progress notifications are handled automatically by the client
```

**Full example:** `uv run python examples/e2e_progress_client.py`

### 🚫 Cancellation

Cancel long-running operations with timeout:

```python
import anyio
from chuk_mcp.protocol.messages.cancellation import send_cancelled_notification
from chuk_mcp.protocol.messages.tools import send_tools_call

async def cancel_after_timeout():
    request_id = "long-op-123"

    async with anyio.create_task_group() as tg:
        # Start long-running operation
        tg.start_soon(send_tools_call, read, write, "process_large_dataset",
                      {"dataset": "big.csv"}, request_id)

        # Cancel after 2 seconds
        with anyio.move_on_after(2):
            await anyio.sleep(999)

        # Send cancellation
        await send_cancelled_notification(write, request_id=request_id, reason="timeout")
        print("🚫 Cancellation sent")

anyio.run(cancel_after_timeout)
```

**Full example:** `uv run python examples/e2e_cancellation_client.py`

### 🌐 Multiple Transports

Use different transport protocols for different scenarios:

```python
import anyio
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.transports.http import http_client, HttpClientParameters

async def main():
    # Stdio transport (local processes)
    p1 = StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "local.db"]
    )
    async with stdio_client(p1) as (r, w):
        init = await send_initialize(r, w)
        print("📡 Stdio:", init.serverInfo.name)

    # Streamable HTTP transport (remote servers)
    p2 = HttpClientParameters(url="http://localhost:8989/mcp")
    async with http_client(p2) as (r, w):
        init = await send_initialize(r, w)
        print("🌐 Streamable HTTP:", init.serverInfo.name)

anyio.run(main)
```

### 🔄 Multi-Server Orchestration

Connect to multiple servers simultaneously:

```python
from chuk_mcp import stdio_client, StdioServerParameters
from chuk_mcp.protocol.messages import send_initialize
from chuk_mcp.protocol.messages.tools import send_tools_list

servers = [
    StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "db1.db"]
    ),
    StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."]
    )
]

print("🔗 Connecting to multiple servers...")

for i, server_params in enumerate(servers, 1):
    try:
        async with stdio_client(server_params) as (read, write):
            init_result = await send_initialize(read, write)
            tools_result = await send_tools_list(read, write)

            print(f"\n📡 Server {i}: {init_result.serverInfo.name}")
            print(f"   Tools: {len(tools_result.tools)}")

            # Show first 3 tools
            for tool in tools_result.tools[:3]:
                print(f"   • {tool.name}")
    except Exception as e:
        print(f"⚠️ Server {i} failed: {e}")
```

### Type Safety & Validation

All protocol messages return fully typed results using Pydantic (or fallback validation):

```python
from chuk_mcp.protocol.types.content import parse_content, TextContent
from chuk_mcp.protocol.messages.tools import send_tools_call

# Call a tool and get a typed result
tool_result = await send_tools_call(read, write, name="greet", arguments={"name": "World"})

# Type-safe content parsing
content = parse_content(tool_result.content[0])
assert isinstance(content, TextContent)
print(content.text)
```

**Benefits:**

* **Typed returns**: All `send_*` functions return typed Pydantic models
* **Content parsing**: Use `parse_content()` for type-safe content handling
* **Runtime validation**: Automatic validation with clear error messages
* **IDE support**: Full autocomplete and type checking

### Monitoring & Logging

Built-in features for production environments:

```python
from chuk_mcp.protocol.messages.logging import send_logging_set_level

# Set server logging level
await send_logging_set_level(write, level="debug")
```

**Features:**

* Structured logging with configurable levels
* Performance monitoring (latency, error rates, throughput)
* Progress tracking and cancellation support
* Clean error propagation (no automatic retries at protocol layer)

**Full example:** `uv run python examples/e2e_logging_client.py`

---

## Ecosystem

`chuk-mcp` is part of a modular suite of Python MCP tools:

* **[chuk-tool-processor](https://pypi.org/project/chuk-tool-processor/)** — Reliable tool call execution with retries, caching, and exponential backoff
* **[chuk-mcp-server](https://pypi.org/project/chuk-mcp-server/)** — Real-world MCP server implementation built on chuk-mcp
* **[chuk-mcp-cli](https://pypi.org/project/chuk-mcp-cli/)** — Interactive CLI and playground for testing MCP servers

Each component focuses on doing one thing well and can be used independently or together. All of these build on `chuk-mcp`'s protocol layer, so they inherit the same low-latency, minimal-overhead characteristics.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
