# chuk_mcp/server/protocol_handler.py
from typing import Dict, Any, Optional, Callable, Tuple
import logging

from ..protocol.messages.json_rpc_message import JSONRPCMessage
from ..protocol.types.info import ServerInfo
from ..protocol.types.capabilities import ServerCapabilities
from .session.memory import SessionManager


class ProtocolHandler:
    """Server-side MCP protocol handler."""
    
    def __init__(self, server_info: ServerInfo, capabilities: ServerCapabilities):
        self.server_info = server_info
        self.capabilities = capabilities
        self.session_manager = SessionManager()
        
        # Method handlers
        self._handlers: Dict[str, Callable] = {}
        self._register_core_handlers()
    
    def _register_core_handlers(self):
        """Register core protocol handlers."""
        self._handlers.update({
            "initialize": self._handle_initialize,
            "notifications/initialized": self._handle_initialized,
            "ping": self._handle_ping,
        })
    
    def register_method(self, method: str, handler: Callable):
        """Register a custom method handler."""
        self._handlers[method] = handler
    
    async def handle_message(
        self, 
        message: JSONRPCMessage, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[JSONRPCMessage], Optional[str]]:
        """Handle incoming message."""
        method = message.method
        if not method:
            return self.create_error_response(message.id, -32600, "Invalid request"), None
        
        # Update session activity
        if session_id:
            self.session_manager.update_activity(session_id)
        
        handler = self._handlers.get(method)
        if not handler:
            return self.create_error_response(message.id, -32601, f"Method not found: {method}"), None
        
        try:
            return await handler(message, session_id)
        except Exception as e:
            logging.error(f"Handler error for {method}: {e}")
            return self.create_error_response(message.id, -32603, f"Internal error: {str(e)}"), None
    
    async def _handle_initialize(self, message: JSONRPCMessage, session_id: Optional[str]):
        """Handle initialize request."""
        params = message.params or {}
        client_info = params.get("clientInfo", {})
        protocol_version = params.get("protocolVersion", "2025-03-26")
        
        # Create session
        new_session_id = self.session_manager.create_session(client_info, protocol_version)
        
        result = {
            "protocolVersion": protocol_version,
            "serverInfo": self.server_info.model_dump(),
            "capabilities": self.capabilities.model_dump(exclude_none=True)
        }
        
        return self.create_response(message.id, result), new_session_id
    
    async def _handle_initialized(self, message: JSONRPCMessage, session_id: Optional[str]):
        """Handle initialized notification."""
        return None, None  # Notifications don't return responses
    
    async def _handle_ping(self, message: JSONRPCMessage, session_id: Optional[str]):
        """Handle ping request."""
        return self.create_response(message.id, {}), None
    
    def create_response(self, msg_id: Any, result: Any) -> JSONRPCMessage:
        """Create success response."""
        return JSONRPCMessage.create_response(msg_id, result)
    
    def create_error_response(self, msg_id: Any, code: int, message: str) -> JSONRPCMessage:
        """Create error response."""
        return JSONRPCMessage.create_error_response(msg_id, code, message)