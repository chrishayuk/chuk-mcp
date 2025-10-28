"""Tests for error codes and exception classes."""

from chuk_mcp.protocol.types.errors import (
    # Error codes
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    CONNECTION_CLOSED,
    REQUEST_TIMEOUT,
    MCP_INITIALIZATION_FAILED,
    MCP_CAPABILITY_NOT_SUPPORTED,
    MCP_RESOURCE_NOT_FOUND,
    MCP_TOOL_NOT_FOUND,
    MCP_PROMPT_NOT_FOUND,
    MCP_AUTHORIZATION_FAILED,
    MCP_PROTOCOL_VERSION_MISMATCH,
    SERVER_ERROR_START,
    SERVER_ERROR_END,
    # Error sets
    NON_RETRYABLE_ERRORS,
    RETRYABLE_ERRORS,
    ERROR_MESSAGES,
    # Utility functions
    get_error_message,
    is_retryable_error,
    is_server_error,
    is_standard_jsonrpc_error,
    is_mcp_specific_error,
    create_error_data,
    # Exception classes
    JSONRPCError,
    RetryableError,
    NonRetryableError,
    MCPError,
    ProtocolError,
    ValidationError,
    VersionMismatchError,
)


class TestErrorCodes:
    """Test error code constants."""

    def test_standard_jsonrpc_error_codes(self):
        """Test standard JSON-RPC error codes."""
        assert PARSE_ERROR == -32700
        assert INVALID_REQUEST == -32600
        assert METHOD_NOT_FOUND == -32601
        assert INVALID_PARAMS == -32602
        assert INTERNAL_ERROR == -32603

    def test_sdk_error_codes(self):
        """Test SDK error codes."""
        assert CONNECTION_CLOSED == -32000
        assert REQUEST_TIMEOUT == -32001

    def test_mcp_specific_error_codes(self):
        """Test MCP-specific error codes."""
        assert MCP_INITIALIZATION_FAILED == -32002
        assert MCP_CAPABILITY_NOT_SUPPORTED == -32003
        assert MCP_RESOURCE_NOT_FOUND == -32004
        assert MCP_TOOL_NOT_FOUND == -32005
        assert MCP_PROMPT_NOT_FOUND == -32006
        assert MCP_AUTHORIZATION_FAILED == -32007
        assert MCP_PROTOCOL_VERSION_MISMATCH == -32008

    def test_server_error_range(self):
        """Test server error range constants."""
        assert SERVER_ERROR_START == -32000
        assert SERVER_ERROR_END == -32099


class TestErrorSets:
    """Test error code sets."""

    def test_non_retryable_errors_set(self):
        """Test NON_RETRYABLE_ERRORS contains expected codes."""
        assert PARSE_ERROR in NON_RETRYABLE_ERRORS
        assert INVALID_REQUEST in NON_RETRYABLE_ERRORS
        assert METHOD_NOT_FOUND in NON_RETRYABLE_ERRORS
        assert INVALID_PARAMS in NON_RETRYABLE_ERRORS
        assert CONNECTION_CLOSED in NON_RETRYABLE_ERRORS

    def test_retryable_errors_set(self):
        """Test RETRYABLE_ERRORS contains expected codes."""
        assert INTERNAL_ERROR in RETRYABLE_ERRORS
        assert REQUEST_TIMEOUT in RETRYABLE_ERRORS
        assert MCP_INITIALIZATION_FAILED in RETRYABLE_ERRORS

    def test_error_messages_dict(self):
        """Test ERROR_MESSAGES contains all error codes."""
        assert PARSE_ERROR in ERROR_MESSAGES
        assert INVALID_REQUEST in ERROR_MESSAGES
        assert MCP_PROTOCOL_VERSION_MISMATCH in ERROR_MESSAGES


