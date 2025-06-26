# chuk_mcp/mcp_client/messages/resources/__init__.py
"""
Resource-related message handling for the Model Context Protocol.
"""

from .send_messages import (
    send_resources_list,
    send_resources_read,
    send_resources_templates_list,
    send_resources_subscribe,
    send_resources_unsubscribe,  # Add this line
)

from .notifications import (
    handle_resources_list_changed_notification,
    handle_resources_updated_notification,
)

from .resource import Resource
from .resource_template import ResourceTemplate
from .resource_content import ResourceContent

__all__ = [
    # Send functions
    "send_resources_list",
    "send_resources_read",
    "send_resources_templates_list",
    "send_resources_subscribe",
    "send_resources_unsubscribe",  # Add this line
    
    # Notification handlers
    "handle_resources_list_changed_notification",
    "handle_resources_updated_notification",
    
    # Data models
    "Resource",
    "ResourceTemplate",
    "ResourceContent",
]