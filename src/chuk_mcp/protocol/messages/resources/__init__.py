# chuk_mcp/protocol/messages/resources/__init__.py
"""
Resources module for the Model Context Protocol client.

This module provides functionality for working with MCP resources, which are
data that servers can provide to clients. Resources can be files, database
records, API responses, or any other data that can be read by URI.

Key features:
- Resource discovery and listing with pagination support
- Resource content reading (text and binary data)
- Resource templates for dynamic URI construction
- Subscription system for resource change notifications
- Support for MIME types and metadata

The resources feature enables:
- Clients to discover available resources from servers
- Reading resource content by URI
- Templates for parameterized resource access
- Real-time notifications when resources change
- Efficient pagination for large resource collections
"""

from .send_messages import (
    send_resources_list,
    send_resources_read,
    send_resources_templates_list,
    send_resources_subscribe,
    send_resources_unsubscribe,
    ListResourcesResult,
    ReadResourceResult,
    ListResourceTemplatesResult,
)

from .notifications import (
    handle_resources_list_changed_notification,
    handle_resources_updated_notification,
)

from .resource import Resource
from .resource_template import ResourceTemplate
from .resource_content import ResourceContent

__all__ = [
    # Core data models
    "Resource",
    "ResourceTemplate",
    "ResourceContent",
    # Result types
    "ListResourcesResult",
    "ReadResourceResult",
    "ListResourceTemplatesResult",
    # Resource messaging functions
    "send_resources_list",
    "send_resources_read",
    "send_resources_templates_list",
    "send_resources_subscribe",
    "send_resources_unsubscribe",
    # Notification handlers
    "handle_resources_list_changed_notification",
    "handle_resources_updated_notification",
]
