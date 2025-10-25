#!/usr/bin/env python3
"""
Comprehensive tests for notifications.py module.
"""

import pytest
import logging
from unittest.mock import AsyncMock

from chuk_mcp.protocol.messages.notifications import (
    send_progress_notification,
    handle_progress_notification,
    send_cancelled_notification,
    handle_cancelled_notification,
    handle_logging_message_notification,
    send_roots_list_changed_notification,
    NotificationHandler,
)
from chuk_mcp.protocol.messages.message_method import MessageMethod


class TestSendProgressNotification:
    """Test send_progress_notification function."""

    @pytest.mark.asyncio
    async def test_send_progress_basic(self):
        """Test sending basic progress notification."""
        write_stream = AsyncMock()

        await send_progress_notification(
            write_stream, progress_token="token-123", progress=50.0
        )

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.method == MessageMethod.NOTIFICATION_PROGRESS
        assert call_args.params["progressToken"] == "token-123"
        assert call_args.params["progress"] == 50.0

    @pytest.mark.asyncio
    async def test_send_progress_with_total(self):
        """Test sending progress with total."""
        write_stream = AsyncMock()

        await send_progress_notification(
            write_stream, progress_token="token-123", progress=50.0, total=100.0
        )

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.params["total"] == 100.0

    @pytest.mark.asyncio
    async def test_send_progress_with_message(self):
        """Test sending progress with message."""
        write_stream = AsyncMock()

        await send_progress_notification(
            write_stream,
            progress_token="token-123",
            progress=75.0,
            message="Processing files...",
        )

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.params["message"] == "Processing files..."

    @pytest.mark.asyncio
    async def test_send_progress_with_all_params(self):
        """Test sending progress with all parameters."""
        write_stream = AsyncMock()

        await send_progress_notification(
            write_stream,
            progress_token=12345,
            progress=33.3,
            total=99.9,
            message="Almost there",
        )

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.params["progressToken"] == 12345
        assert call_args.params["progress"] == 33.3
        assert call_args.params["total"] == 99.9
        assert call_args.params["message"] == "Almost there"

    @pytest.mark.asyncio
    async def test_send_progress_error_handling(self, caplog):
        """Test error handling when sending progress fails."""
        write_stream = AsyncMock()
        write_stream.send.side_effect = Exception("Send failed")

        with caplog.at_level(logging.ERROR):
            await send_progress_notification(
                write_stream, progress_token="token-123", progress=50.0
            )

        assert any(
            "Failed to send progress notification" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_send_progress_debug_logging(self, caplog):
        """Test debug logging for progress notification."""
        write_stream = AsyncMock()

        with caplog.at_level(logging.DEBUG):
            await send_progress_notification(
                write_stream, progress_token="token-123", progress=50.0, total=100.0
            )

        assert any(
            "Sent progress notification" in record.message for record in caplog.records
        )


class TestHandleProgressNotification:
    """Test handle_progress_notification function."""

    @pytest.mark.asyncio
    async def test_handle_progress_basic(self):
        """Test handling basic progress notification."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_PROGRESS,
            "params": {"progressToken": "token-123", "progress": 50.0},
        }

        await handle_progress_notification(callback, notification)

        callback.assert_called_once_with("token-123", 50.0, None, None)

    @pytest.mark.asyncio
    async def test_handle_progress_with_all_params(self):
        """Test handling progress with all parameters."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_PROGRESS,
            "params": {
                "progressToken": 12345,
                "progress": 75.5,
                "total": 100.0,
                "message": "Processing",
            },
        }

        await handle_progress_notification(callback, notification)

        callback.assert_called_once_with(12345, 75.5, 100.0, "Processing")

    @pytest.mark.asyncio
    async def test_handle_progress_wrong_method(self):
        """Test that handler ignores wrong method type."""
        callback = AsyncMock()

        notification = {"method": "other_method", "params": {}}

        await handle_progress_notification(callback, notification)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_progress_missing_params(self):
        """Test handling progress with missing params."""
        callback = AsyncMock()

        notification = {"method": MessageMethod.NOTIFICATION_PROGRESS, "params": {}}

        await handle_progress_notification(callback, notification)

        callback.assert_called_once_with(None, 0, None, None)


