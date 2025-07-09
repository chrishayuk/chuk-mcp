# chuk_mcp/transports/stdio/stdio_client.py
import json
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple, List

import anyio
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

# Import version-aware batching
from chuk_mcp.protocol.features.batching import BatchProcessor, supports_batching
from chuk_mcp.mcp_client.host.environment import get_default_environment
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from .parameters import StdioParameters

__all__ = ["StdioClient", "stdio_client", "stdio_client_with_initialize"]

logger = logging.getLogger(__name__)


class StdioClient:
    """
    A newline-delimited JSON-RPC client speaking over stdio to a subprocess.

    Maintains compatibility with existing tests while providing working
    message transmission functionality. Supports version-aware batch processing.
    """

    def __init__(self, server: StdioParameters):
        if not server.command:
            raise ValueError("Server command must not be empty.")
        if not isinstance(server.args, (list, tuple)):
            raise ValueError("Server arguments must be a list or tuple.")

        self.server = server

        # Global broadcast stream for notifications (id == None) - use buffer to prevent deadlock
        self._notify_send: MemoryObjectSendStream
        self.notifications: MemoryObjectReceiveStream
        self._notify_send, self.notifications = anyio.create_memory_object_stream(100)

        # Per-request streams; key = request id - for test compatibility
        self._pending: Dict[str, MemoryObjectSendStream] = {}

        # Main communication streams - use buffer to prevent deadlock
        self._incoming_send: MemoryObjectSendStream
        self._incoming_recv: MemoryObjectReceiveStream
        self._incoming_send, self._incoming_recv = anyio.create_memory_object_stream(100)

        self._outgoing_send: MemoryObjectSendStream
        self._outgoing_recv: MemoryObjectReceiveStream
        self._outgoing_send, self._outgoing_recv = anyio.create_memory_object_stream(100)

        self.process: Optional[anyio.abc.Process] = None
        self.tg: Optional[anyio.abc.TaskGroup] = None
        
        # Version-aware batch processing
        self.batch_processor = BatchProcessor()
        logger.debug("StdioClient initialized with version-aware batching")

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version and update batching behavior."""
        self.batch_processor.update_protocol_version(version)
        logger.info(f"Protocol version set to: {version}, batching enabled: {self.batch_processor.batching_enabled}")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    
    async def _route_message(self, msg: JSONRPCMessage) -> None:
        """Fast routing with minimal overhead."""
        
        # Main stream (always)
        try:
            await self._incoming_send.send(msg)
        except anyio.BrokenResourceError:
            return

        # Notifications
        if msg.id is None:
            try:
                self._notify_send.send_nowait(msg)
            except (anyio.WouldBlock, anyio.BrokenResourceError):
                pass
            return

        # Legacy streams (handle responses and requests with IDs)
        legacy_stream = self._pending.pop(str(msg.id), None)
        if legacy_stream:
            try:
                await legacy_stream.send(msg)
                await legacy_stream.aclose()
            except anyio.BrokenResourceError:
                pass
        else:
            # Log warning for unknown IDs (needed for tests)
            logger.debug(f"Received message for unknown id: {msg.id}")

    async def _stdout_reader(self) -> None:
        """Read server stdout and route JSON-RPC messages with version-aware batch support."""
        try:
            assert self.process and self.process.stdout

            buffer = ""
            logger.debug("stdout_reader started")

            async for chunk in self.process.stdout:
                # Handle both bytes and string chunks
                if isinstance(chunk, bytes):
                    buffer += chunk.decode('utf-8')
                else:
                    buffer += chunk

                # Split on newlines
                lines = buffer.split('\n')
                buffer = lines[-1]
                
                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        await self._process_message_data(data)
                            
                    except json.JSONDecodeError as exc:
                        logger.error("JSON decode error: %s  [line: %.120s]", exc, line)
                    except Exception as exc:
                        logger.error("Error processing message: %s", exc)
                        logger.debug("Traceback:\n%s", traceback.format_exc())

            logger.debug("stdout_reader exiting")
        except Exception as e:
            logger.error(f"stdout_reader error: {e}")
            logger.debug("Traceback:\n%s", traceback.format_exc())

    async def _process_message_data(self, data) -> None:
        """Process message data with version-aware batching support."""
        
        # Check if we can process this message
        if not self.batch_processor.can_process_batch(data):
            logger.warning(f"Rejecting batch message in protocol version {self.batch_processor.protocol_version}")
            
            # Send error response back to server
            error_response = self.batch_processor.create_batch_rejection_error()
            await self._send_error_response(error_response)
            return
        
        # Handle JSON-RPC batch messages (if supported by version)
        if isinstance(data, list):
            if self.batch_processor.batching_enabled:
                logger.debug(f"Processing batch with {len(data)} messages (protocol: {self.batch_processor.protocol_version})")
                for item in data:
                    try:
                        msg = JSONRPCMessage.model_validate(item)
                        await self._route_message(msg)
                        logger.debug(f"Batch item: {msg.method or 'response'} (id: {msg.id})")
                    except Exception as exc:
                        logger.error("Error processing batch item: %s", exc)
                        logger.debug("Invalid batch item: %.120s", json.dumps(item))
            else:
                # This should not happen as we check can_process_batch above
                logger.error(f"Unexpected batch message in version {self.batch_processor.protocol_version}")
        else:
            # Single message
            try:
                msg = JSONRPCMessage.model_validate(data)
                await self._route_message(msg)
                logger.debug(f"Received: {msg.method or 'response'} (id: {msg.id})")
            except Exception as exc:
                logger.error("Error processing single message: %s", exc)

    async def _send_error_response(self, error_response: Dict) -> None:
        """Send an error response back to the server."""
        try:
            if self.process and self.process.stdin:
                json_str = json.dumps(error_response)
                await self.process.stdin.send(f"{json_str}\n".encode())
                logger.debug(f"Sent error response: {error_response.get('error', {}).get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")

    async def _stdin_writer(self) -> None:
        """Forward outgoing JSON-RPC messages to the server's stdin."""
        try:
            assert self.process and self.process.stdin
            logger.debug("stdin_writer started")

            async for message in self._outgoing_recv:
                try:
                    # CRITICAL FIX: Handle different message types properly
                    if isinstance(message, str):
                        # Raw string message (already JSON)
                        json_str = message
                    elif hasattr(message, 'model_dump_json'):
                        # Pydantic model (JSONRPCMessage) - use model_dump_json
                        json_str = message.model_dump_json(exclude_none=True)
                    elif hasattr(message, 'model_dump'):
                        # Pydantic model - convert to dict first, then to JSON
                        json_str = json.dumps(message.model_dump(exclude_none=True))
                    elif isinstance(message, dict):
                        # Plain dict - serialize directly
                        json_str = json.dumps(message)
                    else:
                        # Other object types - try to serialize
                        json_str = json.dumps(message)
                    
                    # Send the JSON string
                    await self.process.stdin.send(f"{json_str}\n".encode())
                    
                    # Enhanced logging for debugging
                    if hasattr(message, 'method'):
                        logger.debug(f"Sent: {message.method or 'response'} (id: {message.id})")
                    elif isinstance(message, dict) and 'method' in message:
                        logger.debug(f"Sent: {message.get('method', 'response')} (id: {message.get('id')})")
                    else:
                        logger.debug(f"Sent raw message: {json_str[:100]}...")
                        
                except Exception as exc:
                    logger.error("Error serializing message in stdin_writer: %s", exc)
                    logger.debug("Failed message type: %s", type(message))
                    logger.debug("Failed message: %s", repr(message)[:200])
                    logger.debug("Traceback:\n%s", traceback.format_exc())
                    continue

            logger.debug("stdin_writer exiting; closing server stdin")
            if self.process and self.process.stdin:
                await self.process.stdin.aclose()
        except Exception as e:
            logger.error(f"stdin_writer error: {e}")
            logger.debug("Traceback:\n%s", traceback.format_exc())

    # ------------------------------------------------------------------ #
    # Public API for request lifecycle (for test compatibility)
    # ------------------------------------------------------------------ #
    def new_request_stream(self, req_id: str) -> MemoryObjectReceiveStream:
        """
        Create a one-shot receive stream for *req_id*.
        The caller can await .receive() to get the JSONRPCMessage.
        """
        # Use buffer size of 1 to avoid deadlock in tests
        send_s, recv_s = anyio.create_memory_object_stream(1)
        self._pending[req_id] = send_s
        return recv_s

    async def send_json(self, msg: JSONRPCMessage) -> None:
        """
        Queue *msg* for transmission.
        """
        try:
            # Ensure the message is properly queued - no pre-serialization here
            await self._outgoing_send.send(msg)
        except anyio.BrokenResourceError:
            logger.warning("Cannot send message - outgoing stream is closed")

    # ------------------------------------------------------------------ #
    # New API for stdio_client context manager
    # ------------------------------------------------------------------ #
    def get_streams(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get the read and write streams for communication."""
        return self._incoming_recv, self._outgoing_send

    # ------------------------------------------------------------------ #
    # Version information methods
    # ------------------------------------------------------------------ #
    def get_protocol_version(self) -> Optional[str]:
        """Get the current protocol version."""
        return self.batch_processor.protocol_version
    
    def is_batching_enabled(self) -> bool:
        """Check if batching is currently enabled."""
        return self.batch_processor.batching_enabled
    
    def get_batching_info(self) -> Dict[str, any]:
        """Get information about batching support."""
        return {
            "protocol_version": self.batch_processor.protocol_version,
            "batching_enabled": self.batch_processor.batching_enabled,
            "supports_batch_function": supports_batching(self.batch_processor.protocol_version)
        }

    # ------------------------------------------------------------------ #
    # async context-manager interface
    # ------------------------------------------------------------------ #
    async def __aenter__(self):
        try:
            self.process = await anyio.open_process(
                [self.server.command, *self.server.args],
                env=self.server.env or get_default_environment(),
                stderr=sys.stderr,
                start_new_session=True,
            )
            logger.debug("Subprocess PID %s (%s)", self.process.pid, self.server.command)

            self.tg = anyio.create_task_group()
            await self.tg.__aenter__()
            self.tg.start_soon(self._stdout_reader)
            self.tg.start_soon(self._stdin_writer)

            return self
        except Exception as e:
            logger.error(f"Error starting stdio client: {e}")
            raise

    async def __aexit__(self, exc_type, exc, tb):
        """COMPLETE FIXED VERSION: Handle shutdown without JSON or cancel scope errors."""
        try:
            # Close outgoing stream to signal stdin_writer to exit
            await self._outgoing_send.aclose()
            
            if self.tg:
                # Cancel all tasks
                self.tg.cancel_scope.cancel()
                
                # CRITICAL FIX: Do NOT use asyncio.wait_for() with anyio task groups!
                # This was causing the "cancel scope in different task" error.
                # Just handle the BaseExceptionGroup properly.
                try:
                    await self.tg.__aexit__(None, None, None)
                except BaseExceptionGroup as eg:
                    # FIXED: Handle exception groups by changing log levels appropriately
                    # Cancel scope errors during shutdown are EXPECTED, not actual errors
                    for exc in eg.exceptions:
                        if not isinstance(exc, anyio.get_cancelled_exc_class()):
                            error_msg = str(exc)
                            if "cancel scope" in error_msg.lower():
                                # CRITICAL: Log cancel scope issues as DEBUG, not ERROR
                                # This eliminates the misleading error message
                                logger.debug(f"Cancel scope issue during shutdown (expected): {exc}")
                            elif "json object must be str" in error_msg.lower():
                                # JSON serialization errors are actual bugs
                                logger.error(f"JSON serialization error during shutdown: {exc}")
                            else:
                                # Only real errors should be logged as ERROR
                                logger.error(f"Task error during shutdown: {exc}")
                            
                except Exception as e:
                    # Handle regular exceptions for older anyio versions
                    if not isinstance(e, anyio.get_cancelled_exc_class()):
                        error_msg = str(e)
                        if "cancel scope" in error_msg.lower():
                            # CRITICAL: Log cancel scope issues as DEBUG, not ERROR
                            logger.debug(f"Cancel scope issue during shutdown (expected): {e}")
                        elif "json object must be str" in error_msg.lower():
                            # JSON serialization errors are actual bugs
                            logger.error(f"JSON serialization error during shutdown: {e}")
                        else:
                            logger.error(f"Task error during shutdown: {e}")
                
            if self.process and self.process.returncode is None:
                await self._terminate_process()
                
        except Exception as e:
            logger.debug(f"Error during stdio client shutdown: {e}")
            
        return False

    async def _terminate_process(self) -> None:
        """Terminate the helper process gracefully, with shorter timeouts."""
        if not self.process:
            return
        try:
            if self.process.returncode is None:
                logger.debug("Terminating subprocess…")
                self.process.terminate()
                try:
                    # Reduced timeout from 5s to 1s
                    with anyio.fail_after(1.0):
                        await self.process.wait()
                except TimeoutError:
                    # Changed from WARNING to DEBUG level
                    logger.debug("Graceful term timed out – killing …")
                    self.process.kill()
                    try:
                        # Reduced timeout from 5s to 1s  
                        with anyio.fail_after(1.0):
                            await self.process.wait()
                    except TimeoutError:
                        # Changed from WARNING to DEBUG level
                        logger.debug("Process kill timed out during shutdown")
        except Exception as e:
            logger.debug(f"Error during process termination: {e}")


# ---------------------------------------------------------------------- #
# Convenience context-manager that returns streams for send_message
# ---------------------------------------------------------------------- #
@asynccontextmanager
async def stdio_client(server: StdioParameters) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
    """
    Create a stdio client and return streams that work with send_message.
    
    Usage:
        async with stdio_client(server_params) as (read_stream, write_stream):
            response = await send_message(read_stream, write_stream, "ping")
    
    Returns:
        Tuple of (read_stream, write_stream) for JSON-RPC communication
    """
    client = StdioClient(server)
    
    try:
        async with client:
            # Return the streams that send_message expects
            yield client.get_streams()
    except BaseExceptionGroup as eg:
        # FIXED: Handle exception groups by changing log levels appropriately
        for exc in eg.exceptions:
            if not isinstance(exc, anyio.get_cancelled_exc_class()):
                error_msg = str(exc)
                if "cancel scope" in error_msg.lower():
                    logger.debug(f"stdio_client cancel scope issue (expected during shutdown): {exc}")
                elif "json object must be str" in error_msg.lower():
                    logger.error(f"JSON serialization error in stdio_client: {exc}")
                    raise  # Re-raise JSON errors as they indicate bugs
                else:
                    logger.error(f"stdio_client error: {exc}")
                    raise  # Re-raise non-cancel-scope errors
    except Exception as e:
        # Handle regular exceptions
        if not isinstance(e, anyio.get_cancelled_exc_class()):
            error_msg = str(e)
            if "cancel scope" in error_msg.lower():
                logger.debug(f"stdio_client cancel scope issue (expected during shutdown): {e}")
            elif "json object must be str" in error_msg.lower():
                logger.error(f"JSON serialization error in stdio_client: {e}")
                raise  # Re-raise JSON errors as they indicate bugs
            else:
                logger.error(f"stdio_client error: {e}")
                raise  # Re-raise non-cancel-scope errors


@asynccontextmanager
async def stdio_client_with_initialize(
    server: StdioParameters,
    timeout: float = 5.0,
    supported_versions: Optional[List[str]] = None,
    preferred_version: Optional[str] = None,
):
    """
    Create a stdio client and automatically send initialization.
    
    This combines stdio_client with send_initialize_with_client_tracking
    to provide a convenient way to start an MCP server with proper
    initialization and version tracking.
    
    Usage:
        async with stdio_client_with_initialize(server_params) as (read_stream, write_stream, init_result):
            # init_result contains the server capabilities and protocol version
            response = await send_message(read_stream, write_stream, "tools/list")
    
    Args:
        server: Server parameters for starting the subprocess
        timeout: Timeout for initialization in seconds
        supported_versions: List of supported protocol versions
        preferred_version: Preferred protocol version to negotiate
        
    Yields:
        Tuple of (read_stream, write_stream, init_result)
        
    Raises:
        VersionMismatchError: If version negotiation fails
        TimeoutError: If initialization times out
        Exception: For other initialization failures
    """
    from chuk_mcp.protocol.messages.initialize.send_messages import send_initialize_with_client_tracking
    
    client = StdioClient(server)
    
    try:
        async with client:
            read_stream, write_stream = client.get_streams()
            
            # Perform initialization with version tracking
            init_result = await send_initialize_with_client_tracking(
                read_stream=read_stream,
                write_stream=write_stream,
                client=client,
                timeout=timeout,
                supported_versions=supported_versions,
                preferred_version=preferred_version,
            )
            
            if not init_result:
                raise Exception("Initialization failed")
            
            # Yield the streams and initialization result
            yield read_stream, write_stream, init_result
            
    except BaseExceptionGroup as eg:
        # FIXED: Handle exception groups by changing log levels appropriately
        for exc in eg.exceptions:
            if not isinstance(exc, anyio.get_cancelled_exc_class()):
                error_msg = str(exc)
                if "cancel scope" in error_msg.lower():
                    logger.debug(f"stdio_client_with_initialize cancel scope issue (expected): {exc}")
                elif "json object must be str" in error_msg.lower():
                    logger.error(f"JSON serialization error in stdio_client_with_initialize: {exc}")
                    raise  # Re-raise JSON errors as they indicate bugs
                else:
                    logger.error(f"stdio_client_with_initialize error: {exc}")
                    raise  # Re-raise non-cancel-scope errors
    except Exception as e:
        # Handle regular exceptions
        if not isinstance(e, anyio.get_cancelled_exc_class()):
            error_msg = str(e)
            if "cancel scope" in error_msg.lower():
                logger.debug(f"stdio_client_with_initialize cancel scope issue (expected): {e}")
            elif "json object must be str" in error_msg.lower():
                logger.error(f"JSON serialization error in stdio_client_with_initialize: {e}")
                raise  # Re-raise JSON errors as they indicate bugs
            else:
                logger.error(f"stdio_client_with_initialize error: {e}")
                raise  # Re-raise non-cancel-scope errors


# ---------------------------------------------------------------------- #
# Legacy function for backward compatibility
# ---------------------------------------------------------------------- #
def _supports_batch_processing(protocol_version: Optional[str]) -> bool:
    """
    Legacy function for backward compatibility.
    
    Use BatchProcessor or supports_batching() function instead.
    """
    import warnings
    warnings.warn(
        "_supports_batch_processing is deprecated. Use supports_batching() or BatchProcessor instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return supports_batching(protocol_version)