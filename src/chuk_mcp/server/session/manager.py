# chuk_mcp/server/session/manager.py
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SessionInfo:
    """Information about an MCP session."""
    session_id: str
    client_info: Dict[str, Any]
    protocol_version: str
    created_at: float
    last_activity: float
    metadata: Dict[str, Any]


class SessionManager:
    """Manage MCP client sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
    
    def create_session(
        self, 
        client_info: Dict[str, Any], 
        protocol_version: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4()).replace("-", "")
        
        session = SessionInfo(
            session_id=session_id,
            client_info=client_info,
            protocol_version=protocol_version,
            created_at=time.time(),
            last_activity=time.time(),
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def update_activity(self, session_id: str):
        """Update session last activity."""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = time.time()
    
    def cleanup_expired(self, max_age: int = 3600) -> int:
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_activity > max_age
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        return len(expired)
    
    def list_sessions(self) -> Dict[str, SessionInfo]:
        """List all active sessions."""
        return self.sessions.copy()