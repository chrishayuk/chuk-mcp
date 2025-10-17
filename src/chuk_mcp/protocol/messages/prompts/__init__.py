# chuk_mcp/protocol/messages/prompts/__init__.py
"""
Prompts module for the Model Context Protocol client.

This module provides functionality for working with MCP prompts, which are
reusable templates that servers can provide to help clients compose messages
for LLMs. Prompts can be parameterized with arguments to create dynamic
content based on user input or context.

Key features:
- Prompt discovery and listing with pagination support
- Prompt retrieval with argument substitution
- Template-based prompt generation with parameters
- Change notifications when prompt definitions are updated

The prompts feature enables:
- Servers to provide reusable prompt templates
- Clients to discover available prompts
- Dynamic prompt generation with custom arguments
- Real-time updates when prompt definitions change
- Consistent prompt formatting across applications
"""

from .prompt import (
    Prompt,
    PromptArgument,
    PromptMessage,
    ListPromptsResult,
    GetPromptResult,
)

from .send_messages import (
    send_prompts_list,
    send_prompts_get,
)

from .notifications import (
    handle_prompts_list_changed_notification,
)

__all__ = [
    # Prompt types
    "Prompt",
    "PromptArgument",
    "PromptMessage",
    "ListPromptsResult",
    "GetPromptResult",
    # Prompt messaging functions
    "send_prompts_list",
    "send_prompts_get",
    # Notification handlers
    "handle_prompts_list_changed_notification",
]
