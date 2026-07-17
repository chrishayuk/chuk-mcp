# chuk_mcp/protocol/messages/resources/__init__.py
"""Resource data models (retained pure-Python model layer).

The behavioural ``send_resources_*`` operations live in the Rust core and are
re-exported from ``chuk_mcp.protocol.messages``. These Pydantic model classes
remain in Python and are kept importable for downstream consumers.
"""

from .resource import Resource
from .resource_content import ResourceContent
from .resource_template import ResourceTemplate

__all__ = ["Resource", "ResourceContent", "ResourceTemplate"]
