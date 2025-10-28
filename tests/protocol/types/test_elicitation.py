"""Tests for elicitation types and utilities."""

import pytest
from chuk_mcp.protocol.types.elicitation import (
    ElicitationRequest,
    ElicitationParams,
    ElicitationResponse,
    ElicitationError,
    ElicitationHandler,
    ElicitationClient,
    create_text_input_elicitation,
    create_choice_elicitation,
    create_confirmation_elicitation,
    create_form_elicitation,
    example_user_input_function,
    example_elicitation_workflow,
)


class TestElicitationTypes:
    """Test elicitation type definitions."""

    def test_elicitation_request(self):
        """Test ElicitationRequest creation."""
        params = ElicitationParams(
            message="Enter your name", schema_={"type": "object", "properties": {}}
        )
        request = ElicitationRequest(method="elicitation/create", params=params)

        assert request.method == "elicitation/create"
        assert request.params == params

    def test_elicitation_params(self):
        """Test ElicitationParams creation."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        params = ElicitationParams(
            message="Enter your name",
            schema_=schema,
            title="User Information",
            description="Please provide your name",
        )

        assert params.message == "Enter your name"
        assert params.schema_ == schema
        assert params.title == "User Information"
        assert params.description == "Please provide your name"

    def test_elicitation_params_alias(self):
        """Test ElicitationParams schema alias."""
        schema = {"type": "object"}
        # Test using alias 'schema'
        params = ElicitationParams(message="test", schema=schema)
        assert params.schema_ == schema

    def test_elicitation_response(self):
        """Test ElicitationResponse creation."""
        response = ElicitationResponse(data={"name": "John"}, cancelled=False)

        assert response.data == {"name": "John"}
        assert response.cancelled is False

    def test_elicitation_response_cancelled(self):
        """Test ElicitationResponse with cancellation."""
        response = ElicitationResponse(data={}, cancelled=True)

        assert response.cancelled is True

    def test_elicitation_error(self):
        """Test ElicitationError creation."""
        error = ElicitationError(
            code=-32603, message="Internal error", data={"details": "timeout"}
        )

        assert error.code == -32603
        assert error.message == "Internal error"
        assert error.data == {"details": "timeout"}


class TestElicitationHelpers:
    """Test elicitation helper functions."""

    def test_create_text_input_elicitation(self):
        """Test creating text input elicitation."""
        params = create_text_input_elicitation(
            message="Enter your email", field_name="email", title="Email Input"
        )

        assert params.message == "Enter your email"
        assert params.title == "Email Input"
        assert params.schema_["type"] == "object"
        assert "email" in params.schema_["properties"]
        assert params.schema_["required"] == ["email"]

    def test_create_text_input_not_required(self):
        """Test creating optional text input."""
        params = create_text_input_elicitation(
            message="Enter comment", field_name="comment", required=False
        )

        assert "required" not in params.schema_

    def test_create_choice_elicitation(self):
        """Test creating choice elicitation."""
        choices = ["red", "green", "blue"]
        params = create_choice_elicitation(
            message="Choose a color", choices=choices, field_name="color"
        )

        assert params.message == "Choose a color"
        assert params.schema_["properties"]["color"]["enum"] == choices
        assert params.schema_["required"] == ["color"]

    def test_create_confirmation_elicitation(self):
        """Test creating confirmation elicitation."""
        params = create_confirmation_elicitation(
            message="Are you sure?", field_name="confirmed", title="Confirm Action"
        )

        assert params.message == "Are you sure?"
        assert params.title == "Confirm Action"
        assert params.schema_["properties"]["confirmed"]["type"] == "boolean"
        assert params.schema_["required"] == ["confirmed"]

    def test_create_form_elicitation(self):
        """Test creating form elicitation."""
        fields = {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
        }
        params = create_form_elicitation(
            message="Fill in your details",
            fields=fields,
            required_fields=["name", "email"],
            title="User Form",
        )

        assert params.message == "Fill in your details"
        assert params.title == "User Form"
        assert params.schema_["properties"] == fields
        assert params.schema_["required"] == ["name", "email"]

    def test_create_form_elicitation_no_required(self):
        """Test creating form without required fields."""
        fields = {"comment": {"type": "string"}}
        params = create_form_elicitation(message="Optional comment", fields=fields)

        assert "required" not in params.schema_


class TestElicitationHandler:
    """Test ElicitationHandler for server-side use."""

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization."""
        messages = []

        async def mock_send(msg):
            messages.append(msg)

        handler = ElicitationHandler(mock_send)
        assert handler.send_message_func == mock_send
        assert handler._pending_elicitations == {}

    @pytest.mark.asyncio
    async def test_handler_request_user_input_timeout(self):
        """Test handler request with timeout."""
        messages = []

        async def mock_send(msg):
            messages.append(msg)
            # Don't send response - let it timeout

        handler = ElicitationHandler(mock_send)
        params = create_text_input_elicitation("Enter name")

        with pytest.raises(Exception):  # TimeoutError or asyncio.TimeoutError
            await handler.request_user_input(params, timeout=0.1)

        # Verify request was sent
        assert len(messages) == 1
        assert messages[0]["method"] == "elicitation/create"

    @pytest.mark.asyncio
    async def test_handler_handle_success_response(self):
        """Test handling success response."""
        import asyncio

        messages = []

        async def mock_send(msg):
            messages.append(msg)
            # Simulate response after a short delay
            asyncio.create_task(
                handler.handle_elicitation_response(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "result": {"data": {"name": "John"}, "cancelled": False},
                    }
                )
            )

        handler = ElicitationHandler(mock_send)
        params = create_text_input_elicitation("Enter name")

        response = await handler.request_user_input(params, timeout=1.0)

        assert response.data == {"name": "John"}
        assert response.cancelled is False

    @pytest.mark.asyncio
    async def test_handler_handle_error_response(self):
        """Test handling error response."""
        import asyncio

        messages = []

        async def mock_send(msg):
            messages.append(msg)
            # Simulate error response
            asyncio.create_task(
                handler.handle_elicitation_response(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "error": {"code": -32603, "message": "User cancelled"},
                    }
                )
            )

        handler = ElicitationHandler(mock_send)
        params = create_text_input_elicitation("Enter name")

        with pytest.raises(Exception, match="User cancelled"):
            await handler.request_user_input(params, timeout=1.0)

    @pytest.mark.asyncio
    async def test_handler_handle_invalid_response(self):
        """Test handling invalid response."""
        import asyncio

        messages = []

        async def mock_send(msg):
            messages.append(msg)
            # Simulate invalid response (no result or error)
            asyncio.create_task(
                handler.handle_elicitation_response({"jsonrpc": "2.0", "id": msg["id"]})
            )

        handler = ElicitationHandler(mock_send)
        params = create_text_input_elicitation("Enter name")

        with pytest.raises(Exception, match="Invalid elicitation response"):
            await handler.request_user_input(params, timeout=1.0)

    @pytest.mark.asyncio
    async def test_handler_ignore_unknown_response(self):
        """Test that handler ignores responses for unknown IDs."""
        messages = []

        async def mock_send(msg):
            messages.append(msg)

        handler = ElicitationHandler(mock_send)

        # Handle response with unknown ID - should not raise
        await handler.handle_elicitation_response(
            {"jsonrpc": "2.0", "id": "unknown-id", "result": {}}
        )

        # Handle response with no ID - should not raise
        await handler.handle_elicitation_response({"jsonrpc": "2.0", "result": {}})


