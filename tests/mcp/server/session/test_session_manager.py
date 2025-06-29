#!/usr/bin/env python3
"""
Unit tests for the MCP session manager.
"""

import pytest
import time
from typing import Dict, Any

# Import the session manager components
from chuk_mcp.server.session.manager import SessionManager, SessionInfo


class TestSessionInfo:
    """Test the SessionInfo dataclass."""
    
    def test_session_info_creation(self):
        """Test SessionInfo creation."""
        client_info = {"name": "test-client", "version": "1.0.0"}
        metadata = {"key": "value"}
        
        session = SessionInfo(
            session_id="test-session-123",
            client_info=client_info,
            protocol_version="2025-06-18",
            created_at=1234567890.0,
            last_activity=1234567891.0,
            metadata=metadata
        )
        
        assert session.session_id == "test-session-123"
        assert session.client_info == client_info
        assert session.protocol_version == "2025-06-18"
        assert session.created_at == 1234567890.0
        assert session.last_activity == 1234567891.0
        assert session.metadata == metadata
    
    def test_session_info_equality(self):
        """Test SessionInfo equality."""
        session1 = SessionInfo(
            session_id="test-123",
            client_info={},
            protocol_version="2025-06-18",
            created_at=1234567890.0,
            last_activity=1234567891.0,
            metadata={}
        )
        
        session2 = SessionInfo(
            session_id="test-123",
            client_info={},
            protocol_version="2025-06-18",
            created_at=1234567890.0,
            last_activity=1234567891.0,
            metadata={}
        )
        
        assert session1 == session2
        
        # Different session ID should not be equal
        session3 = SessionInfo(
            session_id="test-456",
            client_info={},
            protocol_version="2025-06-18",
            created_at=1234567890.0,
            last_activity=1234567891.0,
            metadata={}
        )
        
        assert session1 != session3


