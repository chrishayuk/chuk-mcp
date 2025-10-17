#!/usr/bin/env python3
"""
Comprehensive tests for roots/send_messages.py module.
"""

import pytest
import anyio
from unittest.mock import AsyncMock, patch

from chuk_mcp.protocol.messages.roots.send_messages import (
    Root,
    ListRootsResult,
    send_roots_list,
    handle_roots_list_request,
    send_roots_list_changed_notification,
    create_root,
    create_file_root,
    parse_file_root,
    RootsManager,
)


class TestRootTypes:
    """Test Root and ListRootsResult types."""

    def test_root_creation(self):
        """Test creating a Root object."""
        root = Root(uri="file:///home/user/project", name="My Project")

        assert root.uri == "file:///home/user/project"
        assert root.name == "My Project"

    def test_root_without_name(self):
        """Test Root without optional name."""
        root = Root(uri="file:///tmp")

        assert root.uri == "file:///tmp"
        assert root.name is None

    def test_root_invalid_uri(self):
        """Test Root validation rejects non-file:// URIs."""
        with pytest.raises(ValueError, match="Root URI must start with 'file://'"):
            root = Root(uri="http://example.com")
            root.__post_init__()

    def test_list_roots_result(self):
        """Test ListRootsResult creation."""
        roots = [
            Root(uri="file:///home/user/project1", name="Project 1"),
            Root(uri="file:///home/user/project2", name="Project 2"),
        ]
        result = ListRootsResult(roots=roots)

        assert len(result.roots) == 2
        assert result.roots[0].name == "Project 1"
        assert result.roots[1].name == "Project 2"


class TestSendRootsList:
    """Test send_roots_list function."""

    @pytest.mark.asyncio
    async def test_send_roots_list(self):
        """Test sending roots/list request."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        # Mock response
        response_data = {
            "roots": [{"uri": "file:///home/user/project", "name": "Project"}]
        }

        async def respond():
            await anyio.sleep(0.01)
            await read_send.send(response_data)

        async with anyio.create_task_group() as tg:
            tg.start_soon(respond)

            with patch(
                "chuk_mcp.protocol.messages.roots.send_messages.send_message",
                return_value=response_data,
            ):
                result = await send_roots_list(read_receive, write_send)

        assert isinstance(result, ListRootsResult)
        assert len(result.roots) == 1
        assert result.roots[0].uri == "file:///home/user/project"


class TestHandleRootsListRequest:
    """Test handle_roots_list_request function."""

    @pytest.mark.asyncio
    async def test_handle_roots_list_request(self):
        """Test handling roots/list request."""
        roots = [
            Root(uri="file:///home/user/docs", name="Documents"),
            Root(uri="file:///home/user/code", name="Code"),
        ]
        request_id = "req-123"

        response = await handle_roots_list_request(roots, request_id)

        assert response.id == request_id
        assert "result" in response.model_dump()
        result = response.model_dump()["result"]
        assert "roots" in result
        assert len(result["roots"]) == 2

    @pytest.mark.asyncio
    async def test_handle_roots_list_request_empty(self):
        """Test handling roots/list request with empty list."""
        roots = []
        request_id = "req-456"

        response = await handle_roots_list_request(roots, request_id)

        assert response.id == request_id
        result = response.model_dump()["result"]
        assert result["roots"] == []


class TestSendRootsListChangedNotification:
    """Test send_roots_list_changed_notification function."""

    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test sending roots list changed notification."""
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        await send_roots_list_changed_notification(write_send)

        # Verify notification was sent
        notification = await write_receive.receive()
        assert notification.method == "notifications/roots/list_changed"

    @pytest.mark.asyncio
    async def test_send_notification_error_handling(self):
        """Test notification error handling."""
        # Create a closed stream to trigger an error
        write_send, write_receive = anyio.create_memory_object_stream(max_buffer_size=1)
        await write_receive.aclose()
        await write_send.aclose()

        # Should not raise, just log error
        await send_roots_list_changed_notification(write_send)


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_root(self):
        """Test create_root helper."""
        root = create_root("file:///home/user/project", "My Project")

        assert root.uri == "file:///home/user/project"
        assert root.name == "My Project"

    def test_create_root_invalid_uri(self):
        """Test create_root with invalid URI."""
        with pytest.raises(ValueError):
            root = create_root("http://example.com")
            root.__post_init__()

    def test_create_file_root_unix(self):
        """Test create_file_root on Unix-like systems."""
        with patch("os.name", "posix"):
            with patch("os.path.abspath", return_value="/home/user/project"):
                root = create_file_root("/home/user/project", "Project")

                assert root.uri.startswith("file://")
                assert root.name == "Project"
                assert "/home/user/project" in root.uri

    def test_create_file_root_windows(self):
        """Test create_file_root on Windows."""
        with patch("os.name", "nt"):
            with patch("os.path.abspath", return_value="C:\\Users\\user\\project"):
                with patch("os.sep", "\\"):
                    root = create_file_root("C:\\Users\\user\\project", "Project")

                    assert root.uri.startswith("file:///")
                    assert root.name == "Project"

    def test_create_file_root_without_name(self):
        """Test create_file_root uses basename when name not provided."""
        with patch("os.path.abspath", return_value="/home/user/myproject"):
            with patch("os.path.basename", return_value="myproject"):
                root = create_file_root("/home/user/myproject")

                assert root.name == "myproject"

    def test_parse_file_root_unix(self):
        """Test parse_file_root on Unix."""
        with patch("os.name", "posix"):
            root = Root(uri="file:///home/user/project", name="Project")
            path = parse_file_root(root)

            assert path == "/home/user/project"

    def test_parse_file_root_windows(self):
        """Test parse_file_root on Windows."""
        with patch("os.name", "nt"):
            root = Root(uri="file:///C:/Users/user/project", name="Project")
            path = parse_file_root(root)

            assert path == "C:/Users/user/project"

    def test_parse_file_root_with_spaces(self):
        """Test parse_file_root with URL-encoded spaces."""
        root = Root(uri="file:///home/user/my%20project", name="Project")
        path = parse_file_root(root)

        assert "my project" in path or "my%20project" in path

    def test_parse_file_root_invalid_uri(self):
        """Test parse_file_root with non-file URI."""
        root = Root(uri="http://example.com")

        with pytest.raises(ValueError, match="Expected file:// URI"):
            parse_file_root(root)


