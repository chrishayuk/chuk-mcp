# chuk_mcp/protocol/messages/completion/__init__.py
"""
Completion module for the Model Context Protocol client.

This module implements argument completion functionality for the MCP protocol,
allowing servers to provide intelligent autocompletion suggestions for tool
arguments, resource parameters, and prompt variables. This enhances the user
experience by providing contextual suggestions as users type.

Key features:
- Autocompletion for resource URI arguments
- Prompt argument completion with context awareness
- Reference-based completion system (resources and prompts)
- Server-side completion provider framework
- Built-in utilities for common completion scenarios
- Support for file path and enum value completion

Completion Flow:
1. Client sends completion/complete request with reference and partial argument
2. Server analyzes the context and current value
3. Server returns up to 100 completion suggestions
4. Client presents suggestions to user for selection

The completion system supports both:
- Resource references (ref/resource) for URI-based completions
- Prompt references (ref/prompt) for prompt argument completions
"""

from .send_messages import (
    # Core data models
    ResourceReference,
    PromptReference,
    Reference,
    ArgumentInfo,
    CompletionResult,
    # Main completion function
    send_completion_complete,
    # Helper creation functions
    create_resource_reference,
    create_prompt_reference,
    create_argument_info,
    # Convenience completion functions
    complete_resource_argument,
    complete_prompt_argument,
    # Server-side provider
    CompletionProvider,
    # Utility completion functions
    complete_file_path,
    complete_enum_value,
)

__all__ = [
    # Core data models
    "ResourceReference",
    "PromptReference",
    "Reference",
    "ArgumentInfo",
    "CompletionResult",
    # Primary completion function
    "send_completion_complete",
    # Object creation helpers
    "create_resource_reference",
    "create_prompt_reference",
    "create_argument_info",
    # Convenience functions
    "complete_resource_argument",
    "complete_prompt_argument",
    # Server implementation utilities
    "CompletionProvider",
    # Common completion utilities
    "complete_file_path",
    "complete_enum_value",
]
