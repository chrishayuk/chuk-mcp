# chuk_mcp/protocol/messages/sampling/send_messages.py
"""
Sampling feature implementation for the Model Context Protocol.

This module implements the client-side sampling feature, which allows servers
to request that the client sample from an LLM on their behalf.
"""

from typing import List, Dict, Any, Optional, Literal, Union
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.protocol.messages.send_message import send_message
from chuk_mcp.protocol.messages.message_method import MessageMethod
from chuk_mcp.protocol.types.content import (
    Content,
    TextContent,
    ImageContent,
    AudioContent,
    create_text_content,
    Role,
)
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field


# Type definitions
IncludeContext = Literal["none", "thisServer", "allServers"]
StopReason = Literal["endTurn", "stopSequence", "maxTokens"]


class SamplingMessage(McpPydanticBase):
    """Describes a message issued to or received from an LLM API."""

    role: Role
    """The role of the message sender."""

    content: Union[TextContent, ImageContent, AudioContent]
    """The content of the message."""

    model_config = {"extra": "allow"}


class ModelHint(McpPydanticBase):
    """
    Hints to use for model selection.

    Keys not declared here are currently left unspecified by the spec
    and are up to the client to interpret.
    """

    name: Optional[str] = None
    """
    A hint for a model name.
    
    The client SHOULD treat this as a substring of a model name; for example:
     - `claude-3-5-sonnet` should match `claude-3-5-sonnet-20241022`
     - `sonnet` should match `claude-3-5-sonnet-20241022`, `claude-3-sonnet-20240229`, etc.
     - `claude` should match any Claude model
    
    The client MAY also map the string to a different provider's model name or 
    a different model family, as long as it fills a similar niche.
    """

    model_config = {"extra": "allow"}


class ModelPreferences(McpPydanticBase):
    """
    The server's preferences for model selection, requested of the client during sampling.

    Because LLMs can vary along multiple dimensions, choosing the "best" model is
    rarely straightforward. Different models excel in different areas—some are
    faster but less capable, others are more capable but more expensive, and so
    on. This interface allows servers to express their priorities across multiple
    dimensions to help clients make an appropriate selection for their use case.

    These preferences are always advisory. The client MAY ignore them. It is also
    up to the client to decide how to interpret these preferences and how to
    balance them against other considerations.
    """

    hints: Optional[List[ModelHint]] = None
    """
    Optional hints to use for model selection.
    
    If multiple hints are specified, the client MUST evaluate them in order
    (such that the first match is taken).
    
    The client SHOULD prioritize these hints over the numeric priorities, but
    MAY still use the priorities to select from ambiguous matches.
    """

    costPriority: Optional[float] = Field(None, ge=0.0, le=1.0)
    """
    How much to prioritize cost when selecting a model. A value of 0 means cost
    is not important, while a value of 1 means cost is the most important factor.
    """

    speedPriority: Optional[float] = Field(None, ge=0.0, le=1.0)
    """
    How much to prioritize sampling speed (latency) when selecting a model. A
    value of 0 means speed is not important, while a value of 1 means speed is
    the most important factor.
    """

    intelligencePriority: Optional[float] = Field(None, ge=0.0, le=1.0)
    """
    How much to prioritize intelligence and capabilities when selecting a
    model. A value of 0 means intelligence is not important, while a value of 1
    means intelligence is the most important factor.
    """

    model_config = {"extra": "allow"}


class CreateMessageResult(McpPydanticBase):
    """
    The client's response to a sampling/createMessage request from the server.
    """

    role: Role
    """The role of the generated message."""

    content: Union[TextContent, ImageContent, AudioContent]
    """The content of the generated message."""

    model: str
    """The name of the model that generated the message."""

    stopReason: Optional[Union[StopReason, str]] = None
    """The reason why sampling stopped, if known."""

    # MCP spec requires _meta field support
    meta: Optional[Dict[str, Any]] = Field(default=None, alias="_meta")
    """MCP metadata field."""

    model_config = {"extra": "allow"}


