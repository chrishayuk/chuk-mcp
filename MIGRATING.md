# Migration Guide

This document provides guidance for migrating between major versions of chuk-mcp.

## Current Version: 0.6

chuk-mcp follows [Semantic Versioning](https://semver.org/). This guide will be updated when breaking changes are introduced.

## Future Migrations

### From 0.x to 1.0 (when released)

Migration notes will be added here when version 1.0 is released.

### Protocol Version Changes

chuk-mcp automatically negotiates protocol versions during initialization. If you need to support specific protocol versions:

```python
# Protocol version is negotiated automatically
# Client and server agree on the highest mutually-supported version
result = await send_initialize(read, write)
print(f"Negotiated version: {result.protocolVersion}")
```

## Breaking Changes

### Version 0.6

- **Pydantic v2 only**: Pydantic v1 is no longer supported. Upgrade to Pydantic 2.11.1+.
- **Python 3.11+ required**: Earlier Python versions are no longer supported.

## Deprecation Policy

- **Legacy protocol support** (2024-11-05): Maintained until 2026-Q2
- **Deprecated features**: Documented in [CHANGELOG.md](CHANGELOG.md)

## Need Help?

- Check the [FAQ](README.md#faq) for common migration questions
- Review [examples/](examples/) for updated usage patterns
- Open an issue for migration-specific questions
