# chuk_mcp/protocol/features/__init__.py
"""
Protocol features and utilities for MCP.

This module contains feature-specific implementations and utilities
that support different aspects of the MCP protocol.
"""

from .batching import (
    BatchProcessor,
    supports_batching,
    should_reject_batch,
    _supports_batch_processing,  # Legacy compatibility
)

__all__ = [
    "BatchProcessor",
    "supports_batching",
    "should_reject_batch",
    "_supports_batch_processing",
]
