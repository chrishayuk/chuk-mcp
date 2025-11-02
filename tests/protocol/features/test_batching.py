#!/usr/bin/env python3
"""
Comprehensive tests for version-aware JSON-RPC batching support.
"""

import pytest
import logging

from chuk_mcp.protocol.features.batching import (
    supports_batching,
    should_reject_batch,
    BatchProcessor,
    _supports_batch_processing,
)


class TestSupportsBatching:
    """Test the supports_batching function."""

    def test_no_version_supports_batching(self):
        """Test that no version defaults to supporting batching."""
        assert supports_batching(None) is True

    def test_early_version_supports_batching(self):
        """Test that early versions support batching."""
        assert supports_batching("2024-11-05") is True
        assert supports_batching("2025-03-26") is True
        assert supports_batching("2025-06-17") is True

    def test_cutoff_version_no_batching(self):
        """Test that 2025-06-18 and later don't support batching."""
        assert supports_batching("2025-06-18") is False
        assert supports_batching("2025-06-19") is False
        assert supports_batching("2025-07-01") is False
        assert supports_batching("2026-01-01") is False

    def test_malformed_version_defaults_to_batching(self):
        """Test that malformed versions default to supporting batching."""
        assert supports_batching("invalid-version") is True
        assert supports_batching("2025") is True
        assert supports_batching("2025-06") is True
        assert supports_batching("not-a-version") is True

    def test_parse_error_defaults_to_batching(self):
        """Test that parse errors default to supporting batching."""
        assert supports_batching("abc-def-ghi") is True
        assert supports_batching("2025-xx-18") is True


class TestShouldRejectBatch:
    """Test the should_reject_batch function."""

    def test_single_message_not_rejected(self):
        """Test that single messages are never rejected."""
        assert should_reject_batch("2025-06-18", {"jsonrpc": "2.0"}) is False
        assert should_reject_batch(None, {"jsonrpc": "2.0"}) is False

    def test_batch_with_old_version_not_rejected(self):
        """Test that batch messages with old versions aren't rejected."""
        batch = [{"jsonrpc": "2.0"}, {"jsonrpc": "2.0"}]
        assert should_reject_batch("2024-11-05", batch) is False
        assert should_reject_batch("2025-06-17", batch) is False
        assert should_reject_batch(None, batch) is False

    def test_batch_with_new_version_rejected(self):
        """Test that batch messages with new versions are rejected."""
        batch = [{"jsonrpc": "2.0"}, {"jsonrpc": "2.0"}]
        assert should_reject_batch("2025-06-18", batch) is True
        assert should_reject_batch("2025-07-01", batch) is True
        assert should_reject_batch("2026-01-01", batch) is True


class TestBatchProcessor:
    """Test the BatchProcessor class."""

    def test_init_with_old_version(self):
        """Test initialization with old protocol version."""
        processor = BatchProcessor("2025-03-26")
        assert processor.protocol_version == "2025-03-26"
        assert processor.batching_enabled is True

    def test_init_with_new_version(self):
        """Test initialization with new protocol version."""
        processor = BatchProcessor("2025-06-18")
        assert processor.protocol_version == "2025-06-18"
        assert processor.batching_enabled is False

    def test_init_with_no_version(self):
        """Test initialization with no protocol version."""
        processor = BatchProcessor(None)
        assert processor.protocol_version is None
        assert processor.batching_enabled is True

    def test_update_protocol_version_enables_batching(self):
        """Test updating protocol version to enable batching."""
        processor = BatchProcessor("2025-06-18")
        assert processor.batching_enabled is False

        processor.update_protocol_version("2025-03-26")
        assert processor.protocol_version == "2025-03-26"
        assert processor.batching_enabled is True

    def test_update_protocol_version_disables_batching(self):
        """Test updating protocol version to disable batching."""
        processor = BatchProcessor("2025-03-26")
        assert processor.batching_enabled is True

        processor.update_protocol_version("2025-06-18")
        assert processor.protocol_version == "2025-06-18"
        assert processor.batching_enabled is False

    def test_update_protocol_version_no_change(self):
        """Test updating protocol version when batching support doesn't change."""
        processor = BatchProcessor("2025-03-26")
        processor.update_protocol_version("2024-11-05")
        assert processor.batching_enabled is True

    def test_can_process_batch_single_message(self):
        """Test that single messages can always be processed."""
        processor = BatchProcessor("2025-06-18")
        single_msg = {"jsonrpc": "2.0", "method": "test"}
        assert processor.can_process_batch(single_msg) is True

    def test_can_process_batch_with_batching_enabled(self):
        """Test batch processing when batching is enabled."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [{"jsonrpc": "2.0"}, {"jsonrpc": "2.0"}]
        assert processor.can_process_batch(batch_msg) is True

    def test_can_process_batch_with_batching_disabled(self):
        """Test batch processing when batching is disabled."""
        processor = BatchProcessor("2025-06-18")
        batch_msg = [{"jsonrpc": "2.0"}, {"jsonrpc": "2.0"}]
        assert processor.can_process_batch(batch_msg) is False

    def test_create_batch_rejection_error_no_id(self):
        """Test creating batch rejection error without message ID."""
        processor = BatchProcessor("2025-06-18")
        error = processor.create_batch_rejection_error()

        assert error["jsonrpc"] == "2.0"
        assert error["id"] is None
        assert error["error"]["code"] == -32600
        assert "not supported" in error["error"]["message"]
        assert error["error"]["data"]["protocol_version"] == "2025-06-18"
        assert error["error"]["data"]["batching_supported"] is False

    def test_create_batch_rejection_error_with_id(self):
        """Test creating batch rejection error with message ID."""
        processor = BatchProcessor("2025-06-18")
        error = processor.create_batch_rejection_error(message_id=123)

        assert error["id"] == 123

    def test_process_message_data_single_message(self):
        """Test processing single message data."""
        processor = BatchProcessor("2025-06-18")
        single_msg = {"jsonrpc": "2.0", "method": "test", "id": 1}

        handler_called = []

        def handler(msg):
            handler_called.append(msg)
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        result = processor.process_message_data(single_msg, handler)
        assert len(handler_called) == 1
        assert result["result"] == "ok"

    def test_process_message_data_batch_enabled(self):
        """Test processing batch message when batching is enabled."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        def handler(msg):
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        results = processor.process_message_data(batch_msg, handler)
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2

    def test_process_message_data_batch_disabled(self):
        """Test processing batch message when batching is disabled."""
        processor = BatchProcessor("2025-06-18")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        def handler(msg):
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        error = processor.process_message_data(batch_msg, handler)
        assert error["error"]["code"] == -32600

    def test_process_message_data_batch_with_notifications(self):
        """Test processing batch with notifications (no response)."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "notify"},  # No id = notification
            {"jsonrpc": "2.0", "method": "call", "id": 1},
        ]

        def handler(msg):
            if "id" in msg:
                return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}
            return None

        results = processor.process_message_data(batch_msg, handler)
        assert len(results) == 1  # Only one response, notification excluded
        assert results[0]["id"] == 1

    def test_process_message_data_batch_all_notifications(self):
        """Test processing batch with all notifications."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "notify1"},
            {"jsonrpc": "2.0", "method": "notify2"},
        ]

        def handler(msg):
            return None

        results = processor.process_message_data(batch_msg, handler)
        assert results is None  # All notifications, no response

    def test_process_message_data_batch_with_handler_error(self):
        """Test processing batch when handler raises exception."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        def handler(msg):
            if msg["id"] == 1:
                raise ValueError("Handler error")
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        results = processor.process_message_data(batch_msg, handler)
        assert len(results) == 2
        # First should be error
        assert "error" in results[0]
        assert results[0]["error"]["code"] == -32603
        # Second should be success
        assert "result" in results[1]

    def test_process_message_data_batch_with_non_dict_item(self):
        """Test processing batch with non-dict item that causes error."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [
            {"jsonrpc": "2.0", "method": "test", "id": 1},
            "invalid",  # This will cause handler to fail
        ]

        def handler(msg):
            if not isinstance(msg, dict):
                raise TypeError("Not a dict")
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        results = processor.process_message_data(batch_msg, handler)
        assert len(results) == 2
        assert "result" in results[0]
        assert "error" in results[1]


