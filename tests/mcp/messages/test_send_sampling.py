#!/usr/bin/env python3
"""
Comprehensive tests for sampling/send_messages.py module.
"""

import pytest
import anyio
from unittest.mock import AsyncMock, patch

from chuk_mcp.protocol.messages.sampling.send_messages import (
    SamplingMessage,
    ModelHint,
    ModelPreferences,
    CreateMessageResult,
    send_sampling_create_message,
    create_sampling_message,
    create_model_preferences,
    sample_text,
    sample_conversation,
    SamplingHandler,
    parse_sampling_message,
    parse_create_message_result,
)
from chuk_mcp.protocol.types.content import create_text_content


class TestSamplingTypes:
    """Test sampling types."""

    def test_sampling_message(self):
        """Test SamplingMessage creation."""
        content = create_text_content("Hello, world!")
        msg = SamplingMessage(role="user", content=content)

        assert msg.role == "user"
        assert msg.content.type == "text"

    def test_model_hint(self):
        """Test ModelHint creation."""
        hint = ModelHint(name="claude-3-5-sonnet")

        assert hint.name == "claude-3-5-sonnet"

    def test_model_hint_optional(self):
        """Test ModelHint without name."""
        hint = ModelHint()

        assert hint.name is None

    def test_model_preferences_with_hints(self):
        """Test ModelPreferences with hints."""
        hints = [ModelHint(name="claude"), ModelHint(name="gpt")]
        prefs = ModelPreferences(
            hints=hints,
            costPriority=0.8,
            speedPriority=0.5,
            intelligencePriority=0.9,
        )

        assert len(prefs.hints) == 2
        assert prefs.costPriority == 0.8
        assert prefs.speedPriority == 0.5
        assert prefs.intelligencePriority == 0.9

    def test_model_preferences_optional_fields(self):
        """Test ModelPreferences with optional fields."""
        prefs = ModelPreferences()

        assert prefs.hints is None
        assert prefs.costPriority is None

    def test_create_message_result(self):
        """Test CreateMessageResult creation."""
        content = create_text_content("Response text")
        result = CreateMessageResult(
            role="assistant",
            content=content,
            model="claude-3-5-sonnet",
            stopReason="endTurn",
        )

        assert result.role == "assistant"
        assert result.model == "claude-3-5-sonnet"
        assert result.stopReason == "endTurn"

    def test_create_message_result_with_meta(self):
        """Test CreateMessageResult with metadata."""
        content = create_text_content("Response")
        result = CreateMessageResult(
            role="assistant",
            content=content,
            model="test-model",
            meta={"custom": "data"},
        )

        assert result.meta == {"custom": "data"}

    def test_create_message_result_optional_stop_reason(self):
        """Test CreateMessageResult without stopReason."""
        content = create_text_content("Response")
        result = CreateMessageResult(
            role="assistant", content=content, model="test-model"
        )

        assert result.stopReason is None