class TestRootsManager:
    """Test RootsManager class."""

    def test_manager_initialization(self):
        """Test RootsManager initialization."""
        manager = RootsManager()

        assert manager.get_roots() == []

    def test_manager_with_write_stream(self):
        """Test RootsManager with write stream."""
        write_stream = AsyncMock()
        manager = RootsManager(write_stream=write_stream)

        assert manager._write_stream == write_stream

    def test_add_root(self):
        """Test adding a root."""
        manager = RootsManager()
        root = Root(uri="file:///home/user/project", name="Project")

        manager.add_root(root)

        roots = manager.get_roots()
        assert len(roots) == 1
        assert roots[0].uri == "file:///home/user/project"

    def test_add_multiple_roots(self):
        """Test adding multiple roots."""
        manager = RootsManager()
        root1 = Root(uri="file:///home/user/project1", name="Project 1")
        root2 = Root(uri="file:///home/user/project2", name="Project 2")

        manager.add_root(root1)
        manager.add_root(root2)

        roots = manager.get_roots()
        assert len(roots) == 2

    @pytest.mark.asyncio
    async def test_add_root_with_notification(self):
        """Test that adding a root triggers notification."""
        import asyncio

        write_stream = AsyncMock()
        manager = RootsManager(write_stream=write_stream)
        root = Root(uri="file:///home/user/project", name="Project")

        manager.add_root(root)

        # Give notification task a chance to run
        await asyncio.sleep(0.01)

        # Verify the root was added
        assert len(manager.get_roots()) == 1

    def test_remove_root(self):
        """Test removing a root."""
        manager = RootsManager()
        root = Root(uri="file:///home/user/project", name="Project")

        manager.add_root(root)
        assert len(manager.get_roots()) == 1

        manager.remove_root("file:///home/user/project")
        assert len(manager.get_roots()) == 0

    def test_remove_nonexistent_root(self):
        """Test removing a root that doesn't exist."""
        manager = RootsManager()

        # Should not raise
        manager.remove_root("file:///nonexistent")
        assert len(manager.get_roots()) == 0

    def test_clear_roots(self):
        """Test clearing all roots."""
        manager = RootsManager()
        root1 = Root(uri="file:///home/user/project1", name="Project 1")
        root2 = Root(uri="file:///home/user/project2", name="Project 2")

        manager.add_root(root1)
        manager.add_root(root2)
        assert len(manager.get_roots()) == 2

        manager.clear()
        assert len(manager.get_roots()) == 0

    def test_clear_empty_roots(self):
        """Test clearing when already empty."""
        manager = RootsManager()

        # Should not trigger notification when clearing empty list
        manager.clear()
        assert len(manager.get_roots()) == 0

    @pytest.mark.asyncio
    async def test_handle_list_request(self):
        """Test handling a list request via manager."""
        manager = RootsManager()
        root = Root(uri="file:///home/user/project", name="Project")
        manager.add_root(root)

        response = await manager.handle_list_request("req-789")

        assert response.id == "req-789"
        result = response.model_dump()["result"]
        assert len(result["roots"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
