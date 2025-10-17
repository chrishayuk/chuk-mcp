# chuk_mcp/server/session/base.py
"""
Base session manager interface and session info.
"""

import time
import uuid
from abc import ABC, abstractmethod
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


class BaseSessionManager(ABC):
    """Base class for session managers - defines the interface."""

    @abstractmethod
    def create_session(
        self,
        client_info: Dict[str, Any],
        protocol_version: str,
        metadata: Optional[Dict[str, Any]] = None,  # type: ignore[assignment]
    ) -> str:
        """
        Create a new session.

        Args:
            client_info: Information about the client
            protocol_version: MCP protocol version
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session by ID.

        Args:
            session_id: The session identifier

        Returns:
            SessionInfo if found, None otherwise
        """
        pass

    @abstractmethod
    def update_activity(self, session_id: str) -> bool:
        """
        Update session last activity timestamp.

        Args:
            session_id: The session identifier

        Returns:
            True if session was found and updated, False otherwise
        """
        pass

    @abstractmethod
    def cleanup_expired(self, max_age: int = 3600) -> int:
        """
        Remove expired sessions.

        Args:
            max_age: Maximum age in seconds before a session is considered expired

        Returns:
            Number of sessions removed
        """
        pass

    @abstractmethod
    def list_sessions(self) -> Dict[str, SessionInfo]:
        """
        List all active sessions.

        Returns:
            Dictionary mapping session IDs to SessionInfo objects
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: The session identifier

        Returns:
            True if session was found and deleted, False otherwise
        """
        pass

    def generate_session_id(self) -> str:
        """
        Generate a new session ID.
        Can be overridden by subclasses for custom ID generation.

        Returns:
            A unique session identifier
        """
        return str(uuid.uuid4()).replace("-", "")


# chuk_mcp/server/session/memory.py
"""
In-memory session manager implementation.
"""
from typing import Dict, Any, Optional  # noqa: E402

from .base import BaseSessionManager, SessionInfo  # noqa: E402, F811


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


# chuk_mcp/server/session/manager.py
"""
Session manager - backward compatibility wrapper.
"""
from .memory import InMemorySessionManager  # noqa: E402, F811  # type: ignore[assignment]

# For backward compatibility, alias the memory implementation as SessionManager
SessionManager = InMemorySessionManager  # type: ignore[misc]

# Re-export everything for convenience
from .base import SessionInfo, BaseSessionManager  # noqa: E402, F811
from .memory import InMemorySessionManager  # noqa: E402, F811  # type: ignore[assignment]

__all__ = [
    "SessionInfo",
    "BaseSessionManager",
    "InMemorySessionManager",
    "SessionManager",  # backward compatibility
]
