# chuk_mcp/protocol/messages/sampling/__init__.py
"""
Sampling module for the Model Context Protocol client.

This module implements the client-side sampling feature, which allows MCP servers
to request that the client sample from an LLM on their behalf. This enables servers
to generate content using the client's LLM capabilities while maintaining proper
user oversight and control.

The sampling feature includes:
- Message creation and conversation handling
- Model selection preferences and hints
- User approval workflows for sampling requests
- Helper functions for common sampling patterns
"""

from .send_messages import (
    # Type definitions
    IncludeContext,
    StopReason,
    SamplingMessage,
    ModelHint,
    ModelPreferences,
    CreateMessageResult,
    # Main sampling function
    send_sampling_create_message,
    # Helper functions
    create_sampling_message,
    create_model_preferences,
    sample_text,
    sample_conversation,
    # Client-side handler
    SamplingHandler,
    # Parsing utilities
    parse_sampling_message,
    parse_create_message_result,
)

__all__ = [
    # Type definitions and literals
    "IncludeContext",
    "StopReason",
    # Core data models
    "SamplingMessage",
    "ModelHint",
    "ModelPreferences",
    "CreateMessageResult",
    # Primary sampling function
    "send_sampling_create_message",
    # Convenience helpers
    "create_sampling_message",
    "create_model_preferences",
    "sample_text",
    "sample_conversation",
    # Client implementation utilities
    "SamplingHandler",
    # Parsing and validation
    "parse_sampling_message",
    "parse_create_message_result",
]