class TestSessionManager:
    """Test the SessionManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh session manager."""
        return SessionManager()
    
    def test_initialization(self, manager):
        """Test session manager initialization."""
        assert isinstance(manager.sessions, dict)
        assert len(manager.sessions) == 0
    
    def test_create_session(self, manager):
        """Test session creation."""
        client_info = {"name": "test-client", "version": "1.0.0"}
        protocol_version = "2025-06-18"
        metadata = {"environment": "test"}
        
        session_id = manager.create_session(client_info, protocol_version, metadata)
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert "-" not in session_id  # UUIDs have dashes removed
        
        # Check session was stored
        assert session_id in manager.sessions
        session = manager.sessions[session_id]
        
        assert session.session_id == session_id
        assert session.client_info == client_info
        assert session.protocol_version == protocol_version
        assert session.metadata == metadata
        assert session.created_at <= time.time()
        assert session.last_activity <= time.time()
        assert session.created_at <= session.last_activity
    
    def test_create_session_defaults(self, manager):
        """Test session creation with default metadata."""
        client_info = {"name": "client"}
        protocol_version = "2025-06-18"
        
        session_id = manager.create_session(client_info, protocol_version)
        
        session = manager.sessions[session_id]
        assert session.metadata == {}
    
    def test_create_multiple_sessions(self, manager):
        """Test creating multiple sessions."""
        session_ids = []
        
        for i in range(5):
            client_info = {"name": f"client-{i}"}
            session_id = manager.create_session(client_info, "2025-06-18")
            session_ids.append(session_id)
        
        # All session IDs should be unique
        assert len(set(session_ids)) == 5
        
        # All sessions should be stored
        assert len(manager.sessions) == 5
        
        # Each session should have correct info
        for i, session_id in enumerate(session_ids):
            session = manager.sessions[session_id]
            assert session.client_info["name"] == f"client-{i}"
    
    def test_get_session_exists(self, manager):
        """Test getting an existing session."""
        client_info = {"name": "test-client"}
        session_id = manager.create_session(client_info, "2025-06-18")
        
        retrieved = manager.get_session(session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.client_info == client_info
    
    def test_get_session_not_exists(self, manager):
        """Test getting a non-existent session."""
        retrieved = manager.get_session("nonexistent-session-id")
        
        assert retrieved is None
    
    def test_update_activity(self, manager):
        """Test updating session activity."""
        client_info = {"name": "test-client"}
        session_id = manager.create_session(client_info, "2025-06-18")
        
        # Get initial activity time
        initial_activity = manager.sessions[session_id].last_activity
        
        # Small delay to ensure time difference
        time.sleep(0.01)
        
        # Update activity
        manager.update_activity(session_id)
        
        # Check activity was updated
        updated_activity = manager.sessions[session_id].last_activity
        assert updated_activity > initial_activity
    
    def test_update_activity_nonexistent(self, manager):
        """Test updating activity for non-existent session."""
        # Should not raise an error
        manager.update_activity("nonexistent-session-id")
        
        # Should not create a session
        assert len(manager.sessions) == 0
    
    def test_cleanup_expired_no_expired(self, manager):
        """Test cleanup when no sessions are expired."""
        # Create some recent sessions
        for i in range(3):
            manager.create_session({"name": f"client-{i}"}, "2025-06-18")
        
        # Cleanup with short max_age should not remove recent sessions
        removed = manager.cleanup_expired(max_age=3600)  # 1 hour
        
        assert removed == 0
        assert len(manager.sessions) == 3
    
    def test_cleanup_expired_with_expired(self, manager):
        """Test cleanup with expired sessions."""
        # Create sessions and manually set old activity times
        session_ids = []
        current_time = time.time()
        
        for i in range(3):
            session_id = manager.create_session({"name": f"client-{i}"}, "2025-06-18")
            session_ids.append(session_id)
            
            # Make first two sessions old
            if i < 2:
                manager.sessions[session_id].last_activity = current_time - 7200  # 2 hours ago
        
        # Cleanup with 1 hour max age
        removed = manager.cleanup_expired(max_age=3600)
        
        assert removed == 2
        assert len(manager.sessions) == 1
        
        # The remaining session should be the recent one
        remaining_session = list(manager.sessions.values())[0]
        assert remaining_session.client_info["name"] == "client-2"
    
    def test_cleanup_expired_all_expired(self, manager):
        """Test cleanup when all sessions are expired."""
        # Create sessions with old activity times
        current_time = time.time()
        
        for i in range(3):
            session_id = manager.create_session({"name": f"client-{i}"}, "2025-06-18")
            manager.sessions[session_id].last_activity = current_time - 7200  # 2 hours ago
        
        # Cleanup with 1 hour max age
        removed = manager.cleanup_expired(max_age=3600)
        
        assert removed == 3
        assert len(manager.sessions) == 0
    
    def test_list_sessions_empty(self, manager):
        """Test listing sessions when empty."""
        sessions = manager.list_sessions()
        
        assert isinstance(sessions, dict)
        assert len(sessions) == 0
    
    def test_list_sessions_with_data(self, manager):
        """Test listing sessions with data."""
        # Create some sessions
        session_ids = []
        for i in range(3):
            session_id = manager.create_session({"name": f"client-{i}"}, "2025-06-18")
            session_ids.append(session_id)
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 3
        assert set(sessions.keys()) == set(session_ids)
        
        # Check that it's a copy (modifying returned dict shouldn't affect manager)
        sessions.clear()
        assert len(manager.sessions) == 3
    
    def test_session_lifecycle(self, manager):
        """Test complete session lifecycle."""
        # Create session
        client_info = {"name": "lifecycle-client", "version": "2.0.0"}
        metadata = {"test": "lifecycle"}
        
        session_id = manager.create_session(client_info, "2025-06-18", metadata)
        
        # Verify creation
        assert session_id in manager.sessions
        session = manager.get_session(session_id)
        assert session is not None
        assert session.client_info == client_info
        assert session.metadata == metadata
        
        # Update activity multiple times
        initial_activity = session.last_activity
        
        for _ in range(3):
            time.sleep(0.01)
            manager.update_activity(session_id)
            
            updated_session = manager.get_session(session_id)
            assert updated_session.last_activity > initial_activity
            initial_activity = updated_session.last_activity
        
        # List sessions
        all_sessions = manager.list_sessions()
        assert session_id in all_sessions
        
        # Cleanup (shouldn't remove recent session)
        removed = manager.cleanup_expired(max_age=1)
        assert removed == 0
        assert session_id in manager.sessions
        
        # Force cleanup by setting old activity
        current_time = time.time()
        manager.sessions[session_id].last_activity = current_time - 7200
        
        removed = manager.cleanup_expired(max_age=3600)
        assert removed == 1
        assert session_id not in manager.sessions
        assert manager.get_session(session_id) is None


class TestSessionManagerConcurrency:
    """Test session manager behavior under concurrent access patterns."""
    
    def test_rapid_session_creation(self):
        """Test rapid session creation doesn't cause conflicts."""
        manager = SessionManager()
        session_ids = set()
        
        # Create many sessions rapidly
        for i in range(100):
            session_id = manager.create_session(
                {"name": f"rapid-client-{i}"}, 
                "2025-06-18"
            )
            session_ids.add(session_id)
        
        # All session IDs should be unique
        assert len(session_ids) == 100
        assert len(manager.sessions) == 100
    
    def test_mixed_operations(self):
        """Test mixed create/update/cleanup operations."""
        manager = SessionManager()
        session_ids = []
        
        # Create initial sessions
        for i in range(10):
            session_id = manager.create_session(
                {"name": f"mixed-client-{i}"}, 
                "2025-06-18"
            )
            session_ids.append(session_id)
        
        # Mix of operations
        current_time = time.time()
        
        # Update some sessions
        for session_id in session_ids[:5]:
            manager.update_activity(session_id)
        
        # Age some sessions
        for session_id in session_ids[5:]:
            manager.sessions[session_id].last_activity = current_time - 7200
        
        # Create more sessions
        for i in range(5):
            session_id = manager.create_session(
                {"name": f"new-client-{i}"}, 
                "2025-06-18"
            )
            session_ids.append(session_id)
        
        # Cleanup expired
        removed = manager.cleanup_expired(max_age=3600)
        
        # Should have removed the 5 aged sessions
        assert removed == 5
        # Should have 10 remaining (5 updated + 5 new)
        assert len(manager.sessions) == 10


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])