# chuk_mcp/protocol/messages/initialize/send_messages.py
import logging
from typing import Optional, List, Any
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

# Import from protocol base and types
from ...mcp_pydantic_base import McpPydanticBase
from ...types.errors import (
    NonRetryableError,
    RetryableError,
    VersionMismatchError,
    INVALID_PARAMS,
)
from ...types.versioning import (
    SUPPORTED_VERSIONS,
    ProtocolVersion,
)
from ...types.capabilities import ClientCapabilities, ServerCapabilities
from ...types.info import ClientInfo, ServerInfo

# Import from messages layer
from ..send_message import send_message

# Use the constants from versioning instead of defining here
SUPPORTED_PROTOCOL_VERSIONS = SUPPORTED_VERSIONS  # For backward compatibility


class InitializeParams(McpPydanticBase):
    """Parameters for the initialize request - matches MCP specification."""

    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: ClientInfo

    model_config = {"extra": "allow"}


class InitializeResult(McpPydanticBase):
    """Result of initialization request - matches MCP specification."""

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: ServerInfo
    instructions: Optional[str] = None
    """Instructions describing how to use the server and its features."""

    model_config = {"extra": "allow"}


async def send_initialize(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    timeout: float = 60.0,
    supported_versions: Optional[List[str]] = None,
    preferred_version: Optional[str] = None,
) -> InitializeResult:
    """
    Send an initialization request following MCP protocol specification.

    Implements proper version negotiation as per MCP lifecycle:
    1. Client sends preferred version
    2. Server responds with same version (if supported) or different version
    3. Client accepts or disconnects if unsupported

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        timeout: Timeout in seconds for the response
        supported_versions: List of protocol versions supported by the client
        preferred_version: Specific version to prefer (for testing/compatibility)

    Returns:
        InitializeResult object on success

    Raises:
        VersionMismatchError: If server responds with an unsupported protocol version
        TimeoutError: If server doesn't respond within the timeout
        RetryableError: For retryable JSON-RPC errors (e.g., 401 authentication failures)
        NonRetryableError: For non-retryable JSON-RPC errors
        Exception: For other unexpected errors
    """
    # Determine supported versions
    if supported_versions is None:
        supported_versions = SUPPORTED_VERSIONS.copy()

    # Determine which version to propose
    if preferred_version and preferred_version in supported_versions:
        # Use preferred version (for testing or specific requirements)
        proposed_version = preferred_version
    else:
        # Use latest supported version (standard behavior)
        proposed_version = supported_versions[0]

    # Create client capabilities and info using types layer classes
    client_capabilities = ClientCapabilities()
    client_info = ClientInfo()

    # Set initialize params following MCP specification
    init_params = InitializeParams(
        protocolVersion=proposed_version,
        capabilities=client_capabilities,
        clientInfo=client_info,
    )

    try:
        logging.debug(f"Proposing MCP protocol version: {proposed_version}")
        logging.debug(f"Client supports versions: {supported_versions}")

        # Send initialize request (MUST NOT be part of a batch per spec)
        response = await send_message(
            read_stream=read_stream,
            write_stream=write_stream,
            method="initialize",
            params=init_params.model_dump(exclude_none=True),
            timeout=timeout,
        )

        logging.debug(f"Received initialization response: {response}")

        # Parse the response
        init_result = InitializeResult.model_validate(response)

        # Version negotiation per MCP specification
        server_version = str(init_result.protocolVersion)

        if server_version == proposed_version:
            # Server accepted our proposed version
            logging.debug(f"Version negotiation successful: {server_version}")
        elif server_version in supported_versions:
            # Server counter-proposed with a different version we support
            logging.debug(
                f"Version negotiation successful: {server_version} (server counter-proposal)"
            )
            logging.debug(
                f"Client proposed: {proposed_version}, Server responded: {server_version}"
            )
        else:
            # Server responded with unsupported version - disconnect per spec
            logging.error("Version negotiation failed:")
            logging.error(f"  Client proposed: {proposed_version}")
            logging.error(f"  Server responded: {server_version}")
            logging.error(f"  Client supports: {supported_versions}")
            raise VersionMismatchError(proposed_version, [server_version])

        # Send initialized notification to complete handshake (per spec)
        await send_initialized_notification(write_stream)

        logging.debug(f"MCP initialization complete - protocol: {server_version}")

        return init_result

    except VersionMismatchError:
        # Re-raise version mismatch errors (client should disconnect)
        raise
    except TimeoutError:
        # Re-raise timeout errors
        raise
    except (RetryableError, NonRetryableError) as e:
        # Handle JSON-RPC errors from send_message
        logging.error(f"Error during MCP initialization: {e}")

        # Check if this is a version mismatch error specifically
        if hasattr(e, "code") and e.code == INVALID_PARAMS:  # -32602
            # Extract version information from error if available
            error_msg = str(e)
            if "protocol version" in error_msg.lower():
                # This is likely a version mismatch, but we don't have the details
                # So raise a generic version mismatch error
                raise VersionMismatchError(proposed_version, ["unknown"])

        # Re-raise JSON-RPC errors instead of swallowing them
        # This allows proper error handling upstream (e.g., OAuth re-authentication)
        raise
    except Exception as e:
        # Log and handle other errors
        logging.error(f"Error during MCP initialization: {e}")

        # Always re-raise exceptions instead of returning None
        # This allows proper error handling and debugging upstream
        raise


