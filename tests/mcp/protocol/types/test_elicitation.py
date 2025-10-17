#!/usr/bin/env python3
"""
Tests for elicitation types and helper functions.
"""

import pytest
from chuk_mcp.protocol.types.elicitation import (
    ElicitationParams,
    ElicitationResponse,
    ElicitationError,
    create_text_input_elicitation,
    create_choice_elicitation,
    create_confirmation_elicitation,
    create_form_elicitation,
    ElicitationHandler,
    ElicitationClient,
)


class TestElicitationTypes:
    """Test basic elicitation types."""

    def test_elicitation_params(self):
        """Test ElicitationParams creation."""
        params = ElicitationParams(
            message="Enter your name",
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
            title="Name Input",
            description="Please provide your full name",
        )

        assert params.message == "Enter your name"
        assert params.schema_ == {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        assert params.title == "Name Input"
        assert params.description == "Please provide your full name"

    def test_elicitation_response(self):
        """Test ElicitationResponse creation."""
        response = ElicitationResponse(data={"username": "test_user"}, cancelled=False)

        assert response.data == {"username": "test_user"}
        assert response.cancelled is False

    def test_elicitation_response_cancelled(self):
        """Test cancelled ElicitationResponse."""
        response = ElicitationResponse(data={}, cancelled=True)

        assert response.data == {}
        assert response.cancelled is True

    def test_elicitation_error(self):
        """Test ElicitationError creation."""
        error = ElicitationError(
            code=-32001, message="User cancelled", data={"reason": "timeout"}
        )

        assert error.code == -32001
        assert error.message == "User cancelled"
        assert error.data == {"reason": "timeout"}


class TestElicitationHelpers:
    """Test elicitation helper functions."""

    def test_create_text_input_elicitation(self):
        """Test creating text input elicitation."""
        params = create_text_input_elicitation(
            message="Enter username",
            field_name="username",
            title="Username",
            required=True,
        )

        assert params.message == "Enter username"
        assert params.title == "Username"
        assert params.schema_["type"] == "object"
        assert "username" in params.schema_["properties"]
        assert params.schema_["properties"]["username"]["type"] == "string"
        assert params.schema_["required"] == ["username"]

    def test_create_text_input_elicitation_optional(self):
        """Test creating optional text input elicitation."""
        params = create_text_input_elicitation(
            message="Enter optional comment", field_name="comment", required=False
        )

        assert params.message == "Enter optional comment"
        assert "required" not in params.schema_

    def test_create_choice_elicitation(self):
        """Test creating choice elicitation."""
        choices = ["option1", "option2", "option3"]
        params = create_choice_elicitation(
            message="Select an option",
            choices=choices,
            field_name="selection",
            title="Choose One",
        )

        assert params.message == "Select an option"
        assert params.title == "Choose One"
        assert params.schema_["properties"]["selection"]["enum"] == choices
        assert params.schema_["required"] == ["selection"]

    def test_create_confirmation_elicitation(self):
        """Test creating confirmation elicitation."""
        params = create_confirmation_elicitation(
            message="Confirm deletion", field_name="confirmed", title="Confirm"
        )

        assert params.message == "Confirm deletion"
        assert params.title == "Confirm"
        assert params.schema_["properties"]["confirmed"]["type"] == "boolean"
        assert params.schema_["required"] == ["confirmed"]

    def test_create_form_elicitation(self):
        """Test creating form elicitation."""
        fields = {
            "name": {"type": "string", "description": "Your name"},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer", "minimum": 0},
        }
        required_fields = ["name", "email"]

        params = create_form_elicitation(
            message="Complete the form",
            fields=fields,
            required_fields=required_fields,
            title="User Information",
        )

        assert params.message == "Complete the form"
        assert params.title == "User Information"
        assert params.schema_["properties"] == fields
        assert params.schema_["required"] == required_fields

    def test_create_form_elicitation_no_required(self):
        """Test creating form elicitation without required fields."""
        fields = {"comment": {"type": "string"}}

        params = create_form_elicitation(
            message="Optional feedback", fields=fields, required_fields=None
        )

        assert "required" not in params.schema_


class TestElicitationHandler:
    """Test ElicitationHandler class."""

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization."""

        async def mock_send_message(message):
            return {"result": "sent"}

        handler = ElicitationHandler(mock_send_message)
        assert handler.send_message_func == mock_send_message
        assert handler._pending_elicitations == {}

    @pytest.mark.asyncio
    async def test_handler_request_user_input(self):
        """Test requesting user input."""
        import asyncio

        responses = []

        async def mock_send_message(message):
            responses.append(message)
            # Simulate async response by setting the future
            request_id = message["id"]
            # Schedule the response to be handled
            asyncio.create_task(
                handler.handle_elicitation_response(
                    {"id": request_id, "result": {"data": {"username": "testuser"}}}
                )
            )

        handler = ElicitationHandler(mock_send_message)
        params = create_text_input_elicitation("Enter username", "username")

        # Request user input with timeout
        response = await handler.request_user_input(params, timeout=1.0)

        # Verify response
        assert response.data == {"username": "testuser"}
        assert len(responses) == 1
        assert responses[0]["method"] == "elicitation/create"

    @pytest.mark.asyncio
    async def test_handler_request_with_timeout(self):
        """Test requesting user input with timeout."""
        import asyncio

        async def mock_send_message(message):
            request_id = message["id"]
            # Small delay then respond
            await asyncio.sleep(0.05)
            asyncio.create_task(
                handler.handle_elicitation_response(
                    {"id": request_id, "result": {"data": {"choice": "yes"}}}
                )
            )

        handler = ElicitationHandler(mock_send_message)
        params = create_confirmation_elicitation("Confirm?", "choice")

        # Request with longer timeout should succeed
        response = await handler.request_user_input(params, timeout=1.0)
        assert response.data == {"choice": "yes"}

    @pytest.mark.asyncio
    async def test_handler_request_timeout_error(self):
        """Test timeout error handling."""
        import asyncio

        async def mock_send_message(message):
            # Never respond - just wait
            await asyncio.sleep(10.0)

        handler = ElicitationHandler(mock_send_message)
        params = create_text_input_elicitation("Enter data", "data")

        # Request with short timeout should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await handler.request_user_input(params, timeout=0.1)

    @pytest.mark.asyncio
    async def test_handler_request_without_timeout(self):
        """Test requesting user input without timeout."""
        import asyncio

        async def mock_send_message(message):
            request_id = message["id"]
            asyncio.create_task(
                handler.handle_elicitation_response(
                    {"id": request_id, "result": {"data": {"field": "value"}}}
                )
            )

        handler = ElicitationHandler(mock_send_message)
        params = create_text_input_elicitation("Enter data", "field")

        # Request without timeout (timeout=None)
        response = await handler.request_user_input(params, timeout=None)

        assert response.data == {"field": "value"}

    @pytest.mark.asyncio
    async def test_handler_response_unknown_id(self):
        """Test handling response with unknown ID (should be ignored)."""
        handler = ElicitationHandler(lambda m: None)

        # Response for non-existent request should be ignored
        await handler.handle_elicitation_response(
            {"id": "unknown-id", "result": {"data": {}}}
        )

    @pytest.mark.asyncio
    async def test_handler_response_no_id(self):
        """Test handling response with no ID (should be ignored)."""
        handler = ElicitationHandler(lambda m: None)

        # Response with no ID should be ignored
        await handler.handle_elicitation_response({"result": {"data": {}}})

    @pytest.mark.asyncio
    async def test_handler_response_with_error(self):
        """Test handling error response."""
        import asyncio

        async def mock_send_message(message):
            request_id = message["id"]
            await asyncio.sleep(0.01)
            await handler.handle_elicitation_response(
                {
                    "id": request_id,
                    "error": {"code": -32001, "message": "User cancelled"},
                }
            )

        handler = ElicitationHandler(mock_send_message)
        params = create_text_input_elicitation("Enter data", "field")

        # Should raise exception due to error response
        with pytest.raises(Exception, match="Elicitation error"):
            await handler.request_user_input(params, timeout=1.0)

    @pytest.mark.asyncio
    async def test_handler_response_invalid(self):
        """Test handling invalid response (no result or error)."""
        import asyncio

        async def mock_send_message(message):
            request_id = message["id"]
            await asyncio.sleep(0.01)
            await handler.handle_elicitation_response({"id": request_id})

        handler = ElicitationHandler(mock_send_message)
        params = create_text_input_elicitation("Enter data", "field")

        # Should raise exception due to invalid response
        with pytest.raises(Exception, match="Invalid elicitation response"):
            await handler.request_user_input(params, timeout=1.0)


class TestElicitationClient:
    """Test ElicitationClient class."""

    def test_client_initialization(self):
        """Test ElicitationClient initialization."""

        async def mock_input_func(message, schema, title):
            return {"test": "data"}

        client = ElicitationClient(mock_input_func)

        assert client.user_input_func == mock_input_func

    @pytest.mark.asyncio
    async def test_client_handle_request_success(self):
        """Test client handling elicitation request successfully."""

        async def mock_input_func(message, schema, title):
            assert message == "Enter your name"
            assert title == "Name Input"
            return {"name": "John Doe"}

        client = ElicitationClient(mock_input_func)

        request = {
            "id": "req-123",
            "params": {
                "message": "Enter your name",
                "schema": {"properties": {"name": {"type": "string"}}},
                "title": "Name Input",
            },
        }

        response = await client.handle_elicitation_request(request)

        assert response["id"] == "req-123"
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["data"] == {"name": "John Doe"}
        assert response["result"]["cancelled"] is False

    @pytest.mark.asyncio
    async def test_client_handle_request_error(self):
        """Test client handling elicitation request with error."""

        async def failing_input_func(message, schema, title):
            raise ValueError("User cancelled")

        client = ElicitationClient(failing_input_func)

        request = {
            "id": "req-456",
            "params": {"message": "Enter data"},
        }

        response = await client.handle_elicitation_request(request)

        assert response["id"] == "req-456"
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "User cancelled" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_client_handle_request_default_params(self):
        """Test client handling request with default parameters."""

        async def mock_input_func(message, schema, title):
            # Check defaults
            assert message == "Input requested"
            assert schema == {}
            assert title is None
            return {"default": "data"}

        client = ElicitationClient(mock_input_func)

        # Request with no params
        request = {"id": "req-789", "params": {}}

        response = await client.handle_elicitation_request(request)

        assert response["result"]["data"] == {"default": "data"}


class TestExampleFunctions:
    """Test example helper functions."""

    @pytest.mark.asyncio
    async def test_example_user_input_function_string(self):
        """Test example_user_input_function with string field."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"username": {"type": "string"}}}

        result = await example_user_input_function("Enter username", schema)

        assert "username" in result
        assert result["username"] == "user_input_for_username"

    @pytest.mark.asyncio
    async def test_example_user_input_function_enum(self):
        """Test example_user_input_function with enum field."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"choice": {"type": "string", "enum": ["a", "b", "c"]}}}

        result = await example_user_input_function("Select option", schema)

        assert result["choice"] == "a"  # First enum value

    @pytest.mark.asyncio
    async def test_example_user_input_function_boolean(self):
        """Test example_user_input_function with boolean field."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"confirmed": {"type": "boolean"}}}

        result = await example_user_input_function("Confirm", schema)

        assert result["confirmed"] is True

    @pytest.mark.asyncio
    async def test_example_user_input_function_integer(self):
        """Test example_user_input_function with integer field."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"count": {"type": "integer"}}}

        result = await example_user_input_function("Enter count", schema)

        assert result["count"] == 42

    @pytest.mark.asyncio
    async def test_example_user_input_function_number(self):
        """Test example_user_input_function with number field."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"amount": {"type": "number"}}}

        result = await example_user_input_function("Enter amount", schema)

        assert result["amount"] == 3.14

    @pytest.mark.asyncio
    async def test_example_user_input_function_with_title(self, capsys):
        """Test example_user_input_function with title."""
        from chuk_mcp.protocol.types.elicitation import example_user_input_function

        schema = {"properties": {"field": {"type": "string"}}}

        await example_user_input_function("Message", schema, title="Test Title")

        captured = capsys.readouterr()
        assert "Test Title" in captured.out

    @pytest.mark.asyncio
    async def test_example_elicitation_workflow_confirmed(self, capsys):
        """Test example_elicitation_workflow with confirmation."""
        from chuk_mcp.protocol.types.elicitation import example_elicitation_workflow

        result = await example_elicitation_workflow()

        assert "deleted successfully" in result.lower()
        captured = capsys.readouterr()
        assert "Would send:" in captured.out or "Would request" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
