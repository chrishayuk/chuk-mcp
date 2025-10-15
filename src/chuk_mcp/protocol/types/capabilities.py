# chuk_mcp/protocol/types/capabilities.py
"""
MCP capability definitions for clients and servers.

These capabilities define what features are supported by MCP clients and servers
during the initialization handshake.
"""

from typing import Optional, Dict, Any
from ..mcp_pydantic_base import McpPydanticBase, Field


# Individual capability types (used by both client and server)
class LoggingCapability(McpPydanticBase):
    """Capability for logging operations - spec compliant."""

    model_config = {"extra": "allow"}


class PromptsCapability(McpPydanticBase):
    """Capability for prompts operations - spec compliant."""

    listChanged: Optional[bool] = None
    """Whether this supports notifications for changes to the prompt list."""
    model_config = {"extra": "allow"}


class ResourcesCapability(McpPydanticBase):
    """Capability for resources operations - spec compliant."""

    subscribe: Optional[bool] = None
    """Whether this supports subscribing to resource updates."""
    listChanged: Optional[bool] = None
    """Whether this supports notifications for changes to the resource list."""
    model_config = {"extra": "allow"}


class ToolsCapability(McpPydanticBase):
    """Capability for tools operations - spec compliant."""

    listChanged: Optional[bool] = None
    """Whether this supports notifications for changes to the tool list."""
    model_config = {"extra": "allow"}


class CompletionCapability(McpPydanticBase):
    """Capability for completion operations - spec compliant."""

    model_config = {"extra": "allow"}


class RootsCapability(McpPydanticBase):
    """Capability for root operations - spec compliant."""

    listChanged: Optional[bool] = None
    """Whether this supports notifications for changes to the roots list."""
    model_config = {"extra": "allow"}


class SamplingCapability(McpPydanticBase):
    """Capability for sampling operations - spec compliant."""

    model_config = {"extra": "allow"}


class ElicitationCapability(McpPydanticBase):
    """Capability for elicitation operations - spec compliant."""

    model_config = {"extra": "allow"}


# Server capabilities container
class ServerCapabilities(McpPydanticBase):
    """Capabilities that a server may support - matches official MCP specification."""

    experimental: Optional[Dict[str, Dict[str, Any]]] = None
    """Experimental, non-standard capabilities that the server supports."""

    logging: Optional[LoggingCapability] = None
    """Present if the server supports sending log messages to the client."""

    prompts: Optional[PromptsCapability] = None
    """Present if the server offers any prompt templates."""

    resources: Optional[ResourcesCapability] = None
    """Present if the server offers any resources to read."""

    tools: Optional[ToolsCapability] = None
    """Present if the server offers any tools to call."""

    completion: Optional[CompletionCapability] = None
    """Present if the server supports argument completion."""

    model_config = {"extra": "allow"}


# Client capabilities container
class ClientCapabilities(McpPydanticBase):
    """Capabilities a client may support - matches official MCP specification."""

    experimental: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)
    """Experimental, non-standard capabilities that the client supports."""

    sampling: Optional[SamplingCapability] = None
    """Present if the client supports sampling from an LLM."""

    elicitation: Optional[ElicitationCapability] = None
    """Present if the client supports elicitation from the user."""

    roots: Optional[RootsCapability] = Field(
        default_factory=lambda: RootsCapability(listChanged=True)
    )
    """Present if the client supports listing roots."""

    model_config = {"extra": "allow"}


# Legacy aliases for backward compatibility
MCPServerCapabilities = ServerCapabilities
MCPClientCapabilities = ClientCapabilities