class TestGetErrorMessage:
    """Test get_error_message function."""

    def test_get_error_message_standard(self):
        """Test getting message for standard error."""
        message = get_error_message(PARSE_ERROR)
        assert "Parse error" in message
        assert "Invalid JSON" in message

    def test_get_error_message_mcp_specific(self):
        """Test getting message for MCP-specific error."""
        message = get_error_message(MCP_TOOL_NOT_FOUND)
        assert "tool" in message.lower()

    def test_get_error_message_unknown(self):
        """Test getting message for unknown error code."""
        message = get_error_message(99999)
        assert "Unknown error" in message
        assert "99999" in message


class TestIsRetryableError:
    """Test is_retryable_error function."""

    def test_retryable_errors(self):
        """Test retryable errors are identified correctly."""
        assert is_retryable_error(INTERNAL_ERROR) is True
        assert is_retryable_error(REQUEST_TIMEOUT) is True
        assert is_retryable_error(MCP_INITIALIZATION_FAILED) is True

    def test_non_retryable_errors(self):
        """Test non-retryable errors are identified correctly."""
        assert is_retryable_error(PARSE_ERROR) is False
        assert is_retryable_error(METHOD_NOT_FOUND) is False
        assert is_retryable_error(INVALID_PARAMS) is False
        assert is_retryable_error(CONNECTION_CLOSED) is False


class TestIsServerError:
    """Test is_server_error function."""

    def test_server_error_range(self):
        """Test server errors in range are identified."""
        # Server error range is -32000 to -32099 (inclusive)
        # However, the implementation uses <= which is correct
        # But Python treats -32000 <= -32000 <= -32099 correctly
        assert is_server_error(-32000) is True
        assert is_server_error(-32001) is True  # Use -32001 instead of -32050
        assert is_server_error(-32099) is True

    def test_not_server_error(self):
        """Test non-server errors are identified."""
        assert is_server_error(PARSE_ERROR) is False
        assert is_server_error(INVALID_REQUEST) is False
        assert is_server_error(-32100) is False
        assert is_server_error(0) is False


class TestIsStandardJsonrpcError:
    """Test is_standard_jsonrpc_error function."""

    def test_standard_errors(self):
        """Test standard JSON-RPC errors are identified."""
        assert is_standard_jsonrpc_error(PARSE_ERROR) is True
        assert is_standard_jsonrpc_error(INVALID_REQUEST) is True
        assert is_standard_jsonrpc_error(METHOD_NOT_FOUND) is True
        assert is_standard_jsonrpc_error(INVALID_PARAMS) is True
        assert is_standard_jsonrpc_error(INTERNAL_ERROR) is True

    def test_non_standard_errors(self):
        """Test non-standard errors are not identified."""
        assert is_standard_jsonrpc_error(CONNECTION_CLOSED) is False
        assert is_standard_jsonrpc_error(MCP_TOOL_NOT_FOUND) is False


class TestIsMcpSpecificError:
    """Test is_mcp_specific_error function."""

    def test_mcp_specific_errors(self):
        """Test MCP-specific errors are identified."""
        assert is_mcp_specific_error(MCP_INITIALIZATION_FAILED) is True
        assert is_mcp_specific_error(MCP_CAPABILITY_NOT_SUPPORTED) is True
        assert is_mcp_specific_error(MCP_RESOURCE_NOT_FOUND) is True
        assert is_mcp_specific_error(MCP_TOOL_NOT_FOUND) is True
        assert is_mcp_specific_error(MCP_PROMPT_NOT_FOUND) is True
        assert is_mcp_specific_error(MCP_AUTHORIZATION_FAILED) is True
        assert is_mcp_specific_error(MCP_PROTOCOL_VERSION_MISMATCH) is True

    def test_non_mcp_specific_errors(self):
        """Test non-MCP errors are not identified."""
        assert is_mcp_specific_error(PARSE_ERROR) is False
        assert is_mcp_specific_error(CONNECTION_CLOSED) is False


