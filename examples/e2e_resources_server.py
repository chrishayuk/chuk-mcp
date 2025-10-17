#!/usr/bin/env python3
"""
E2E Resources Server - Powered by chuk-mcp
Demonstrates server-side resource management using chuk-mcp framework.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run resources demo server."""
    capabilities = ServerCapabilities(resources={"listChanged": True})
    server = MCPServer(
        name="resources-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register resource handlers
    async def handle_resources_list(message, session_id):
        """
        Handle resources/list request.

        Returns list of available resources that can be read by clients.
        """
        resources = [
            {
                "uri": "file:///docs/api-reference.md",
                "name": "API Reference Documentation",
                "description": "Complete API reference for the system",
                "mimeType": "text/markdown",
            },
            {
                "uri": "file:///data/config.json",
                "name": "System Configuration",
                "description": "Current system configuration settings",
                "mimeType": "application/json",
            },
            {
                "uri": "file:///logs/app.log",
                "name": "Application Logs",
                "description": "Recent application log entries",
                "mimeType": "text/plain",
            },
        ]
        result = {"resources": resources}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_resources_read(message, session_id):
        """
        Handle resources/read request.

        Returns the content of a specific resource by URI.
        """
        params = message.params if hasattr(message, "params") else {}
        uri = params.get("uri") if isinstance(params, dict) else None

        # Simulate reading different resources
        if uri == "file:///docs/api-reference.md":
            content = [
                {
                    "uri": uri,
                    "mimeType": "text/markdown",
                    "text": """# API Reference

## Authentication
All API requests require authentication via API key.

## Endpoints

### GET /api/v1/users
Retrieve list of users.

**Parameters:**
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Response:**
```json
{
  "users": [...],
  "total": 1234
}
```

### POST /api/v1/users
Create a new user.

**Body:**
```json
{
  "name": "string",
  "email": "string"
}
```
""",
                }
            ]
        elif uri == "file:///data/config.json":
            content = [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": """{
  "environment": "production",
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "app_db"
  },
  "cache": {
    "enabled": true,
    "ttl": 3600
  },
  "features": {
    "beta_mode": false,
    "maintenance": false
  }
}""",
                }
            ]
        elif uri == "file:///logs/app.log":
            content = [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": """2025-10-17 10:30:15 INFO Starting application server
2025-10-17 10:30:16 INFO Database connection established
2025-10-17 10:30:16 INFO Cache initialized
2025-10-17 10:30:17 INFO Server listening on port 8080
2025-10-17 10:31:05 INFO Received request: GET /api/v1/users
2025-10-17 10:31:06 INFO Request completed: 200 OK (127ms)
2025-10-17 10:32:45 WARN Rate limit approaching for client 192.168.1.10
2025-10-17 10:35:10 INFO Health check passed
""",
                }
            ]
        else:
            content = [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": f"Resource not found: {uri}",
                }
            ]

        result = {"contents": content}
        return server.protocol_handler.create_response(message.id, result), None

    # Register protocol handlers
    server.protocol_handler.register_method("resources/list", handle_resources_list)
    server.protocol_handler.register_method("resources/read", handle_resources_read)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
