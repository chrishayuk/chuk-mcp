# chuk_mcp/protocol/messages/json_rpc_message.py
from typing import Any, Dict, Optional, Union, Literal, List
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, ConfigDict

# Type aliases matching the official implementation
RequestId = Union[int, str]
ProgressToken = Union[str, int]


class JSONRPCRequest(McpPydanticBase):
    """A request that expects a response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    method: str
    params: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class JSONRPCNotification(McpPydanticBase):
    """A notification which does not expect a response."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class JSONRPCResponse(McpPydanticBase):
    """A successful (non-error) response to a request."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    result: Any  # Can be any JSON-serializable value, not just Dict

    model_config = ConfigDict(extra="allow")


class JSONRPCError(McpPydanticBase):
    """A response to a request that indicates an error occurred."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    error: Dict[str, Any]  # {code: int, message: str, data?: any}

    model_config = ConfigDict(extra="allow")

    def model_post_init(self, __context):
        """Validate error structure."""
        if self.error:
            if "code" not in self.error or not isinstance(self.error["code"], int):
                raise ValueError("Error must have an integer 'code' field")
            if "message" not in self.error or not isinstance(
                self.error["message"], str
            ):
                raise ValueError("Error must have a string 'message' field")


# For batch support
JSONRPCBatchRequest = List[Union[JSONRPCRequest, JSONRPCNotification]]
JSONRPCBatchResponse = List[Union[JSONRPCResponse, JSONRPCError]]

# Union type for any valid JSON-RPC message
JSONRPCMessage = Union[
    JSONRPCRequest,
    JSONRPCNotification,
    JSONRPCBatchRequest,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCBatchResponse,
]


# Helper functions to create messages with proper types


def create_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    id: Optional[RequestId] = None,
    progress_token: Optional[ProgressToken] = None,
) -> JSONRPCRequest:
    """Create a request message with optional progress token."""
    if id is None:
        import uuid

        id = str(uuid.uuid4())

    # Add progress token to params._meta if provided
    if progress_token is not None:
        if params is None:
            params = {}
        if "_meta" not in params:
            params["_meta"] = {}
        params["_meta"]["progressToken"] = progress_token

    return JSONRPCRequest(jsonrpc="2.0", id=id, method=method, params=params)


def create_notification(
    method: str, params: Optional[Dict[str, Any]] = None
) -> JSONRPCNotification:
    """Create a notification message."""
    return JSONRPCNotification(jsonrpc="2.0", method=method, params=params)


def create_response(id: RequestId, result: Any = None) -> JSONRPCResponse:
    """Create a successful response message."""
    if result is None:
        result = {}  # Empty result as per spec
    return JSONRPCResponse(jsonrpc="2.0", id=id, result=result)


