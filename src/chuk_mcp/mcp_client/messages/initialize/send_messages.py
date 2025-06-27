# chuk_mcp/chuk_mcp.mcp_client/messages/initialize/send_messages.py
import logging
from typing import Optional, List, Dict, Any
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field

# chuk_mcp imports - using your existing structure
from chuk_mcp.mcp_client.messages.exceptions import NonRetryableError, RetryableError
from chuk_mcp.mcp_client.messages.send_message import send_message
from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.messages.initialize.errors import VersionMismatchError
from chuk_mcp.mcp_client.messages.initialize.mcp_client_capabilities import MCPClientCapabilities
from chuk_mcp.mcp_client.messages.initialize.mcp_client_info import MCPClientInfo
from chuk_mcp.mcp_client.messages.initialize.mcp_server_capabilities import MCPServerCapabilities
from chuk_mcp.mcp_client.messages.initialize.mcp_server_info import MCPServerInfo

# Official MCP protocol versions (following YYYY-MM-DD format)
# Listed in order of preference (newest first)
SUPPORTED_PROTOCOL_VERSIONS = [
    "2025-06-18",    # Current protocol version (per official docs)
    "2025-03-26",    # Previous version (from lifecycle doc)
    "2024-11-05",    # Earlier supported version (legitimate older version)
]

class InitializeParams(McpPydanticBase):
    """Parameters for the initialize request - matches MCP specification."""
    protocolVersion: str
    capabilities: MCPClientCapabilities
    clientInfo: MCPClientInfo
    
    model_config = {"extra": "allow"}

class InitializeResult(McpPydanticBase):
    """Result of initialization request - matches MCP specification."""
    protocolVersion: str
    capabilities: MCPServerCapabilities
    serverInfo: MCPServerInfo
    instructions: Optional[str] = None
    """Instructions describing how to use the server and its features."""
    
    model_config = {"extra": "allow"}

async def send_initialize(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    timeout: float = 5.0,
    supported_versions: Optional[List[str]] = None,
    preferred_version: Optional[str] = None,
) -> Optional[InitializeResult]:
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
        InitializeResult object if successful, None otherwise
        
    Raises:
        VersionMismatchError: If server responds with an unsupported protocol version
        TimeoutError: If server doesn't respond within the timeout
        Exception: For other unexpected errors
    """
    # Determine supported versions
    if supported_versions is None:
        supported_versions = SUPPORTED_PROTOCOL_VERSIONS.copy()
    
    # Determine which version to propose
    if preferred_version and preferred_version in supported_versions:
        # Use preferred version (for testing or specific requirements)
        proposed_version = preferred_version
    else:
        # Use latest supported version (standard behavior)
        proposed_version = supported_versions[0]

    # Create client capabilities and info using your existing classes
    client_capabilities = MCPClientCapabilities()
    client_info = MCPClientInfo()

    # Set initialize params following MCP specification
    init_params = InitializeParams(
        protocolVersion=proposed_version,
        capabilities=client_capabilities,
        clientInfo=client_info,
    )

    try:
        logging.info(f"Proposing MCP protocol version: {proposed_version}")
        logging.debug(f"Client supports versions: {supported_versions}")
        
        # Send initialize request (MUST NOT be part of a batch per spec)
        response = await send_message(
            read_stream=read_stream,
            write_stream=write_stream,
            method="initialize",
            params=init_params.model_dump(exclude_none=True),
            timeout=timeout,
            retries=1,  # Don't retry initialization
        )
        
        logging.debug(f"Received initialization response: {response}")
        
        # Parse the response
        init_result = InitializeResult.model_validate(response)
        
        # Version negotiation per MCP specification
        server_version = str(init_result.protocolVersion)
        
        if server_version == proposed_version:
            # Server accepted our proposed version
            logging.info(f"✅ Version negotiation successful: {server_version}")
        elif server_version in supported_versions:
            # Server counter-proposed with a different version we support
            logging.info(f"✅ Version negotiation successful: {server_version} (server counter-proposal)")
            logging.debug(f"Client proposed: {proposed_version}, Server responded: {server_version}")
        else:
            # Server responded with unsupported version - disconnect per spec
            logging.error(f"❌ Version negotiation failed:")
            logging.error(f"  Client proposed: {proposed_version}")
            logging.error(f"  Server responded: {server_version}")
            logging.error(f"  Client supports: {supported_versions}")
            raise VersionMismatchError(proposed_version, [server_version])

        # Send initialized notification to complete handshake (per spec)
        await send_initialized_notification(write_stream)
        
        logging.info(f"🚀 MCP initialization complete - protocol: {server_version}")
        
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
        if hasattr(e, 'code') and e.code == -32602:  # INVALID_PARAMS
            # Extract version information from error if available
            error_msg = str(e)
            if "protocol version" in error_msg.lower():
                # This is likely a version mismatch, but we don't have the details
                # So raise a generic version mismatch error
                raise VersionMismatchError(proposed_version, ["unknown"])
        
        # For other errors, return None as per original behavior
        return None
    except Exception as e:
        # Log and handle other errors
        logging.error(f"Error during MCP initialization: {e}")
        
        # Check if this is a timeout
        if isinstance(e, TimeoutError):
            raise
            
        # For other unexpected errors, return None
        return None
        
async def send_initialized_notification(write_stream: MemoryObjectSendStream) -> None:
    """
    Send the 'notifications/initialized' notification per MCP specification.
    
    This MUST be sent after successful initialization response to indicate
    the client is ready for normal operations.
    
    Args:
        write_stream: Stream to write the notification to
    """
    try:
        # Create initialized notification (no params per spec)
        notification = JSONRPCMessage.create_notification(
            method="notifications/initialized",
            params={}
        )
        
        # Send the notification
        await write_stream.send(notification)
        logging.debug("✅ Sent notifications/initialized")
        
    except Exception as e:
        logging.error(f"Error sending initialized notification: {e}")
        raise

def get_supported_versions() -> List[str]:
    """Get the list of all supported MCP protocol versions."""
    return SUPPORTED_PROTOCOL_VERSIONS.copy()

def get_current_version() -> str:
    """Get the current (latest) MCP protocol version."""
    return SUPPORTED_PROTOCOL_VERSIONS[0]

def is_version_supported(version: str) -> bool:
    """Check if a specific MCP protocol version is supported."""
    return version in SUPPORTED_PROTOCOL_VERSIONS

def validate_version_format(version: str) -> bool:
    """Validate that a version follows MCP format (YYYY-MM-DD)."""
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, version))

async def send_initialize_with_client_tracking(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
    client: Optional[Any] = None,  # StdioClient instance
    timeout: float = 5.0,
    supported_versions: Optional[List[str]] = None,
    preferred_version: Optional[str] = None,
) -> Optional[InitializeResult]:
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
        InitializeResult object if successful, None otherwise
        
    Raises:
        VersionMismatchError: If server responds with an unsupported protocol version
        TimeoutError: If server doesn't respond within the timeout
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
    
    # If successful and we have a client, set the protocol version
    if result and client and hasattr(client, 'set_protocol_version'):
        client.set_protocol_version(result.protocolVersion)
        logging.info(f"Set client protocol version to: {result.protocolVersion}")
    
    return result