class TestSendSamplingCreateMessage:
    """Test send_sampling_create_message function."""

    @pytest.mark.asyncio
    async def test_send_sampling_basic(self):
        """Test basic sampling request."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Hello!"},
            "model": "test-model",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            msg = create_sampling_message("user", "Hello")
            result = await send_sampling_create_message(
                read_receive, write_send, messages=[msg], max_tokens=100
            )

        assert result["role"] == "assistant"
        assert result["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_send_sampling_with_model_preferences(self):
        """Test sampling with model preferences."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Response"},
            "model": "claude-3-5-sonnet",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            msg = create_sampling_message("user", "Test")
            prefs = create_model_preferences(
                hints=["claude"], intelligence_priority=1.0
            )
            result = await send_sampling_create_message(
                read_receive,
                write_send,
                messages=[msg],
                max_tokens=200,
                model_preferences=prefs,
            )

        assert result["model"] == "claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_send_sampling_with_all_params(self):
        """Test sampling with all optional parameters."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Complete response"},
            "model": "test-model",
            "stopReason": "maxTokens",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            msg = create_sampling_message("user", "Prompt")
            prefs = create_model_preferences(cost_priority=0.5)

            result = await send_sampling_create_message(
                read_receive,
                write_send,
                messages=[msg],
                max_tokens=500,
                model_preferences=prefs,
                system_prompt="You are a helpful assistant",
                include_context="allServers",
                temperature=0.7,
                stop_sequences=["STOP"],
                metadata={"session": "test"},
                timeout=30.0,
                retries=1,
            )

        assert result["stopReason"] == "maxTokens"

    @pytest.mark.asyncio
    async def test_send_sampling_with_dict_messages(self):
        """Test sampling with dict messages instead of objects."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "OK"},
            "model": "test",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            msg_dict = {
                "role": "user",
                "content": {"type": "text", "text": "Hello"},
            }
            result = await send_sampling_create_message(
                read_receive, write_send, messages=[msg_dict], max_tokens=100
            )

        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_send_sampling_with_dict_preferences(self):
        """Test sampling with dict model preferences."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Response"},
            "model": "fast-model",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            msg = create_sampling_message("user", "Quick question")
            prefs_dict = {"speedPriority": 1.0}

            result = await send_sampling_create_message(
                read_receive,
                write_send,
                messages=[msg],
                max_tokens=50,
                model_preferences=prefs_dict,
            )

        assert result["model"] == "fast-model"


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_sampling_message_with_string(self):
        """Test create_sampling_message with string content."""
        msg = create_sampling_message("user", "Hello, AI!")

        assert msg.role == "user"
        assert msg.content.type == "text"
        assert msg.content.text == "Hello, AI!"

    def test_create_sampling_message_with_content(self):
        """Test create_sampling_message with Content object."""
        content = create_text_content("Structured content")
        msg = create_sampling_message("assistant", content)

        assert msg.role == "assistant"
        assert msg.content.text == "Structured content"

    def test_create_model_preferences_all_params(self):
        """Test create_model_preferences with all parameters."""
        prefs = create_model_preferences(
            hints=["claude-3", "gpt-4"],
            cost_priority=0.3,
            speed_priority=0.6,
            intelligence_priority=0.9,
        )

        assert len(prefs.hints) == 2
        assert prefs.hints[0].name == "claude-3"
        assert prefs.costPriority == 0.3
        assert prefs.speedPriority == 0.6
        assert prefs.intelligencePriority == 0.9

    def test_create_model_preferences_minimal(self):
        """Test create_model_preferences with minimal params."""
        prefs = create_model_preferences()

        assert prefs.hints is None
        assert prefs.costPriority is None

    @pytest.mark.asyncio
    async def test_sample_text_basic(self):
        """Test sample_text helper."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Generated text"},
            "model": "test-model",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            result = await sample_text(
                read_receive, write_send, prompt="Generate something"
            )

        assert isinstance(result, CreateMessageResult)
        assert result.role == "assistant"
        assert result.model == "test-model"

    @pytest.mark.asyncio
    async def test_sample_text_with_model_hint(self):
        """Test sample_text with model hint."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Response"},
            "model": "claude-3-5-sonnet",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            result = await sample_text(
                read_receive,
                write_send,
                prompt="Test prompt",
                model_hint="claude",
                temperature=0.5,
                system_prompt="Be concise",
            )

        assert result.model == "claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_sample_conversation(self):
        """Test sample_conversation helper."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Conversation response"},
            "model": "chat-model",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            conversation = [
                ("user", "Hello"),
                ("assistant", "Hi there!"),
                ("user", "How are you?"),
            ]

            result = await sample_conversation(
                read_receive, write_send, conversation=conversation
            )

        assert isinstance(result, CreateMessageResult)
        assert result.role == "assistant"

    @pytest.mark.asyncio
    async def test_sample_conversation_with_preferences(self):
        """Test sample_conversation with model preferences."""
        read_send, read_receive = anyio.create_memory_object_stream(max_buffer_size=10)
        write_send, write_receive = anyio.create_memory_object_stream(
            max_buffer_size=10
        )

        response_data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Smart response"},
            "model": "intelligent-model",
        }

        with patch(
            "chuk_mcp.protocol.messages.sampling.send_messages.send_message",
            return_value=response_data,
        ):
            prefs = create_model_preferences(intelligence_priority=1.0)
            conversation = [("user", "Explain quantum physics")]

            result = await sample_conversation(
                read_receive,
                write_send,
                conversation=conversation,
                model_preferences=prefs,
                temperature=0.2,
                include_context="thisServer",
            )

        assert result.model == "intelligent-model"


