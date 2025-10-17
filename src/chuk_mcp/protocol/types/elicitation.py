# chuk_mcp/protocol/types/elicitation.py
"""
Elicitation types and utilities for MCP.

NEW in 2025-06-18: Servers can now ask users for input mid-session
by sending an elicitation/create request with a message and a JSON schema.
"""

from typing import Dict, Any, Optional, Literal
from ..mcp_pydantic_base import McpPydanticBase, Field


class ElicitationRequest(McpPydanticBase):
    """
    Request for user input during an interaction (NEW in 2025-06-18).

    This allows servers to request additional information from users
    during tool execution or other operations.
    """

    method: Literal["elicitation/create"] = "elicitation/create"
    """The method name for elicitation requests."""

    params: "ElicitationParams"
    """Parameters for the elicitation request."""


class ElicitationParams(McpPydanticBase):
    """Parameters for an elicitation request."""

    message: str
    """Human-readable message explaining what input is needed."""

    schema_: Dict[str, Any] = Field(..., alias="schema")
    """JSON Schema defining the expected structure of the user's response."""

    title: Optional[str] = None
    """Optional title for the input request (for UI display)."""

    description: Optional[str] = None
    """Optional longer description of what input is needed."""

    model_config = {"extra": "allow", "populate_by_name": True}


class ElicitationResponse(McpPydanticBase):
    """Response from an elicitation request."""

    data: Dict[str, Any]
    """The user's response data, structured according to the request schema."""

    cancelled: Optional[bool] = None
    """Whether the user cancelled the input request."""

    model_config = {"extra": "allow"}


class ElicitationError(McpPydanticBase):
    """Error response for an elicitation request."""

    code: int
    """Error code."""

    message: str
    """Human-readable error message."""

    data: Optional[Dict[str, Any]] = None
    """Optional additional error data."""


# Helper functions for creating elicitation requests


def create_text_input_elicitation(
    message: str,
    field_name: str = "input",
    title: Optional[str] = None,
    required: bool = True,
) -> ElicitationParams:
    """
    Create an elicitation request for simple text input.

    Args:
        message: Message explaining what input is needed
        field_name: Name of the input field in the response
        title: Optional title for the input
        required: Whether the input is required
    """
    schema = {
        "type": "object",
        "properties": {field_name: {"type": "string", "description": message}},
    }

    if required:
        schema["required"] = [field_name]

    return ElicitationParams(message=message, schema_=schema, title=title)


def create_choice_elicitation(
    message: str,
    choices: list[str],
    field_name: str = "choice",
    title: Optional[str] = None,
) -> ElicitationParams:
    """
    Create an elicitation request for selecting from choices.

    Args:
        message: Message explaining what choice is needed
        choices: List of available choices
        field_name: Name of the choice field in the response
        title: Optional title for the choice
    """
    schema = {
        "type": "object",
        "properties": {
            field_name: {"type": "string", "enum": choices, "description": message}
        },
        "required": [field_name],
    }

    return ElicitationParams(message=message, schema_=schema, title=title)


def create_confirmation_elicitation(
    message: str, field_name: str = "confirmed", title: Optional[str] = None
) -> ElicitationParams:
    """
    Create an elicitation request for yes/no confirmation.

    Args:
        message: Message explaining what needs confirmation
        field_name: Name of the confirmation field in the response
        title: Optional title for the confirmation
    """
    schema = {
        "type": "object",
        "properties": {field_name: {"type": "boolean", "description": message}},
        "required": [field_name],
    }

    return ElicitationParams(message=message, schema_=schema, title=title)


def create_form_elicitation(
    message: str,
    fields: Dict[str, Dict[str, Any]],
    required_fields: Optional[list[str]] = None,
    title: Optional[str] = None,
) -> ElicitationParams:
    """
    Create an elicitation request for multiple form fields.

    Args:
        message: Message explaining what information is needed
        fields: Dictionary of field names to JSON Schema field definitions
        required_fields: List of required field names
        title: Optional title for the form
    """
    schema = {"type": "object", "properties": fields}

    if required_fields:
        schema["required"] = required_fields

    return ElicitationParams(message=message, schema_=schema, title=title)


# Server-side elicitation handler


