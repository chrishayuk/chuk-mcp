# chuk_mcp/protocol/types/errors.py
"""
MCP Protocol Error Codes and Exception Classes - Based on official specification and JSON-RPC 2.0
Updated for full spec compliance while maintaining existing functionality.
"""

from typing import Dict, Any, Optional

# Standard JSON-RPC 2.0 error codes (per official spec)
PARSE_ERROR = -32700
"""Invalid JSON was received by the server."""

INVALID_REQUEST = -32600
"""The JSON sent is not a valid Request object."""

METHOD_NOT_FOUND = -32601
"""The method does not exist / is not available."""

INVALID_PARAMS = -32602
"""Invalid method parameter(s)."""

INTERNAL_ERROR = -32603
"""Internal JSON-RPC error."""

# SDK error codes (from official MCP implementation)
CONNECTION_CLOSED = -32000
"""Connection has been closed."""

REQUEST_TIMEOUT = -32001
"""Request timed out."""

# Server error codes (reserved range -32000 to -32099)
SERVER_ERROR_START = -32000
SERVER_ERROR_END = -32099

# Additional MCP-specific error codes (in server error range)
MCP_INITIALIZATION_FAILED = -32002
"""MCP initialization failed."""

MCP_CAPABILITY_NOT_SUPPORTED = -32003
"""Requested capability is not supported."""

MCP_RESOURCE_NOT_FOUND = -32004
"""Requested resource was not found."""

MCP_TOOL_NOT_FOUND = -32005
"""Requested tool was not found."""

MCP_PROMPT_NOT_FOUND = -32006
"""Requested prompt was not found."""

MCP_AUTHORIZATION_FAILED = -32007
"""Authorization failed."""

MCP_PROTOCOL_VERSION_MISMATCH = -32008
"""Protocol version mismatch between client and server."""

# Define which errors are non-retryable (permanent errors)
NON_RETRYABLE_ERRORS = {
    PARSE_ERROR,  # JSON parsing error is permanent
    INVALID_REQUEST,  # Invalid request structure is permanent
    METHOD_NOT_FOUND,  # Method not found is permanent
    INVALID_PARAMS,  # Invalid params is a client error
    MCP_CAPABILITY_NOT_SUPPORTED,  # Capability mismatch is permanent
    MCP_TOOL_NOT_FOUND,  # Tool not found is permanent
    MCP_PROMPT_NOT_FOUND,  # Prompt not found is permanent
    MCP_AUTHORIZATION_FAILED,  # Auth failure is permanent
    MCP_PROTOCOL_VERSION_MISMATCH,  # Version mismatch is permanent
    CONNECTION_CLOSED,  # Connection closed is permanent
}

# Define which errors might be retryable
RETRYABLE_ERRORS = {
    INTERNAL_ERROR,  # Server might recover
    REQUEST_TIMEOUT,  # Timeout might be transient
    MCP_INITIALIZATION_FAILED,  # Might succeed on retry
    MCP_RESOURCE_NOT_FOUND,  # Resource might become available
}

# Error code descriptions following MCP specification
ERROR_MESSAGES = {
    # Standard JSON-RPC errors
    PARSE_ERROR: "Parse error: Invalid JSON was received by the server.",
    INVALID_REQUEST: "Invalid Request: The JSON sent is not a valid Request object.",
    METHOD_NOT_FOUND: "Method not found: The method does not exist / is not available.",
    INVALID_PARAMS: "Invalid params: Invalid method parameter(s).",
    INTERNAL_ERROR: "Internal error: Internal JSON-RPC error.",
    # SDK errors
    CONNECTION_CLOSED: "Connection closed",
    REQUEST_TIMEOUT: "Request timeout",
    # MCP-specific errors
    MCP_INITIALIZATION_FAILED: "MCP initialization failed",
    MCP_CAPABILITY_NOT_SUPPORTED: "Requested capability is not supported",
    MCP_RESOURCE_NOT_FOUND: "Requested resource was not found",
    MCP_TOOL_NOT_FOUND: "Requested tool was not found",
    MCP_PROMPT_NOT_FOUND: "Requested prompt was not found",
    MCP_AUTHORIZATION_FAILED: "Authorization failed",
    MCP_PROTOCOL_VERSION_MISMATCH: "Protocol version mismatch",
}


