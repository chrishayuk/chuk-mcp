# chuk_mcp/protocol/messages/prompts/prompt.py
from typing import Optional, List
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class PromptArgument(McpPydanticBase):
    """Argument definition for a prompt template."""

    name: str
    """The name of the argument."""

    description: Optional[str] = None
    """Optional description of what the argument is for."""

    required: Optional[bool] = None
    """Whether this argument is required."""

    model_config = {"extra": "allow"}


class Prompt(McpPydanticBase):
    """A prompt template that can be used by clients."""

    name: str
    """The name of the prompt."""

    description: Optional[str] = None
    """Optional description of what the prompt does."""

    arguments: Optional[List[PromptArgument]] = None
    """List of arguments this prompt accepts."""

    model_config = {"extra": "allow"}


class PromptMessage(McpPydanticBase):
    """A message in a prompt response."""

    role: str
    """The role of the message (e.g., 'user', 'assistant')."""

    content: dict
    """The content of the message."""

    model_config = {"extra": "allow"}


class GetPromptResult(McpPydanticBase):
    """Result of getting a specific prompt."""

    description: Optional[str] = None
    """Optional description of the prompt."""

    messages: Optional[List[PromptMessage]] = None
    """The messages that make up this prompt."""

    model_config = {"extra": "allow"}


class ListPromptsResult(McpPydanticBase):
    """Result of listing prompts."""

    prompts: List[Prompt]
    """List of available prompts."""

    nextCursor: Optional[str] = None
    """Pagination cursor for fetching more prompts."""

    model_config = {"extra": "allow"}
