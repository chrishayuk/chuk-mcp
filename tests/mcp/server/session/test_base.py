#!/usr/bin/env python3
"""
Unit tests for the base session manager interface.
"""

import pytest
from abc import ABC

from chuk_mcp.server.session.base import (
    BaseSessionManager,
    SessionInfo,
)


class TestBaseSessionManager:
    """Test the BaseSessionManager abstract base class."""

    def test_is_abstract(self):
        """Test that BaseSessionManager is an abstract class."""
        assert issubclass(BaseSessionManager, ABC)

    def test_cannot_instantiate_directly(self):
        """Test that BaseSessionManager cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            BaseSessionManager()

    def test_generate_session_id(self):
        """Test the generate_session_id method (only concrete method)."""

        # Create a minimal concrete implementation just to test generate_session_id
        class MinimalSessionManager(BaseSessionManager):
            def create_session(self, client_info, protocol_version, metadata=None):
                pass

            def get_session(self, session_id):
                pass

            def update_activity(self, session_id):
                pass

            def cleanup_expired(self, max_age=3600):
                pass

            def list_sessions(self):
                pass

            def delete_session(self, session_id):
                pass

        manager = MinimalSessionManager()

        # Generate some IDs and verify properties
        session_id1 = manager.generate_session_id()
        session_id2 = manager.generate_session_id()

        # Should be strings
        assert isinstance(session_id1, str)
        assert isinstance(session_id2, str)

        # Should not be empty
        assert len(session_id1) > 0
        assert len(session_id2) > 0

        # Should be unique (UUIDs)
        assert session_id1 != session_id2

        # Should not contain dashes (they are removed)
        assert "-" not in session_id1
        assert "-" not in session_id2

        # Should be 32 characters (UUID without dashes)
        assert len(session_id1) == 32
        assert len(session_id2) == 32

    def test_abstract_methods_exist(self):
        """Test that all abstract methods are defined."""
        abstract_methods = {
            "create_session",
            "get_session",
            "update_activity",
            "cleanup_expired",
            "list_sessions",
            "delete_session",
        }

        # Get abstract methods from BaseSessionManager
        manager_abstract = BaseSessionManager.__abstractmethods__

        assert abstract_methods == manager_abstract

    def test_custom_session_id_generation(self):
        """Test that generate_session_id can be overridden."""

        class CustomSessionManager(BaseSessionManager):
            def create_session(self, client_info, protocol_version, metadata=None):
                pass

            def get_session(self, session_id):
                pass

            def update_activity(self, session_id):
                pass

            def cleanup_expired(self, max_age=3600):
                pass

            def list_sessions(self):
                pass

            def delete_session(self, session_id):
                pass

            def generate_session_id(self):
                # Custom implementation
                return "custom-session-id"

        manager = CustomSessionManager()
        session_id = manager.generate_session_id()

        assert session_id == "custom-session-id"


class TestSessionInfoDataclass:
    """Additional tests for SessionInfo dataclass."""

    def test_session_info_attributes(self):
        """Test all SessionInfo attributes."""
        client_info = {"name": "test", "version": "1.0"}
        metadata = {"env": "test", "region": "us-west"}

        session = SessionInfo(
            session_id="abc123",
            client_info=client_info,
            protocol_version="2025-06-18",
            created_at=1234567890.5,
            last_activity=1234567891.7,
            metadata=metadata,
        )

        # Verify all attributes are accessible
        assert session.session_id == "abc123"
        assert session.client_info == client_info
        assert session.client_info["name"] == "test"
        assert session.protocol_version == "2025-06-18"
        assert session.created_at == 1234567890.5
        assert session.last_activity == 1234567891.7
        assert session.metadata == metadata
        assert session.metadata["env"] == "test"

    def test_session_info_immutability(self):
        """Test that SessionInfo fields can be modified (it's a dataclass)."""
        session = SessionInfo(
            session_id="test",
            client_info={},
            protocol_version="2025-06-18",
            created_at=100.0,
            last_activity=100.0,
            metadata={},
        )

        # Dataclasses are mutable by default
        session.last_activity = 200.0
        assert session.last_activity == 200.0

    def test_session_info_repr(self):
        """Test SessionInfo string representation."""
        session = SessionInfo(
            session_id="test123",
            client_info={"name": "client"},
            protocol_version="2025-06-18",
            created_at=1000.0,
            last_activity=1001.0,
            metadata={"key": "value"},
        )

        repr_str = repr(session)

        # Should contain the class name
        assert "SessionInfo" in repr_str

        # Should contain field names
        assert "session_id" in repr_str
        assert "test123" in repr_str

    def test_session_info_with_empty_dicts(self):
        """Test SessionInfo with empty dictionaries."""
        session = SessionInfo(
            session_id="empty",
            client_info={},
            protocol_version="2025-06-18",
            created_at=0.0,
            last_activity=0.0,
            metadata={},
        )

        assert session.client_info == {}
        assert session.metadata == {}
        assert len(session.client_info) == 0
        assert len(session.metadata) == 0

    def test_session_info_with_complex_data(self):
        """Test SessionInfo with complex nested data."""
        client_info = {
            "name": "complex-client",
            "version": "2.0.0",
            "capabilities": {
                "sampling": {"supported": True},
                "prompts": {"list_changed": True},
            },
            "tags": ["production", "high-priority"],
        }

        metadata = {
            "request_id": "req-123",
            "user": {"id": "user-456", "role": "admin"},
            "config": {"timeout": 30, "retry": 3},
        }

        session = SessionInfo(
            session_id="complex",
            client_info=client_info,
            protocol_version="2025-06-18",
            created_at=1234567890.0,
            last_activity=1234567890.0,
            metadata=metadata,
        )

        # Verify nested access works
        assert session.client_info["capabilities"]["sampling"]["supported"] is True
        assert session.client_info["tags"][0] == "production"
        assert session.metadata["user"]["role"] == "admin"
        assert session.metadata["config"]["timeout"] == 30


class TestBaseSessionManagerInterface:
    """Test the interface contract of BaseSessionManager."""

    def test_create_concrete_subclass(self):
        """Test creating a concrete implementation of BaseSessionManager."""

        class TestSessionManager(BaseSessionManager):
            def __init__(self):
                self.sessions = {}

            def create_session(self, client_info, protocol_version, metadata=None):
                session_id = self.generate_session_id()
                self.sessions[session_id] = {
                    "client_info": client_info,
                    "protocol_version": protocol_version,
                }
                return session_id

            def get_session(self, session_id):
                return self.sessions.get(session_id)

            def update_activity(self, session_id):
                if session_id in self.sessions:
                    return True
                return False

            def cleanup_expired(self, max_age=3600):
                return 0

            def list_sessions(self):
                return self.sessions.copy()

            def delete_session(self, session_id):
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    return True
                return False

        # Should be able to instantiate the concrete subclass
        manager = TestSessionManager()
        assert isinstance(manager, BaseSessionManager)

        # Test the interface works
        session_id = manager.create_session({"name": "test"}, "2025-06-18")
        assert session_id is not None

        session = manager.get_session(session_id)
        assert session is not None

        result = manager.update_activity(session_id)
        assert result is True

        sessions = manager.list_sessions()
        assert session_id in sessions

        result = manager.delete_session(session_id)
        assert result is True

        count = manager.cleanup_expired()
        assert count == 0

    def test_method_signatures(self):
        """Test that method signatures match the interface."""

        # Create a minimal implementation
        class SignatureTestManager(BaseSessionManager):
            def create_session(self, client_info, protocol_version, metadata=None):
                return "test-id"

            def get_session(self, session_id):
                return None

            def update_activity(self, session_id):
                return False

            def cleanup_expired(self, max_age=3600):
                return 0

            def list_sessions(self):
                return {}

            def delete_session(self, session_id):
                return False

        manager = SignatureTestManager()

        # Test create_session with different argument combinations
        session_id = manager.create_session({"name": "test"}, "2025-06-18")
        assert session_id == "test-id"

        session_id = manager.create_session({"name": "test"}, "2025-06-18", {"k": "v"})
        assert session_id == "test-id"

        # Test other methods
        result = manager.get_session("test-id")
        assert result is None

        result = manager.update_activity("test-id")
        assert result is False

        result = manager.cleanup_expired()
        assert result == 0

        result = manager.cleanup_expired(max_age=1800)
        assert result == 0

        result = manager.list_sessions()
        assert result == {}

        result = manager.delete_session("test-id")
        assert result is False


class TestModuleImports:
    """Test module-level imports and exports."""

    def test_base_module_imports(self):
        """Test that base module components can be imported."""
        from chuk_mcp.server.session.base import BaseSessionManager, SessionInfo

        assert BaseSessionManager is not None
        assert SessionInfo is not None

    def test_memory_module_imports(self):
        """Test that memory module components can be imported."""
        from chuk_mcp.server.session.memory import InMemorySessionManager

        assert InMemorySessionManager is not None

    def test_inmemory_session_manager(self):
        """Test that InMemorySessionManager works correctly."""
        from chuk_mcp.server.session.memory import InMemorySessionManager

        assert InMemorySessionManager is not None

        manager = InMemorySessionManager()
        assert manager is not None
        assert isinstance(manager.sessions, dict)

        session_id = manager.create_session(
            client_info={"name": "inline-test"}, protocol_version="2025-06-18"
        )
        assert session_id is not None

        session = manager.get_session(session_id)
        assert session is not None

        result = manager.update_activity(session_id)
        assert result is True

        result = manager.update_activity("nonexistent")
        assert result is False

        removed = manager.cleanup_expired(max_age=3600)
        assert removed >= 0

        sessions = manager.list_sessions()
        assert isinstance(sessions, dict)
        assert session_id in sessions

        result = manager.delete_session(session_id)
        assert result is True

        result = manager.delete_session("nonexistent")
        assert result is False

        count = manager.get_session_count()
        assert count >= 0

        manager.create_session({"name": "test"}, "2025-06-18")
        cleared = manager.clear_all_sessions()
        assert cleared >= 0

    def test_backward_compatibility_import(self):
        """Test backward compatibility SessionManager alias."""
        from chuk_mcp.server.session.base import SessionInfo
        from chuk_mcp.server.session.memory import InMemorySessionManager

        # These should all work
        manager1 = InMemorySessionManager()
        assert isinstance(manager1, BaseSessionManager)

        # Create a session to ensure it works
        session_id = manager1.create_session({"name": "test"}, "2025-06-18")
        assert session_id is not None

        session = manager1.get_session(session_id)
        assert isinstance(session, SessionInfo)

    def test_session_manager_alias(self):
        """Test SessionManager backward compatibility alias."""
        from chuk_mcp.server.session.memory import SessionManager

        assert SessionManager is not None

        # It should be an alias for InMemorySessionManager
        manager = SessionManager()
        assert manager is not None

        # Should work like InMemorySessionManager
        session_id = manager.create_session({"name": "alias-test"}, "2025-06-18")
        assert session_id is not None

    def test_package_all_exports(self):
        """Test __all__ exports from session package."""
        import chuk_mcp.server.session as session_module

        # Test that __all__ exists and contains expected items
        assert hasattr(session_module, "__all__")
        all_exports = session_module.__all__

        expected_exports = [
            "SessionInfo",
            "BaseSessionManager",
            "InMemorySessionManager",
            "SessionManager",
        ]

        for export in expected_exports:
            assert export in all_exports, f"{export} should be in __all__"

        # Test that all exported items are actually importable
        for export_name in all_exports:
            assert hasattr(session_module, export_name)
            export_obj = getattr(session_module, export_name)
            assert export_obj is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
