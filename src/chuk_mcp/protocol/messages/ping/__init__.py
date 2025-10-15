# chuk_mcp/protocol/messages/ping/__init__.py
"""
Ping module for the Model Context Protocol client.

This module provides ping functionality for testing connectivity and responsiveness
between MCP clients and servers. The ping feature is a simple health check mechanism
that helps verify that the connection is active and the server is responding.

Key features:
- Simple ping/pong communication for connectivity testing
- Configurable timeout and retry behavior
- Boolean response indicating success/failure
- Lightweight health check mechanism

The ping feature enables:
- Connection health monitoring
- Server responsiveness testing
- Network connectivity verification
- Simple debugging and diagnostics
"""

from .send_messages import (
    send_ping,
)

__all__ = [
    # Ping functionality
    "send_ping",
]
