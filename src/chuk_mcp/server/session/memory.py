# chuk_mcp/server/session/memory.py
"""
In-memory session manager implementation.
"""

import time
from typing import Dict, Any, Optional

from .base import BaseSessionManager, SessionInfo


class InMemorySessionManager(BaseSessionManager):
    """In-memory implementation of session manager."""

    def __init__(self) -> None:
        """Initialize the in-memory session store."""
        self.sessions: Dict[str, SessionInfo] = {}

    def create_session(
        self,
        client_info: Dict[str, Any],
        protocol_version: str,
        metadata: Optional[Dict[str, Any]] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a new session in memory."""
        session_id = self.generate_session_id()

        session = SessionInfo(
            session_id=session_id,
            client_info=client_info,
            protocol_version=protocol_version,
            created_at=time.time(),
            last_activity=time.time(),
            metadata=metadata or {},
        )

        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID from memory."""
        return self.sessions.get(session_id)

    def update_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = time.time()
            return True
        return False

    def cleanup_expired(self, max_age: int = 3600) -> int:
        """Remove expired sessions from memory."""
        now = time.time()
        expired = [
            sid
            for sid, session in self.sessions.items()
            if now - session.last_activity > max_age
        ]

        for sid in expired:
            del self.sessions[sid]

        return len(expired)

    def list_sessions(self) -> Dict[str, SessionInfo]:
        """List all active sessions."""
        return self.sessions.copy()

    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_count(self) -> int:
        """Get the current number of active sessions."""
        return len(self.sessions)

    def clear_all_sessions(self) -> int:
        """Clear all sessions. Returns the number of sessions cleared."""
        count = len(self.sessions)
        self.sessions.clear()
        return count


# Backward compatibility alias
SessionManager = InMemorySessionManager