class TestSendCancelledNotification:
    """Test send_cancelled_notification function."""

    @pytest.mark.asyncio
    async def test_send_cancelled_basic(self):
        """Test sending basic cancellation notification."""
        write_stream = AsyncMock()

        await send_cancelled_notification(write_stream, request_id="req-123")

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.method == MessageMethod.NOTIFICATION_CANCELLED
        assert call_args.params["requestId"] == "req-123"

    @pytest.mark.asyncio
    async def test_send_cancelled_with_reason(self):
        """Test sending cancellation with reason."""
        write_stream = AsyncMock()

        await send_cancelled_notification(
            write_stream, request_id=456, reason="User cancelled"
        )

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.params["requestId"] == 456
        assert call_args.params["reason"] == "User cancelled"

    @pytest.mark.asyncio
    async def test_send_cancelled_error_handling(self, caplog):
        """Test error handling when sending cancellation fails."""
        write_stream = AsyncMock()
        write_stream.send.side_effect = Exception("Send failed")

        with caplog.at_level(logging.ERROR):
            await send_cancelled_notification(write_stream, request_id="req-123")

        assert any(
            "Failed to send cancellation notification" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_send_cancelled_debug_logging(self, caplog):
        """Test debug logging for cancellation."""
        write_stream = AsyncMock()

        with caplog.at_level(logging.DEBUG):
            await send_cancelled_notification(write_stream, request_id="req-123")

        assert any(
            "Sent cancellation for request req-123" in record.message
            for record in caplog.records
        )


class TestHandleCancelledNotification:
    """Test handle_cancelled_notification function."""

    @pytest.mark.asyncio
    async def test_handle_cancelled_basic(self):
        """Test handling basic cancellation notification."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_CANCELLED,
            "params": {"requestId": "req-123"},
        }

        await handle_cancelled_notification(callback, notification)

        callback.assert_called_once_with("req-123", None)

    @pytest.mark.asyncio
    async def test_handle_cancelled_with_reason(self):
        """Test handling cancellation with reason."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_CANCELLED,
            "params": {"requestId": 789, "reason": "Timeout"},
        }

        await handle_cancelled_notification(callback, notification)

        callback.assert_called_once_with(789, "Timeout")

    @pytest.mark.asyncio
    async def test_handle_cancelled_wrong_method(self):
        """Test that handler ignores wrong method type."""
        callback = AsyncMock()

        notification = {"method": "other_method", "params": {}}

        await handle_cancelled_notification(callback, notification)

        callback.assert_not_called()


class TestHandleLoggingMessageNotification:
    """Test handle_logging_message_notification function."""

    @pytest.mark.asyncio
    async def test_handle_logging_basic(self):
        """Test handling basic logging notification."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_MESSAGE,
            "params": {"level": "error", "data": "Something went wrong"},
        }

        await handle_logging_message_notification(callback, notification)

        callback.assert_called_once_with("error", "Something went wrong", None)

    @pytest.mark.asyncio
    async def test_handle_logging_with_logger(self):
        """Test handling logging with logger name."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_MESSAGE,
            "params": {
                "level": "debug",
                "data": {"key": "value"},
                "logger": "my.logger",
            },
        }

        await handle_logging_message_notification(callback, notification)

        callback.assert_called_once_with("debug", {"key": "value"}, "my.logger")

    @pytest.mark.asyncio
    async def test_handle_logging_default_level(self):
        """Test handling logging with default level."""
        callback = AsyncMock()

        notification = {
            "method": MessageMethod.NOTIFICATION_MESSAGE,
            "params": {"data": "Info message"},
        }

        await handle_logging_message_notification(callback, notification)

        callback.assert_called_once_with("info", "Info message", None)

    @pytest.mark.asyncio
    async def test_handle_logging_wrong_method(self):
        """Test that handler ignores wrong method type."""
        callback = AsyncMock()

        notification = {"method": "other_method", "params": {}}

        await handle_logging_message_notification(callback, notification)

        callback.assert_not_called()


