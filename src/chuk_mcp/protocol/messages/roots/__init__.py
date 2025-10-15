# chuk_mcp/protocol/messages/roots/__init__.py
"""
Roots module for the Model Context Protocol client.

This module implements the client-side roots feature, which allows MCP servers
to discover what directories and files the client has access to. The roots
feature provides a way for clients to expose specific filesystem locations
that servers can operate on, enabling secure and controlled file access.

Key features:
- Root directory/file management and validation
- Support for file:// URI scheme with proper path conversion
- Notification system for root list changes
- Helper utilities for creating and managing roots
- Client-side root management with RootsManager class
"""

from .send_messages import (
    # Core data models
    Root,
    ListRootsResult,
    # Main messaging functions
    send_roots_list,
    handle_roots_list_request,
    send_roots_list_changed_notification,
    # Helper functions
    create_root,
    create_file_root,
    parse_file_root,
    # Management class
    RootsManager,
)

__all__ = [
    # Core data models
    "Root",
    "ListRootsResult",
    # Primary messaging functions
    "send_roots_list",
    "handle_roots_list_request",
    "send_roots_list_changed_notification",
    # Utility functions
    "create_root",
    "create_file_root",
    "parse_file_root",
    # Management utilities
    "RootsManager",
]