class TestLegacyFunction:
    """Test the legacy _supports_batch_processing function."""

    def test_legacy_function_with_warning(self):
        """Test that legacy function works but raises deprecation warning."""
        with pytest.warns(DeprecationWarning):
            result = _supports_batch_processing("2025-03-26")
            assert result is True

    def test_legacy_function_returns_correct_value(self):
        """Test that legacy function returns correct values."""
        with pytest.warns(DeprecationWarning):
            assert _supports_batch_processing("2025-03-26") is True
        with pytest.warns(DeprecationWarning):
            assert _supports_batch_processing("2025-06-18") is False


class TestLogging:
    """Test logging behavior."""

    def test_supports_batching_logs_debug(self, caplog):
        """Test that supports_batching logs debug messages."""
        with caplog.at_level(logging.DEBUG):
            supports_batching("2025-03-26")
            assert any(
                "supports batching" in record.message for record in caplog.records
            )

    def test_supports_batching_logs_warning_malformed(self, caplog):
        """Test that malformed version logs warning."""
        with caplog.at_level(logging.WARNING):
            supports_batching("invalid")
            assert any("Malformed" in record.message for record in caplog.records)

    def test_batch_processor_logs_info_on_change(self, caplog):
        """Test that batch processor logs when batching support changes."""
        processor = BatchProcessor("2025-03-26")
        with caplog.at_level(logging.INFO):
            processor.update_protocol_version("2025-06-18")
            assert any("changed" in record.message for record in caplog.records)

    def test_batch_processor_logs_warning_on_rejection(self, caplog):
        """Test that batch processor logs warning when rejecting batch."""
        processor = BatchProcessor("2025-06-18")
        batch_msg = [{"jsonrpc": "2.0"}, {"jsonrpc": "2.0"}]

        def handler(msg):
            return {"result": "ok"}

        with caplog.at_level(logging.WARNING):
            processor.process_message_data(batch_msg, handler)
            assert any("Rejecting batch" in record.message for record in caplog.records)

    def test_batch_processor_logs_debug_processing(self, caplog):
        """Test that batch processor logs debug when processing batch."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [{"jsonrpc": "2.0", "id": 1}, {"jsonrpc": "2.0", "id": 2}]

        def handler(msg):
            return {"jsonrpc": "2.0", "id": msg["id"], "result": "ok"}

        with caplog.at_level(logging.DEBUG):
            processor.process_message_data(batch_msg, handler)
            assert any(
                "Processing batch" in record.message for record in caplog.records
            )

    def test_batch_processor_logs_error_on_handler_failure(self, caplog):
        """Test that batch processor logs error when handler fails."""
        processor = BatchProcessor("2025-03-26")
        batch_msg = [{"jsonrpc": "2.0", "id": 1}]

        def handler(msg):
            raise ValueError("Handler failed")

        with caplog.at_level(logging.ERROR):
            processor.process_message_data(batch_msg, handler)
            assert any(
                "Error processing batch item" in record.message
                for record in caplog.records
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