async def send_sampling_create_message(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    messages: List[Union[Dict[str, Any], SamplingMessage]],
    max_tokens: int,
    model_preferences: Optional[Union[Dict[str, Any], ModelPreferences]] = None,
    system_prompt: Optional[str] = None,
    include_context: Optional[IncludeContext] = None,
    temperature: Optional[float] = None,
    stop_sequences: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Request the client to sample from an LLM.

    The client has full discretion over which model to select. The client
    should also inform the user before beginning sampling, to allow them to
    inspect the request (human in the loop) and decide whether to approve it.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        messages: List of messages to send to the LLM
        max_tokens: Maximum number of tokens to sample
        model_preferences: Optional preferences for model selection
        system_prompt: Optional system prompt to use
        include_context: Whether to include context from MCP servers
        temperature: Optional temperature for sampling
        stop_sequences: Optional list of stop sequences
        metadata: Optional metadata to pass to the LLM provider
        timeout: Timeout in seconds (longer default for LLM calls)

    Returns:
        CreateMessageResult with content and model info

    Raises:
        Exception: If the client rejects the request or an error occurs
    """
    # Convert messages to dicts if needed
    messages_list = []
    for msg in messages:
        if hasattr(msg, "model_dump"):
            messages_list.append(msg.model_dump())
        else:
            messages_list.append(msg)

    # Build params
    params = {
        "messages": messages_list,
        "maxTokens": max_tokens,
    }

    # Add optional parameters
    if model_preferences is not None:
        if hasattr(model_preferences, "model_dump"):
            params["modelPreferences"] = model_preferences.model_dump()
        else:
            params["modelPreferences"] = model_preferences

    if system_prompt is not None:
        params["systemPrompt"] = system_prompt

    if include_context is not None:
        params["includeContext"] = include_context

    if temperature is not None:
        params["temperature"] = temperature

    if stop_sequences is not None:
        params["stopSequences"] = stop_sequences

    if metadata is not None:
        params["metadata"] = metadata

    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method=MessageMethod.SAMPLING_CREATE_MESSAGE,
        params=params,
        timeout=timeout,
    )

    return response


# Helper functions


def create_sampling_message(
    role: Role, content: Union[str, Content]
) -> SamplingMessage:
    """
    Create a sampling message.

    Args:
        role: The role (user or assistant)
        content: Text string or Content object

    Returns:
        SamplingMessage object
    """
    if isinstance(content, str):
        content_obj: Content = create_text_content(content)  # type: ignore[assignment]
    else:
        content_obj = content

    return SamplingMessage(role=role, content=content_obj)  # type: ignore[arg-type]


def create_model_preferences(
    hints: Optional[List[str]] = None,
    cost_priority: Optional[float] = None,
    speed_priority: Optional[float] = None,
    intelligence_priority: Optional[float] = None,
) -> ModelPreferences:
    """
    Create model preferences for sampling.

    Args:
        hints: List of model name hints (evaluated in order)
        cost_priority: Priority for cost (0.0 to 1.0)
        speed_priority: Priority for speed (0.0 to 1.0)
        intelligence_priority: Priority for intelligence (0.0 to 1.0)

    Returns:
        ModelPreferences object
    """
    model_hints = None
    if hints:
        model_hints = [ModelHint(name=hint) for hint in hints]

    return ModelPreferences(
        hints=model_hints,
        costPriority=cost_priority,
        speedPriority=speed_priority,
        intelligencePriority=intelligence_priority,
    )


async def sample_text(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    prompt: str,
    max_tokens: int = 1000,
    model_hint: Optional[str] = None,
    temperature: Optional[float] = None,
    system_prompt: Optional[str] = None,
    timeout: float = 60.0,
) -> CreateMessageResult:
    """
    Simplified helper to sample text from an LLM.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        prompt: The user prompt
        max_tokens: Maximum tokens to generate
        model_hint: Optional model name hint
        temperature: Optional temperature
        system_prompt: Optional system prompt
        timeout: Timeout in seconds

    Returns:
        CreateMessageResult with the generated text
    """
    messages = [create_sampling_message("user", prompt)]

    model_prefs = None
    if model_hint:
        model_prefs = create_model_preferences(hints=[model_hint])

    response = await send_sampling_create_message(
        read_stream=read_stream,
        write_stream=write_stream,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=max_tokens,
        model_preferences=model_prefs,
        system_prompt=system_prompt,
        temperature=temperature,
        timeout=timeout,
    )

    return CreateMessageResult.model_validate(response)


async def sample_conversation(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    conversation: List[tuple[Role, str]],
    max_tokens: int = 1000,
    model_preferences: Optional[ModelPreferences] = None,
    temperature: Optional[float] = None,
    include_context: Optional[IncludeContext] = None,
    timeout: float = 60.0,
) -> CreateMessageResult:
    """
    Sample from an LLM with a conversation history.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        conversation: List of (role, content) tuples
        max_tokens: Maximum tokens to generate
        model_preferences: Optional model preferences
        temperature: Optional temperature
        include_context: Whether to include MCP context
        timeout: Timeout in seconds

    Returns:
        CreateMessageResult with the generated response
    """
    messages = [
        create_sampling_message(role, content) for role, content in conversation
    ]

    response = await send_sampling_create_message(
        read_stream=read_stream,
        write_stream=write_stream,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=max_tokens,
        model_preferences=model_preferences,
        temperature=temperature,
        include_context=include_context,
        timeout=timeout,
    )

    return CreateMessageResult.model_validate(response)


# Client-side implementation helpers


class SamplingHandler:
    """
    Helper class for implementing client-side sampling support.

    Clients can use this class to handle sampling requests from servers.
    """

    def __init__(self, llm_provider: Any = None):
        """
        Initialize the sampling handler.

        Args:
            llm_provider: Optional LLM provider interface
        """
        self._llm_provider = llm_provider
        self._approval_handler = None
        self._model_selector = None

    def set_approval_handler(self, handler: Any) -> None:
        """
        Set the handler for user approval.

        Args:
            handler: Async function (messages, params) -> bool
        """
        self._approval_handler = handler

    def set_model_selector(self, selector: Any) -> None:
        """
        Set the model selection logic.

        Args:
            selector: Async function (preferences) -> model_name
        """
        self._model_selector = selector

    async def handle_create_message_request(
        self, params: Dict[str, Any], request_id: Any
    ) -> Dict[str, Any]:
        """
        Handle a sampling/createMessage request from a server.

        Args:
            params: Request parameters
            request_id: The request ID

        Returns:
            Response dict with result or error

        Raises:
            Exception: If sampling fails or is rejected
        """
        # Extract parameters
        messages = params.get("messages", [])
        max_tokens = params.get("maxTokens", 1000)
        model_prefs = params.get("modelPreferences")
        system_prompt = params.get("systemPrompt")
        temperature = params.get("temperature")
        stop_sequences = params.get("stopSequences")
        metadata = params.get("metadata")
        include_context = params.get("includeContext", "none")

        # Request user approval if handler is set
        if self._approval_handler:
            approved = await self._approval_handler(messages, params)
            if not approved:
                raise ValueError("User rejected the sampling request")

        # Select model
        model_name = "default-model"
        if self._model_selector and model_prefs:
            model_name = await self._model_selector(model_prefs)

        # Prepare context if requested
        context_messages: List[SamplingMessage] = []
        if include_context != "none":
            # This would gather context from MCP servers
            # Implementation depends on the client's architecture
            pass

        # Call LLM provider
        if not self._llm_provider:
            raise ValueError("No LLM provider configured")

        # Combine messages
        all_messages = context_messages + messages

        # Sample from LLM (implementation depends on provider)
        result = await self._llm_provider.create_message(
            messages=all_messages,
            max_tokens=max_tokens,
            system=system_prompt,
            temperature=temperature,
            stop_sequences=stop_sequences,
            metadata=metadata,
        )

        # Build response
        return {
            "role": result.role,
            "content": result.content.model_dump()
            if hasattr(result.content, "model_dump")
            else result.content,
            "model": model_name,
            "stopReason": result.stop_reason,
        }


def parse_sampling_message(data: Dict[str, Any]) -> SamplingMessage:
    """Parse a sampling message from a dictionary."""
    return SamplingMessage.model_validate(data)


def parse_create_message_result(data: Dict[str, Any]) -> CreateMessageResult:
    """Parse a create message result from a dictionary."""
    return CreateMessageResult.model_validate(data)


__all__ = [
    # Types
    "IncludeContext",
    "StopReason",
    "SamplingMessage",
    "ModelHint",
    "ModelPreferences",
    "CreateMessageResult",
    # Main function
    "send_sampling_create_message",
    # Helper functions
    "create_sampling_message",
    "create_model_preferences",
    "sample_text",
    "sample_conversation",
    # Handler class
    "SamplingHandler",
    # Parsing functions
    "parse_sampling_message",
    "parse_create_message_result",
]
