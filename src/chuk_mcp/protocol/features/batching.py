# chuk_mcp/protocol/features/batching.py
"""
Version-aware JSON-RPC batching support for MCP.

This module handles batching behavior based on the negotiated protocol version:
- Versions before 2025-06-18: Support batching (JSON-RPC 2.0 compliant)
- Versions 2025-06-18+: No batching support (MCP spec deviation)
"""

from typing import List, Optional, Union, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


def supports_batching(protocol_version: Optional[str]) -> bool:
    """
    Check if the protocol version supports JSON-RPC batch processing.

    Batching was removed in version 2025-06-18 per MCP specification.

    Args:
        protocol_version: The negotiated protocol version

    Returns:
        True if batch processing is supported, False otherwise
    """
    if not protocol_version:
        # Default to supporting batch for backward compatibility with unversioned connections
        logger.debug("No protocol version specified, assuming batching support")
        return True

    try:
        # Parse version and check if it's before 2025-06-18
        version_parts = protocol_version.split("-")
        if len(version_parts) != 3:
            # Default for malformed versions
            logger.warning(
                f"Malformed protocol version '{protocol_version}', assuming batching support"
            )
            return True

        year = int(version_parts[0])
        month = int(version_parts[1])
        day = int(version_parts[2])

        # 2025-06-18 and later DON'T support batching
        if year > 2025:
            logger.debug(
                f"Protocol version {protocol_version} does not support batching (year > 2025)"
            )
            return False
        elif year == 2025 and month > 6:
            logger.debug(
                f"Protocol version {protocol_version} does not support batching (month > 6)"
            )
            return False
        elif year == 2025 and month == 6 and day >= 18:
            logger.debug(
                f"Protocol version {protocol_version} does not support batching (>= 2025-06-18)"
            )
            return False

        # All earlier versions support batching
        logger.debug(f"Protocol version {protocol_version} supports batching")
        return True

    except (ValueError, TypeError, IndexError) as e:
        # If we can't parse the version, default to supporting batch for safety
        logger.warning(
            f"Could not parse protocol version '{protocol_version}': {e}, assuming batching support"
        )
        return True


def should_reject_batch(protocol_version: Optional[str], message_data: Any) -> bool:
    """
    Check if a batch message should be rejected based on protocol version.

    Args:
        protocol_version: The negotiated protocol version
        message_data: The parsed JSON data (could be dict or list)

    Returns:
        True if the batch should be rejected, False otherwise
    """
    # Only reject if it's a batch and the version doesn't support batching
    is_batch = isinstance(message_data, list)
    version_rejects_batching = not supports_batching(protocol_version)

    return is_batch and version_rejects_batching


class BatchProcessor:
    """Handles version-aware batch processing for JSON-RPC messages."""

    def __init__(self, protocol_version: Optional[str] = None):
        self.protocol_version = protocol_version
        self.batching_enabled = supports_batching(protocol_version)

        logger.debug(
            f"BatchProcessor initialized for version {protocol_version}, batching={'enabled' if self.batching_enabled else 'disabled'}"
        )

    def update_protocol_version(self, version: str) -> None:
        """Update the protocol version and recalculate batching support."""
        old_batching = self.batching_enabled
        self.protocol_version = version
        self.batching_enabled = supports_batching(version)

        if old_batching != self.batching_enabled:
            logger.info(
                f"Batching support changed: {old_batching} -> {self.batching_enabled} (version: {version})"
            )

    def can_process_batch(self, message_data: Any) -> bool:
        """
        Check if we can process a batch message.

        Args:
            message_data: The parsed JSON data

        Returns:
            True if we can process it, False if it should be rejected
        """
        if not isinstance(message_data, list):
            return True  # Not a batch, always processable

        return self.batching_enabled

    def create_batch_rejection_error(
        self, message_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create an error response for rejected batch messages.

        Args:
            message_id: Optional message ID for the error response

        Returns:
            JSON-RPC error response
        """
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": -32600,  # Invalid Request
                "message": f"JSON-RPC batching not supported in protocol version {self.protocol_version}",
                "data": {
                    "protocol_version": self.protocol_version,
                    "batching_supported": False,
                    "upgrade_required": "Consider using individual requests or downgrading to a compatible protocol version",
                },
            },
        }

    def process_message_data(
        self, message_data: Any, handler_func: Callable
    ) -> Union[Dict, List, None]:
        """
        Process message data with version-aware batching.

        Args:
            message_data: The parsed JSON data (dict or list)
            handler_func: Function to handle individual messages

        Returns:
            Response data (dict for single, list for batch, None for notifications)
        """
        # Handle single messages
        if not isinstance(message_data, list):
            return handler_func(message_data)

        # Handle batch messages
        if not self.batching_enabled:
            # Return error for unsupported batch
            logger.warning(
                f"Rejecting batch message in protocol version {self.protocol_version}"
            )
            return self.create_batch_rejection_error()

        # Process each message in the batch
        logger.debug(f"Processing batch with {len(message_data)} messages")
        responses = []

        for item in message_data:
            try:
                response = handler_func(item)
                if response is not None:  # Don't include notification responses
                    responses.append(response)
            except Exception as e:
                logger.error(f"Error processing batch item: {e}")
                # Add error response for this item
                error_response = {
                    "jsonrpc": "2.0",
                    "id": item.get("id") if isinstance(item, dict) else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error processing batch item: {str(e)}",
                    },
                }
                responses.append(error_response)

        # Return batch response or None if all were notifications
        return responses if responses else None


# Legacy function for backward compatibility
def _supports_batch_processing(protocol_version: Optional[str]) -> bool:
    """
    Legacy function for backward compatibility.

    Use BatchProcessor or supports_batching() function instead.
    """
    import warnings

    warnings.warn(
        "_supports_batch_processing is deprecated. Use supports_batching() or BatchProcessor instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return supports_batching(protocol_version)


# Testing utilities
def test_version_batching_scenarios():
    """Test different version scenarios for batching support."""
    test_cases = [
        ("2024-11-05", True, "Early version should support batching"),
        ("2025-03-26", True, "Pre-2025-06-18 should support batching"),
        ("2025-06-18", False, "2025-06-18 should not support batching"),
        ("2025-07-01", False, "Post-2025-06-18 should not support batching"),
        (None, True, "No version should default to batching support"),
        ("invalid-version", True, "Invalid version should default to batching support"),
    ]

    for version, expected, description in test_cases:
        result = supports_batching(version)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}: {version} -> {result}")

    # Test batch processor
    print("\nTesting BatchProcessor:")

    for version in ["2025-03-26", "2025-06-18"]:
        processor = BatchProcessor(version)

        single_msg = {"jsonrpc": "2.0", "method": "test", "id": 1}
        batch_msg = [single_msg, single_msg]

        can_single = processor.can_process_batch(single_msg)
        can_batch = processor.can_process_batch(batch_msg)

        print(f"  Version {version}: single={can_single}, batch={can_batch}")


if __name__ == "__main__":
    # Run tests
    test_version_batching_scenarios()