class TestSamplingHandler:
    """Test SamplingHandler class."""

    def test_handler_initialization(self):
        """Test SamplingHandler initialization."""
        handler = SamplingHandler()

        assert handler._llm_provider is None
        assert handler._approval_handler is None
        assert handler._model_selector is None

    def test_handler_initialization_with_provider(self):
        """Test SamplingHandler with LLM provider."""
        mock_provider = AsyncMock()
        handler = SamplingHandler(llm_provider=mock_provider)

        assert handler._llm_provider == mock_provider

    def test_set_approval_handler(self):
        """Test setting approval handler."""
        handler = SamplingHandler()

        async def approve(messages, params):
            return True

        handler.set_approval_handler(approve)

        assert handler._approval_handler == approve

    def test_set_model_selector(self):
        """Test setting model selector."""
        handler = SamplingHandler()

        async def select_model(preferences):
            return "selected-model"

        handler.set_model_selector(select_model)

        assert handler._model_selector == select_model

    @pytest.mark.asyncio
    async def test_handle_create_message_request_basic(self):
        """Test handling create message request."""
        # Mock LLM provider
        mock_result = type(
            "Result",
            (),
            {
                "role": "assistant",
                "content": create_text_content("LLM response"),
                "stop_reason": "endTurn",
            },
        )()

        mock_provider = AsyncMock()
        mock_provider.create_message = AsyncMock(return_value=mock_result)

        handler = SamplingHandler(llm_provider=mock_provider)

        params = {
            "messages": [{"role": "user", "content": {"type": "text", "text": "Hi"}}],
            "maxTokens": 100,
        }

        result = await handler.handle_create_message_request(params, "req-1")

        assert result["role"] == "assistant"
        assert result["model"] == "default-model"
        assert result["stopReason"] == "endTurn"

    @pytest.mark.asyncio
    async def test_handle_create_message_request_with_approval(self):
        """Test request handling with user approval."""

        async def approve_handler(messages, params):
            return True

        mock_result = type(
            "Result",
            (),
            {
                "role": "assistant",
                "content": create_text_content("Approved response"),
                "stop_reason": "endTurn",
            },
        )()

        mock_provider = AsyncMock()
        mock_provider.create_message = AsyncMock(return_value=mock_result)

        handler = SamplingHandler(llm_provider=mock_provider)
        handler.set_approval_handler(approve_handler)

        params = {
            "messages": [{"role": "user", "content": {"type": "text", "text": "Test"}}],
            "maxTokens": 50,
        }

        result = await handler.handle_create_message_request(params, "req-2")

        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_handle_create_message_request_rejected(self):
        """Test request handling when user rejects."""

        async def reject_handler(messages, params):
            return False

        handler = SamplingHandler()
        handler.set_approval_handler(reject_handler)

        params = {
            "messages": [{"role": "user", "content": {"type": "text", "text": "Test"}}],
            "maxTokens": 50,
        }

        with pytest.raises(ValueError, match="User rejected"):
            await handler.handle_create_message_request(params, "req-3")

    @pytest.mark.asyncio
    async def test_handle_create_message_request_with_model_selector(self):
        """Test request handling with model selector."""

        async def select_model(preferences):
            return "custom-model"

        mock_result = type(
            "Result",
            (),
            {
                "role": "assistant",
                "content": create_text_content("Response"),
                "stop_reason": "endTurn",
            },
        )()

        mock_provider = AsyncMock()
        mock_provider.create_message = AsyncMock(return_value=mock_result)

        handler = SamplingHandler(llm_provider=mock_provider)
        handler.set_model_selector(select_model)

        params = {
            "messages": [{"role": "user", "content": {"type": "text", "text": "Hi"}}],
            "maxTokens": 100,
            "modelPreferences": {"costPriority": 1.0},
        }

        result = await handler.handle_create_message_request(params, "req-4")

        assert result["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_handle_create_message_request_no_provider(self):
        """Test request handling without LLM provider."""
        handler = SamplingHandler()

        params = {
            "messages": [{"role": "user", "content": {"type": "text", "text": "Hi"}}],
            "maxTokens": 100,
        }

        with pytest.raises(ValueError, match="No LLM provider"):
            await handler.handle_create_message_request(params, "req-5")


class TestParsingFunctions:
    """Test parsing functions."""

    def test_parse_sampling_message(self):
        """Test parse_sampling_message."""
        data = {
            "role": "user",
            "content": {"type": "text", "text": "Parse this"},
        }

        msg = parse_sampling_message(data)

        assert isinstance(msg, SamplingMessage)
        assert msg.role == "user"
        assert msg.content.text == "Parse this"

    def test_parse_create_message_result(self):
        """Test parse_create_message_result."""
        data = {
            "role": "assistant",
            "content": {"type": "text", "text": "Result"},
            "model": "parser-model",
            "stopReason": "endTurn",
        }

        result = parse_create_message_result(data)

        assert isinstance(result, CreateMessageResult)
        assert result.role == "assistant"
        assert result.model == "parser-model"
        assert result.stopReason == "endTurn"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
