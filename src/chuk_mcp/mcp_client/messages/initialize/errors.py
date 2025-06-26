# chuk_mcp/mcp_client/messages/initialize/errors.py
from typing import Any, Dict, List

class VersionMismatchError(Exception):
    """
    Error raised when client and server protocol versions don't match.
    
    Follows MCP specification for version negotiation errors:
    - Uses error code -32602 (Invalid params) 
    - Includes structured data with supported/requested versions
    """
    
    def __init__(self, requested: str, supported: List[str]):
        self.requested = requested
        self.supported = supported
        
        # Create error message following MCP specification format
        message = "Unsupported protocol version"
        super().__init__(f"Protocol version mismatch. Requested: {requested}, Supported: {supported}")
        
        # Store MCP-compliant error data
        self.error_code = -32602  # INVALID_PARAMS per MCP spec
        self.error_message = message
        self.error_data = {
            "supported": supported,
            "requested": requested
        }   
    
    def to_json_rpc_error(self) -> Dict[str, Any]:
        """Convert to JSON-RPC error format following MCP specification."""
        return {
            "code": self.error_code,
            "message": self.error_message,
            "data": self.error_data
        }
    
    @classmethod
    def from_json_rpc_error(cls, error: Dict[str, Any]) -> 'VersionMismatchError':
        """Create VersionMismatchError from JSON-RPC error response."""
        data = error.get("data", {})
        requested = data.get("requested", "unknown")
        supported = data.get("supported", [])
        return cls(requested, supported)
    
    def __str__(self) -> str:
        """Human-readable error description."""
        return (f"MCP Protocol version mismatch: "
                f"Client requested '{self.requested}' but server supports {self.supported}")
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"VersionMismatchError(requested='{self.requested}', supported={self.supported})"