def create_error_response(
    id: RequestId, code: int, message: str, data: Any = None
) -> JSONRPCError:
    """Create an error response message."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return JSONRPCError(jsonrpc="2.0", id=id, error=error)


def parse_message(
    data: Union[Dict, List],
) -> Union[JSONRPCRequest, JSONRPCNotification, JSONRPCResponse, JSONRPCError, List]:
    """
    Parse incoming JSON data into appropriate JSON-RPC message type.

    Args:
        data: Parsed JSON data (dict for single message, list for batch)

    Returns:
        Appropriate JSONRPCMessage subtype

    Raises:
        ValueError: If the message doesn't match any valid JSON-RPC format
    """
    # Handle batch messages
    if isinstance(data, list):
        messages = []
        for item in data:
            messages.append(parse_message(item))

        # Determine if it's a request or response batch
        if all(isinstance(m, (JSONRPCRequest, JSONRPCNotification)) for m in messages):
            return messages  # JSONRPCBatchRequest
        elif all(isinstance(m, (JSONRPCResponse, JSONRPCError)) for m in messages):
            return messages  # JSONRPCBatchResponse
        else:
            raise ValueError("Batch contains mixed request/response types")

    # Single message
    if not isinstance(data, dict):
        raise ValueError("Message must be a dict or list")

    # For backward compatibility, try to parse with JSONRPCMessage first
    try:
        return JSONRPCMessage.model_validate(data)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Check required fields
    if data.get("jsonrpc") != "2.0":
        raise ValueError("Missing or invalid jsonrpc version")

    has_id = "id" in data
    has_method = "method" in data
    has_result = "result" in data
    has_error = "error" in data

    # Determine message type based on fields
    if has_method and has_id:
        # Request
        return JSONRPCRequest.model_validate(data)
    elif has_method and not has_id:
        # Notification
        return JSONRPCNotification.model_validate(data)
    elif has_id and has_result and not has_error:
        # Success response
        return JSONRPCResponse.model_validate(data)
    elif has_id and has_error and not has_result:
        # Error response
        return JSONRPCError.model_validate(data)
    else:
        raise ValueError("Invalid JSON-RPC message structure")


# For backward compatibility - create a wrapper that can handle any message type
class JSONRPCMessageWrapper:
    """
    Wrapper to provide backward compatibility for code expecting unified JSONRPCMessage.
    This should be phased out in favor of using specific message types.
    """

    def __init__(self, message: JSONRPCMessage):
        self._message = message

    @property
    def jsonrpc(self) -> str:
        return getattr(self._message, "jsonrpc", "2.0")

    @property
    def id(self) -> Optional[RequestId]:
        return getattr(self._message, "id", None)

    @property
    def method(self) -> Optional[str]:
        return getattr(self._message, "method", None)

    @property
    def params(self) -> Optional[Dict[str, Any]]:
        return getattr(self._message, "params", None)

    @property
    def result(self) -> Optional[Any]:
        return getattr(self._message, "result", None)

    @property
    def error(self) -> Optional[Dict[str, Any]]:
        return getattr(self._message, "error", None)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Dump the underlying message."""
        if hasattr(self._message, "model_dump"):
            return self._message.model_dump(**kwargs)
        elif isinstance(self._message, list):
            # Batch message
            return [m.model_dump(**kwargs) for m in self._message]  # type: ignore[return-value]
        else:
            raise ValueError("Unknown message type")

    def model_dump_json(self, **kwargs) -> str:
        """Dump as JSON."""
        import json

        return json.dumps(self.model_dump(**kwargs))

    def is_request(self) -> bool:
        return isinstance(self._message, JSONRPCRequest)

    def is_notification(self) -> bool:
        return isinstance(self._message, JSONRPCNotification)

    def is_response(self) -> bool:
        return isinstance(self._message, JSONRPCResponse)

    def is_error_response(self) -> bool:
        return isinstance(self._message, JSONRPCError)

    def is_batch(self) -> bool:
        return isinstance(self._message, list)