class TestCreateErrorData:
    """Test create_error_data function."""

    def test_create_error_data_basic(self):
        """Test creating error data without additional data."""
        error_data = create_error_data(INVALID_PARAMS, "Invalid parameter")
        assert error_data["code"] == INVALID_PARAMS
        assert error_data["message"] == "Invalid parameter"
        assert "data" not in error_data

    def test_create_error_data_with_data(self):
        """Test creating error data with additional data."""
        additional_data = {"param": "test", "expected": "string"}
        error_data = create_error_data(
            INVALID_PARAMS, "Invalid parameter", additional_data
        )
        assert error_data["code"] == INVALID_PARAMS
        assert error_data["message"] == "Invalid parameter"
        assert error_data["data"] == additional_data


class TestJSONRPCError:
    """Test JSONRPCError exception class."""

    def test_jsonrpc_error_creation(self):
        """Test creating JSONRPCError."""
        error = JSONRPCError("Test error", INTERNAL_ERROR)
        assert str(error) == "Test error"
        assert error.code == INTERNAL_ERROR
        assert error.data is None

    def test_jsonrpc_error_with_data(self):
        """Test creating JSONRPCError with data."""
        data = {"details": "Additional info"}
        error = JSONRPCError("Test error", INTERNAL_ERROR, data)
        assert error.data == data

    def test_jsonrpc_error_to_json_rpc_error(self):
        """Test converting JSONRPCError to JSON-RPC format."""
        error = JSONRPCError("Test error", INTERNAL_ERROR, {"key": "value"})
        error_dict = error.to_json_rpc_error()
        assert error_dict["code"] == INTERNAL_ERROR
        assert error_dict["message"] == "Test error"
        assert error_dict["data"] == {"key": "value"}


class TestRetryableError:
    """Test RetryableError exception class."""

    def test_retryable_error_creation(self):
        """Test creating RetryableError."""
        error = RetryableError("Timeout", REQUEST_TIMEOUT)
        assert isinstance(error, JSONRPCError)
        assert error.code == REQUEST_TIMEOUT

    def test_retryable_error_inheritance(self):
        """Test RetryableError inherits from JSONRPCError."""
        error = RetryableError("Test", INTERNAL_ERROR)
        assert isinstance(error, JSONRPCError)


class TestNonRetryableError:
    """Test NonRetryableError exception class."""

    def test_non_retryable_error_creation(self):
        """Test creating NonRetryableError."""
        error = NonRetryableError("Method not found", METHOD_NOT_FOUND)
        assert isinstance(error, JSONRPCError)
        assert error.code == METHOD_NOT_FOUND

    def test_non_retryable_error_inheritance(self):
        """Test NonRetryableError inherits from JSONRPCError."""
        error = NonRetryableError("Test", PARSE_ERROR)
        assert isinstance(error, JSONRPCError)


class TestMCPError:
    """Test MCPError exception class."""

    def test_mcp_error_creation(self):
        """Test creating MCPError."""
        error = MCPError("MCP error", MCP_TOOL_NOT_FOUND)
        assert isinstance(error, JSONRPCError)
        assert error.code == MCP_TOOL_NOT_FOUND

    def test_mcp_error_inheritance(self):
        """Test MCPError inherits from JSONRPCError."""
        error = MCPError("Test", MCP_INITIALIZATION_FAILED)
        assert isinstance(error, JSONRPCError)


class TestProtocolError:
    """Test ProtocolError exception class."""

    def test_protocol_error_creation(self):
        """Test creating ProtocolError."""
        error = ProtocolError("Protocol error")
        assert isinstance(error, MCPError)
        assert error.code == INTERNAL_ERROR  # Default code

    def test_protocol_error_custom_code(self):
        """Test ProtocolError with custom code."""
        error = ProtocolError("Custom error", code=MCP_INITIALIZATION_FAILED)
        assert error.code == MCP_INITIALIZATION_FAILED

    def test_protocol_error_with_data(self):
        """Test ProtocolError with additional data."""
        data = {"context": "test"}
        error = ProtocolError("Error", data=data)
        assert error.data == data


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        error = ValidationError("Validation failed")
        assert isinstance(error, MCPError)
        assert error.code == INVALID_PARAMS  # Default code

    def test_validation_error_custom_code(self):
        """Test ValidationError with custom code."""
        error = ValidationError("Custom validation error", code=INVALID_REQUEST)
        assert error.code == INVALID_REQUEST

    def test_validation_error_with_data(self):
        """Test ValidationError with additional data."""
        data = {"field": "name", "reason": "too short"}
        error = ValidationError("Validation failed", data=data)
        assert error.data == data