async def send_initialized_notification(write_stream: MemoryObjectSendStream) -> None:
    """
    Send the 'notifications/initialized' notification per MCP specification.

    This MUST be sent after successful initialization response to indicate
    the client is ready for normal operations.

    Args:
        write_stream: Stream to write the notification to
    """
    from ..json_rpc_message import create_notification

    try:
        # Create initialized notification (no params per spec)
        notification = create_notification(
            method="notifications/initialized", params={}
        )

        # Send the notification
        await write_stream.send(notification)
        logging.debug("Sent notifications/initialized")

    except Exception as e:
        logging.error(f"Error sending initialized notification: {e}")
        raise


def get_supported_versions() -> List[str]:
    """Get the list of all supported MCP protocol versions."""
    return ProtocolVersion.get_all_supported()


def get_current_version() -> str:
    """Get the current (latest) MCP protocol version."""
    return ProtocolVersion.get_latest_supported()


def is_version_supported(version: str) -> bool:
    """Check if a specific MCP protocol version is supported."""
    return ProtocolVersion.is_supported(version)


def validate_version_format(version: str) -> bool:
    """Validate that a version follows MCP format (YYYY-MM-DD)."""
    return ProtocolVersion.validate_format(version)


async def send_initialize_with_client_tracking(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    client: Optional[Any] = None,  # StdioClient instance
    timeout: float = 60.0,
    supported_versions: Optional[List[str]] = None,
    preferred_version: Optional[str] = None,
) -> InitializeResult:
    """
    Send an initialization request and track the protocol version in the client.

    This version extends send_initialize to automatically set the negotiated
    protocol version in the StdioClient for version-aware feature support.

    Args:
        read_stream: Stream to read responses from
        write_stream: Stream to write requests to
        client: Optional StdioClient instance to track protocol version
        timeout: Timeout in seconds for the response
        supported_versions: List of protocol versions supported by the client
        preferred_version: Specific version to prefer (for testing/compatibility)

    Returns:
        InitializeResult object on success

    Raises:
        VersionMismatchError: If server responds with an unsupported protocol version
        TimeoutError: If server doesn't respond within the timeout
        RetryableError: For retryable JSON-RPC errors (e.g., 401 authentication failures)
        NonRetryableError: For non-retryable JSON-RPC errors
        Exception: For other unexpected errors
    """
    # Call the standard initialize function
    result = await send_initialize(
        read_stream=read_stream,
        write_stream=write_stream,
        timeout=timeout,
        supported_versions=supported_versions,
        preferred_version=preferred_version,
    )

    # Set the protocol version if we have a client
    if client and hasattr(client, "set_protocol_version"):
        client.set_protocol_version(result.protocolVersion)
        logging.debug(f"Set client protocol version to: {result.protocolVersion}")

    return result