def get_error_message(code: int) -> str:
    """Get the description for an error code."""
    return ERROR_MESSAGES.get(code, f"Unknown error: Code {code}")


def is_retryable_error(code: int) -> bool:
    """
    Determine if an error should be retried.

    Args:
        code: The JSON-RPC error code

    Returns:
        True if the error might be transient and worth retrying
    """
    return code not in NON_RETRYABLE_ERRORS


def is_server_error(code: int) -> bool:
    """Check if the error code is in the server error range."""
    return SERVER_ERROR_END <= code <= SERVER_ERROR_START


def is_standard_jsonrpc_error(code: int) -> bool:
    """Check if the error code is a standard JSON-RPC error."""
    return code in {
        PARSE_ERROR,
        INVALID_REQUEST,
        METHOD_NOT_FOUND,
        INVALID_PARAMS,
        INTERNAL_ERROR,
    }


def is_mcp_specific_error(code: int) -> bool:
    """Check if the error code is MCP-specific."""
    mcp_codes = {
        MCP_INITIALIZATION_FAILED,
        MCP_CAPABILITY_NOT_SUPPORTED,
        MCP_RESOURCE_NOT_FOUND,
        MCP_TOOL_NOT_FOUND,
        MCP_PROMPT_NOT_FOUND,
        MCP_AUTHORIZATION_FAILED,
        MCP_PROTOCOL_VERSION_MISMATCH,
    }
    return code in mcp_codes


def create_error_data(
    code: int, message: str, data: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Create a properly formatted error response data structure.

    Args:
        code: The error code
        message: Human-readable error message
        data: Optional additional error data

    Returns:
        Dict formatted for JSON-RPC error response
    """
    error_dict = {"code": code, "message": message}

    if data is not None:
        error_dict["data"] = data

    return error_dict


# Exception Classes
class JSONRPCError(Exception):
    """Base class for JSON-RPC errors."""

    def __init__(self, message: str, code: int, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.data = data

    def to_json_rpc_error(self) -> Dict[str, Any]:
        """Convert to JSON-RPC error format."""
        return create_error_data(self.code, str(self), self.data)


class RetryableError(JSONRPCError):
    """Exception for JSON-RPC errors that can be retried."""

    pass


class NonRetryableError(JSONRPCError):
    """Exception for JSON-RPC errors that should not be retried."""

    pass


class MCPError(JSONRPCError):
    """Base class for MCP-specific errors."""

    pass


class ProtocolError(MCPError):
    """Error in MCP protocol handling."""

    def __init__(
        self,
        message: str,
        code: int = INTERNAL_ERROR,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, data)


class ValidationError(MCPError):
    """Error in data validation."""

    def __init__(
        self,
        message: str,
        code: int = INVALID_PARAMS,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, data)


class VersionMismatchError(MCPError):
    """Error raised when client and server protocol versions don't match."""

    def __init__(self, requested: str, supported: list[str]):
        self.requested = requested
        self.supported = supported

        message = (
            f"Protocol version mismatch. Requested: {requested}, Supported: {supported}"
        )
        data = {"supported": supported, "requested": requested}

        super().__init__(message, MCP_PROTOCOL_VERSION_MISMATCH, data)

    @classmethod
    def from_json_rpc_error(cls, error: Dict[str, Any]) -> "VersionMismatchError":
        """Create VersionMismatchError from JSON-RPC error response."""
        data = error.get("data", {})
        requested = data.get("requested", "unknown")
        supported = data.get("supported", [])
        return cls(requested, supported)


__all__ = [
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
    # Error code ranges
    "SERVER_ERROR_START",
    "SERVER_ERROR_END",
    # Error sets
    "NON_RETRYABLE_ERRORS",
    "RETRYABLE_ERRORS",
    "ERROR_MESSAGES",
    # Utility functions
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
]