class ElicitationHandler:
    """
    Handler for server-side elicitation requests.

    This allows MCP servers to request user input during operations.
    """

    def __init__(self, send_message_func) -> None:
        """
        Initialize the elicitation handler.

        Args:
            send_message_func: Function to send messages to the client
        """
        self.send_message_func = send_message_func
        self._pending_elicitations: Dict[str, Any] = {}

    async def request_user_input(
        self, params: ElicitationParams, timeout: Optional[float] = None
    ) -> ElicitationResponse:
        """
        Request input from the user.

        Args:
            params: Elicitation parameters
            timeout: Optional timeout for the request

        Returns:
            The user's response

        Raises:
            TimeoutError: If the request times out
            Exception: If the request fails
        """
        import uuid
        import asyncio

        request_id = str(uuid.uuid4())

        # Create the elicitation request
        request = {
            "jsonrpc": "2.0",
            "method": "elicitation/create",
            "id": request_id,
            "params": params.model_dump(exclude_none=True),
        }

        # Create a future to wait for the response
        response_future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
        self._pending_elicitations[request_id] = response_future

        try:
            # Send the request to the client
            await self.send_message_func(request)

            # Wait for the response
            if timeout:
                response = await asyncio.wait_for(response_future, timeout=timeout)
            else:
                response = await response_future

            return ElicitationResponse.model_validate(response)

        finally:
            # Clean up
            self._pending_elicitations.pop(request_id, None)

    async def handle_elicitation_response(self, message: Dict[str, Any]) -> None:
        """
        Handle an elicitation response from the client.

        Args:
            message: The JSON-RPC response message
        """
        message_id = message.get("id")
        if not message_id or message_id not in self._pending_elicitations:
            return

        future = self._pending_elicitations[message_id]

        if "error" in message:
            # Handle error response
            error = message["error"]
            future.set_exception(
                Exception(f"Elicitation error: {error.get('message', 'Unknown error')}")
            )
        elif "result" in message:
            # Handle success response
            future.set_result(message["result"])
        else:
            # Invalid response
            future.set_exception(Exception("Invalid elicitation response"))


# Client-side elicitation support


class ElicitationClient:
    """
    Client-side support for handling elicitation requests.

    This allows MCP clients to respond to server requests for user input.
    """

    def __init__(self, user_input_func):
        """
        Initialize the elicitation client.

        Args:
            user_input_func: Function to get input from the user
                            Should accept (message, schema, title) and return data dict
        """
        self.user_input_func = user_input_func

    async def handle_elicitation_request(
        self, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle an elicitation request from the server.

        Args:
            message: The JSON-RPC request message

        Returns:
            The response message to send back to the server
        """
        message_id = message.get("id")
        params = message.get("params", {})

        try:
            # Extract elicitation parameters
            user_message = params.get("message", "Input requested")
            schema = params.get("schema", {})
            title = params.get("title")

            # Get input from the user
            user_data = await self.user_input_func(user_message, schema, title)

            # Create success response
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {"data": user_data, "cancelled": False},
            }

        except Exception as e:
            # Create error response
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": -32603, "message": f"Elicitation error: {str(e)}"},
            }


# Example usage


async def example_user_input_function(
    message: str, schema: Dict[str, Any], title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Example user input function for demonstration.

    In a real implementation, this would show a UI dialog or prompt.
    """
    print(f"\n{'=' * 50}")
    print("USER INPUT REQUESTED")
    if title:
        print(f"Title: {title}")
    print(f"Message: {message}")
    print(f"Schema: {schema}")
    print(f"{'=' * 50}")

    # For demo purposes, return some mock data
    properties = schema.get("properties", {})
    result = {}

    for field_name, field_schema in properties.items():
        field_type = field_schema.get("type", "string")

        if field_type == "string":
            if "enum" in field_schema:
                result[field_name] = field_schema["enum"][0]  # First choice
            else:
                result[field_name] = f"user_input_for_{field_name}"
        elif field_type == "boolean":
            result[field_name] = True
        elif field_type == "integer":
            result[field_name] = 42
        elif field_type == "number":
            result[field_name] = 3.14

    return result


async def example_elicitation_workflow():
    """Example of how elicitation might be used in a tool."""

    # This would be part of a tool implementation
    async def mock_send_message(message):
        print(f"Would send: {message}")

    _handler = ElicitationHandler(mock_send_message)

    # Request user confirmation before proceeding
    _confirmation = create_confirmation_elicitation(
        "Do you want to proceed with deleting the file?", title="Confirm File Deletion"
    )

    try:
        # In a real implementation, this would wait for user response
        print("Would request user confirmation here...")

        # Mock response
        response_data = {"confirmed": True}

        if response_data.get("confirmed"):
            return "File deleted successfully"
        else:
            return "File deletion cancelled by user"

    except Exception as e:
        return f"Could not get user confirmation: {e}"


__all__ = [
    # Core types
    "ElicitationRequest",
    "ElicitationParams",
    "ElicitationResponse",
    "ElicitationError",
    # Helper functions
    "create_text_input_elicitation",
    "create_choice_elicitation",
    "create_confirmation_elicitation",
    "create_form_elicitation",
    # Handlers
    "ElicitationHandler",
    "ElicitationClient",
    # Examples
    "example_user_input_function",
    "example_elicitation_workflow",
]