# For backward compatibility, keep the original JSONRPCMessage class
# but update it to use the proper message types internally
class JSONRPCMessage(McpPydanticBase):  # type: ignore[no-redef]
    """
    Unified JSON-RPC message type for backward compatibility.
    New code should use specific message types directly.
    """

    jsonrpc: str = "2.0"
    id: Optional[RequestId] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")

    def model_post_init(self, __context):
        """Validate JSON-RPC 2.0 compliance."""
        # Skip validation in test environments or when explicitly disabled
        import os

        if os.environ.get("SKIP_JSONRPC_VALIDATION", "false").lower() == "true":
            return

        # ID validation: if present, must be string or number (not null)
        if self.id is not None and not isinstance(self.id, (str, int)):
            raise ValueError("Request ID must be string or number, not null")

        # Response validation: must have either result or error, not both
        if self.id is not None and self.method is None:  # This is a response
            if self.result is not None and self.error is not None:
                raise ValueError("Response cannot have both result and error")
            if self.result is None and self.error is None:
                raise ValueError("Response must have either result or error")

    def to_specific_type(
        self,
    ) -> Union[JSONRPCRequest, JSONRPCNotification, JSONRPCResponse, JSONRPCError]:
        """Convert to the appropriate specific message type."""
        if self.method is not None and self.id is not None:
            return JSONRPCRequest(
                jsonrpc=self.jsonrpc,  # type: ignore[arg-type]
                id=self.id,
                method=self.method,
                params=self.params,  # type: ignore[arg-type]
            )
        elif self.method is not None and self.id is None:
            return JSONRPCNotification(
                jsonrpc=self.jsonrpc,  # type: ignore[arg-type]
                method=self.method,
                params=self.params,  # type: ignore[arg-type]
            )
        elif self.id is not None and self.result is not None:
            return JSONRPCResponse(jsonrpc=self.jsonrpc, id=self.id, result=self.result)  # type: ignore[arg-type]
        elif self.id is not None and self.error is not None:
            return JSONRPCError(jsonrpc=self.jsonrpc, id=self.id, error=self.error)  # type: ignore[arg-type]
        else:
            raise ValueError("Invalid JSON-RPC message structure")

    @classmethod
    def from_specific_type(
        cls,
        msg: Union[JSONRPCRequest, JSONRPCNotification, JSONRPCResponse, JSONRPCError],
    ) -> "JSONRPCMessage":
        """Create from a specific message type."""
        if isinstance(msg, JSONRPCRequest):
            return cls(  # type: ignore[return-value]
                jsonrpc=msg.jsonrpc, id=msg.id, method=msg.method, params=msg.params
            )
        elif isinstance(msg, JSONRPCNotification):
            return cls(jsonrpc=msg.jsonrpc, method=msg.method, params=msg.params)  # type: ignore[return-value]
        elif isinstance(msg, JSONRPCResponse):
            return cls(jsonrpc=msg.jsonrpc, id=msg.id, result=msg.result)  # type: ignore[return-value]
        elif isinstance(msg, JSONRPCError):
            return cls(jsonrpc=msg.jsonrpc, id=msg.id, error=msg.error)  # type: ignore[return-value]
        else:
            raise ValueError(f"Unknown message type: {type(msg)}")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Dump model data."""
        # Don't use by_alias by default for backward compatibility
        result = super().model_dump(**kwargs)

        # Only exclude None values when exclude_none=True is explicitly set
        if kwargs.get("exclude_none", False):
            result = {k: v for k, v in result.items() if v is not None}

        return result

    def model_dump_json(self, **kwargs) -> str:
        """Dump model as JSON."""
        if "exclude_none" not in kwargs:
            kwargs["exclude_none"] = True
        return super().model_dump_json(**kwargs)

    @classmethod
    def model_validate(cls, data):
        """Enhanced validation that handles error field properly."""
        if isinstance(data, dict):
            data = data.copy()  # Don't modify original

            # Handle error field validation
            if "error" in data and data["error"] is not None:
                if isinstance(data["error"], dict):
                    # Validate error structure
                    if "code" not in data["error"] or "message" not in data["error"]:
                        raise ValueError("Error must have 'code' and 'message' fields")

        return super().model_validate(data)

    @classmethod
    def create_request(
        cls,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[RequestId] = None,
    ) -> "JSONRPCMessage":
        """Create a request message."""
        if id is None:
            import uuid

            id = str(uuid.uuid4())
        return cls(jsonrpc="2.0", id=id, method=method, params=params)  # type: ignore[return-value]

    @classmethod
    def create_notification(
        cls, method: str, params: Optional[Dict[str, Any]] = None
    ) -> "JSONRPCMessage":
        """Create a notification message."""
        return cls(jsonrpc="2.0", method=method, params=params)  # type: ignore[return-value]

    @classmethod
    def create_response(
        cls, id: RequestId, result: Optional[Dict[str, Any]] = None
    ) -> "JSONRPCMessage":
        """Create a successful response message."""
        return cls(jsonrpc="2.0", id=id, result=result or {})  # type: ignore[return-value]

    @classmethod
    def create_error_response(
        cls, id: RequestId, code: int, message: str, data: Any = None
    ) -> "JSONRPCMessage":
        """Create an error response message."""
        error_dict = {"code": code, "message": message}
        if data is not None:
            error_dict["data"] = data
        return cls(jsonrpc="2.0", id=id, error=error_dict)  # type: ignore[return-value]

    def is_request(self) -> bool:
        """Check if this is a request message."""
        return self.method is not None and self.id is not None

    def is_notification(self) -> bool:
        """Check if this is a notification message."""
        return self.method is not None and self.id is None

    def is_response(self) -> bool:
        """Check if this is a response message."""
        return self.method is None and self.id is not None

    def is_error_response(self) -> bool:
        """Check if this is an error response."""
        return self.is_response() and self.error is not None