class TestElicitationClient:
    """Test ElicitationClient for client-side use."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""

        async def mock_user_input(message, schema, title):
            return {"name": "John"}

        client = ElicitationClient(mock_user_input)
        assert client.user_input_func == mock_user_input

    @pytest.mark.asyncio
    async def test_client_handle_request_success(self):
        """Test client handling successful request."""

        async def mock_user_input(message, schema, title):
            return {"name": "John"}

        client = ElicitationClient(mock_user_input)

        request = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "elicitation/create",
            "params": {
                "message": "Enter your name",
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "title": "Name Input",
            },
        }

        response = await client.handle_elicitation_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req-1"
        assert response["result"]["data"] == {"name": "John"}
        assert response["result"]["cancelled"] is False

    @pytest.mark.asyncio
    async def test_client_handle_request_error(self):
        """Test client handling request with error."""

        async def mock_user_input(message, schema, title):
            raise ValueError("User input failed")

        client = ElicitationClient(mock_user_input)

        request = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "params": {"message": "Enter name", "schema": {}},
        }

        response = await client.handle_elicitation_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req-1"
        assert "error" in response
        assert "User input failed" in response["error"]["message"]


class TestExampleFunctions:
    """Test example/utility functions."""

    @pytest.mark.asyncio
    async def test_example_user_input_function_string(self):
        """Test example user input function with string field."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }

        result = await example_user_input_function("Enter name", schema)
        assert "name" in result
        assert result["name"] == "user_input_for_name"

    @pytest.mark.asyncio
    async def test_example_user_input_function_enum(self):
        """Test example user input function with enum field."""
        schema = {
            "type": "object",
            "properties": {"color": {"type": "string", "enum": ["red", "blue"]}},
        }

        result = await example_user_input_function("Choose color", schema)
        assert result["color"] == "red"

    @pytest.mark.asyncio
    async def test_example_user_input_function_boolean(self):
        """Test example user input function with boolean field."""
        schema = {
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
        }

        result = await example_user_input_function("Confirm", schema)
        assert result["confirmed"] is True

    @pytest.mark.asyncio
    async def test_example_user_input_function_integer(self):
        """Test example user input function with integer field."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
        }

        result = await example_user_input_function("Enter age", schema)
        assert result["age"] == 42

    @pytest.mark.asyncio
    async def test_example_user_input_function_number(self):
        """Test example user input function with number field."""
        schema = {
            "type": "object",
            "properties": {"price": {"type": "number"}},
        }

        result = await example_user_input_function("Enter price", schema)
        assert result["price"] == 3.14

    @pytest.mark.asyncio
    async def test_example_user_input_function_with_title(self):
        """Test example user input function with title."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = await example_user_input_function("Enter name", schema, title="Name")
        assert "name" in result

    @pytest.mark.asyncio
    async def test_example_elicitation_workflow(self):
        """Test example elicitation workflow."""
        result = await example_elicitation_workflow()
        assert "File deleted successfully" in result or "cancelled" in result