class TestSendRootsListChangedNotification:
    """Test send_roots_list_changed_notification function."""

    @pytest.mark.asyncio
    async def test_send_roots_list_changed(self):
        """Test sending roots list changed notification."""
        write_stream = AsyncMock()

        await send_roots_list_changed_notification(write_stream)

        write_stream.send.assert_called_once()
        call_args = write_stream.send.call_args[0][0]
        assert call_args.method == MessageMethod.NOTIFICATION_ROOTS_LIST_CHANGED
        assert call_args.params == {}

    @pytest.mark.asyncio
    async def test_send_roots_list_changed_error_handling(self, caplog):
        """Test error handling when sending roots notification fails."""
        write_stream = AsyncMock()
        write_stream.send.side_effect = Exception("Send failed")

        with caplog.at_level(logging.ERROR):
            await send_roots_list_changed_notification(write_stream)

        assert any(
            "Failed to send roots list changed notification" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_send_roots_list_changed_debug_logging(self, caplog):
        """Test debug logging for roots notification."""
        write_stream = AsyncMock()

        with caplog.at_level(logging.DEBUG):
            await send_roots_list_changed_notification(write_stream)

        assert any(
            "Sent roots list changed notification" in record.message
            for record in caplog.records
        )


class TestNotificationHandler:
    """Test NotificationHandler class."""

    def test_notification_handler_init(self):
        """Test NotificationHandler initialization."""
        handler = NotificationHandler()

        assert isinstance(handler.handlers, dict)
        assert len(handler.handlers) == 0

    def test_register_handler(self, caplog):
        """Test registering a handler."""
        handler = NotificationHandler()

        async def my_handler(notification):
            pass

        with caplog.at_level(logging.DEBUG):
            handler.register("test_method", my_handler)

        assert "test_method" in handler.handlers
        assert handler.handlers["test_method"] == my_handler
        assert any(
            "Registered handler for test_method" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_handle_with_registered_handler(self):
        """Test handling notification with registered handler."""
        handler = NotificationHandler()

        mock_handler = AsyncMock()
        handler.register("test_method", mock_handler)

        notification = {"method": "test_method", "params": {"key": "value"}}

        await handler.handle(notification)

        mock_handler.assert_called_once_with(notification)

    @pytest.mark.asyncio
    async def test_handle_without_registered_handler(self, caplog):
        """Test handling notification without registered handler."""
        handler = NotificationHandler()

        notification = {"method": "unknown_method", "params": {}}

        with caplog.at_level(logging.DEBUG):
            await handler.handle(notification)

        assert any(
            "No handler registered for unknown_method" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_handle_no_method(self, caplog):
        """Test handling notification without method."""
        handler = NotificationHandler()

        notification = {"params": {}}

        with caplog.at_level(logging.WARNING):
            await handler.handle(notification)

        assert any(
            "Received notification without method" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_handle_handler_exception(self, caplog):
        """Test handling exception in handler."""
        handler = NotificationHandler()

        async def failing_handler(notification):
            raise ValueError("Handler error")

        handler.register("test_method", failing_handler)

        notification = {"method": "test_method", "params": {}}

        with caplog.at_level(logging.ERROR):
            await handler.handle(notification)

        assert any(
            "Error handling test_method notification" in record.message
            for record in caplog.records
        )

    def test_register_defaults(self):
        """Test registering default handlers."""
        handler = NotificationHandler()

        handler.register_defaults()

        # Check that default handlers are registered for all notification types
        assert MessageMethod.NOTIFICATION_INITIALIZED in handler.handlers
        assert MessageMethod.NOTIFICATION_PROGRESS in handler.handlers
        assert MessageMethod.NOTIFICATION_CANCELLED in handler.handlers
        assert MessageMethod.NOTIFICATION_MESSAGE in handler.handlers
        assert MessageMethod.NOTIFICATION_RESOURCES_LIST_CHANGED in handler.handlers
        assert MessageMethod.NOTIFICATION_RESOURCES_UPDATED in handler.handlers
        assert MessageMethod.NOTIFICATION_TOOLS_LIST_CHANGED in handler.handlers
        assert MessageMethod.NOTIFICATION_PROMPTS_LIST_CHANGED in handler.handlers
        assert MessageMethod.NOTIFICATION_ROOTS_LIST_CHANGED in handler.handlers

    @pytest.mark.asyncio
    async def test_register_defaults_logging(self, caplog):
        """Test that default handlers log notifications at DEBUG level."""
        handler = NotificationHandler()
        handler.register_defaults()

        notification = {
            "method": MessageMethod.NOTIFICATION_PROGRESS,
            "params": {"progress": 50},
        }

        with caplog.at_level(logging.DEBUG):
            await handler.handle(notification)

        assert any(
            "Notification" in record.message and "progress" in record.message.lower()
            for record in caplog.records
        )

    def test_multiple_registrations(self):
        """Test registering multiple handlers."""
        handler = NotificationHandler()

        async def handler1(notification):
            pass

        async def handler2(notification):
            pass

        async def handler3(notification):
            pass

        handler.register("method1", handler1)
        handler.register("method2", handler2)
        handler.register("method3", handler3)

        assert len(handler.handlers) == 3
        assert handler.handlers["method1"] == handler1
        assert handler.handlers["method2"] == handler2
        assert handler.handlers["method3"] == handler3

    def test_overwrite_registration(self):
        """Test overwriting a handler registration."""
        handler = NotificationHandler()

        async def handler1(notification):
            pass

        async def handler2(notification):
            pass

        handler.register("method", handler1)
        assert handler.handlers["method"] == handler1

        handler.register("method", handler2)
        assert handler.handlers["method"] == handler2

    @pytest.mark.asyncio
    async def test_handle_multiple_notifications(self):
        """Test handling multiple notifications."""
        handler = NotificationHandler()

        mock_handler1 = AsyncMock()
        mock_handler2 = AsyncMock()

        handler.register("method1", mock_handler1)
        handler.register("method2", mock_handler2)

        await handler.handle({"method": "method1", "params": {}})
        await handler.handle({"method": "method2", "params": {}})

        mock_handler1.assert_called_once()
        mock_handler2.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
