# chuk_mcp/protocol/types/__init__.py
"""
Shared type definitions for the Model Context Protocol.

This module contains type definitions that are used by both clients and servers,
ensuring consistency across the entire MCP ecosystem.
"""

from .capabilities import (
    # Individual capability types
    LoggingCapability,
    PromptsCapability,
    ResourcesCapability,
    ToolsCapability,
    CompletionCapability,
    RootsCapability,
    SamplingCapability,
    ElicitationCapability,
    # Capability containers
    ServerCapabilities,
    ClientCapabilities,
    # Legacy aliases
    MCPServerCapabilities,
    MCPClientCapabilities,
)

from .info import (
    ServerInfo,
    ClientInfo,
    # Legacy aliases
    MCPServerInfo,
    MCPClientInfo,
)

from .content import (
    # Content types
    Role,
    Annotations,
    TextContent,
    ImageContent,
    AudioContent,
    TextResourceContents,
    BlobResourceContents,
    ResourceContents,
    EmbeddedResource,
    Content,
    # Helper functions
    create_text_content,
    create_image_content,
    create_audio_content,
    create_embedded_resource,
    create_annotations,
    # Utility functions
    is_text_content,
    is_image_content,
    is_audio_content,
    is_embedded_resource,
    parse_content,
    content_to_dict,
)

from .errors import (
    # Error codes - Standard JSON-RPC
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    # Error codes - SDK
    CONNECTION_CLOSED,
    REQUEST_TIMEOUT,
    # Error codes - MCP specific
    MCP_INITIALIZATION_FAILED,
    MCP_CAPABILITY_NOT_SUPPORTED,
    MCP_RESOURCE_NOT_FOUND,
    MCP_TOOL_NOT_FOUND,
    MCP_PROMPT_NOT_FOUND,
    MCP_AUTHORIZATION_FAILED,
    MCP_PROTOCOL_VERSION_MISMATCH,
    # Error sets and utilities
    NON_RETRYABLE_ERRORS,
    RETRYABLE_ERRORS,
    ERROR_MESSAGES,
    get_error_message,
    is_retryable_error,
    is_server_error,
    is_standard_jsonrpc_error,
    is_mcp_specific_error,
    create_error_data,
    # Exception classes
    JSONRPCError,
    RetryableError,
    NonRetryableError,
    MCPError,
    ProtocolError,
    ValidationError,
    VersionMismatchError,
)

from .versioning import (
    SUPPORTED_VERSIONS,
    CURRENT_VERSION,
    ProtocolVersion,
    validate_version_compatibility,
)

__all__ = [
    # Individual capabilities
    "LoggingCapability",
    "PromptsCapability",
    "ResourcesCapability",
    "ToolsCapability",
    "CompletionCapability",
    "RootsCapability",
    "SamplingCapability",
    "ElicitationCapability",
    # Capability containers
    "ServerCapabilities",
    "ClientCapabilities",
    # Legacy capability aliases
    "MCPServerCapabilities",
    "MCPClientCapabilities",
    # Info types
    "ServerInfo",
    "ClientInfo",
    "MCPServerInfo",
    "MCPClientInfo",
    # Content types
    "Role",
    "Annotations",
    "TextContent",
    "ImageContent",
    "AudioContent",
    "TextResourceContents",
    "BlobResourceContents",
    "ResourceContents",
    "EmbeddedResource",
    "Content",
    # Content helpers
    "create_text_content",
    "create_image_content",
    "create_audio_content",
    "create_embedded_resource",
    "create_annotations",
    # Content utilities
    "is_text_content",
    "is_image_content",
    "is_audio_content",
    "is_embedded_resource",
    "parse_content",
    "content_to_dict",
    # Error codes - Standard JSON-RPC
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    # Error codes - SDK
    "CONNECTION_CLOSED",
    "REQUEST_TIMEOUT",
    # Error codes - MCP specific
    "MCP_INITIALIZATION_FAILED",
    "MCP_CAPABILITY_NOT_SUPPORTED",
    "MCP_RESOURCE_NOT_FOUND",
    "MCP_TOOL_NOT_FOUND",
    "MCP_PROMPT_NOT_FOUND",
    "MCP_AUTHORIZATION_FAILED",
    "MCP_PROTOCOL_VERSION_MISMATCH",
    # Error utilities
    "NON_RETRYABLE_ERRORS",
    "RETRYABLE_ERRORS",
    "ERROR_MESSAGES",
    "get_error_message",
    "is_retryable_error",
    "is_server_error",
    "is_standard_jsonrpc_error",
    "is_mcp_specific_error",
    "create_error_data",
    # Exception classes
    "JSONRPCError",
    "RetryableError",
    "NonRetryableError",
    "MCPError",
    "ProtocolError",
    "ValidationError",
    "VersionMismatchError",
    # Versioning
    "SUPPORTED_VERSIONS",
    "CURRENT_VERSION",
    "ProtocolVersion",
    "validate_version_compatibility",
]
