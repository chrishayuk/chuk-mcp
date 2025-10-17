# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6] - 2025-01-XX

### Added
- Full protocol compliance for MCP 2025-06-18
- Client and server support
- Streamable HTTP transport (chunked/NDJSON)
- Stdio transport for local processes
- Type-safe protocol messages with optional Pydantic v2 support
- Comprehensive examples (quickstart + E2E client-server pairs)
- Protocol feature support:
  - Tools (list/call)
  - Resources (list/read/subscribe)
  - Prompts (list/get)
  - Roots management
  - Sampling & Completions
  - Progress tracking
  - Cancellation
  - Logging
  - Elicitation
  - Annotations

### Protocol Support
- **Latest**: `2025-06-18` (primary support)
- **Stable**: `2025-03-26` (full compatibility)
- **Legacy**: `2024-11-05` (backward compatibility)

### Breaking Changes
- Pydantic v2 only (v1 unsupported)
- Python 3.11+ required

## Versioning Policy

This project follows [Semantic Versioning](https://semver.org/) for public APIs under `chuk_mcp.*`:

- **Major version** (X.0.0): Breaking changes to public APIs
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, backward compatible