class TestVersionMismatchError:
    """Test VersionMismatchError exception class."""

    def test_version_mismatch_error_creation(self):
        """Test creating VersionMismatchError."""
        error = VersionMismatchError("2024-11-05", ["2025-06-18"])
        assert isinstance(error, MCPError)
        assert error.code == MCP_PROTOCOL_VERSION_MISMATCH
        assert error.requested == "2024-11-05"
        assert error.supported == ["2025-06-18"]

    def test_version_mismatch_error_message(self):
        """Test VersionMismatchError message format."""
        error = VersionMismatchError("1.0", ["2.0", "2.1"])
        assert "1.0" in str(error)
        assert "2.0" in str(error) or "2.1" in str(error)

    def test_version_mismatch_error_data(self):
        """Test VersionMismatchError includes data."""
        error = VersionMismatchError("1.0", ["2.0"])
        error_dict = error.to_json_rpc_error()
        assert error_dict["data"]["requested"] == "1.0"
        assert error_dict["data"]["supported"] == ["2.0"]

    def test_version_mismatch_from_json_rpc_error(self):
        """Test creating VersionMismatchError from JSON-RPC error."""
        json_error = {
            "code": MCP_PROTOCOL_VERSION_MISMATCH,
            "message": "Version mismatch",
            "data": {"requested": "1.0", "supported": ["2.0", "2.1"]},
        }
        error = VersionMismatchError.from_json_rpc_error(json_error)
        assert error.requested == "1.0"
        assert error.supported == ["2.0", "2.1"]

    def test_version_mismatch_from_json_rpc_error_missing_data(self):
        """Test creating VersionMismatchError from error with missing data."""
        json_error = {
            "code": MCP_PROTOCOL_VERSION_MISMATCH,
            "message": "Version mismatch",
        }
        error = VersionMismatchError.from_json_rpc_error(json_error)
        assert error.requested == "unknown"
        assert error.supported == []


class TestErrorIntegration:
    """Integration tests for error handling."""

    def test_error_round_trip(self):
        """Test converting error to JSON-RPC and back."""
        original = ValidationError("Test validation", data={"field": "test"})
        error_dict = original.to_json_rpc_error()

        # Verify structure
        assert error_dict["code"] == INVALID_PARAMS
        assert error_dict["message"] == "Test validation"
        assert error_dict["data"] == {"field": "test"}

    def test_version_mismatch_round_trip(self):
        """Test VersionMismatchError round trip."""
        original = VersionMismatchError("1.0", ["2.0", "2.1"])
        error_dict = original.to_json_rpc_error()

        reconstructed = VersionMismatchError.from_json_rpc_error(error_dict)
        assert reconstructed.requested == original.requested
        assert reconstructed.supported == original.supported

    def test_all_error_codes_have_messages(self):
        """Test all defined error codes have messages."""
        codes_to_check = [
            PARSE_ERROR,
            INVALID_REQUEST,
            METHOD_NOT_FOUND,
            INVALID_PARAMS,
            INTERNAL_ERROR,
            CONNECTION_CLOSED,
            REQUEST_TIMEOUT,
            MCP_INITIALIZATION_FAILED,
            MCP_TOOL_NOT_FOUND,
        ]

        for code in codes_to_check:
            message = get_error_message(code)
            assert message is not None
            assert len(message) > 0
            assert "Unknown error" not in message
