# chuk_mcp/server/session/base.py
"""
Base session manager interface and session info.
"""

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
