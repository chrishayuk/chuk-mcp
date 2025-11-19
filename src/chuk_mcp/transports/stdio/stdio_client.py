# chuk_mcp/transports/stdio/stdio_client.py
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple, List, Any, AsyncGenerator

import anyio
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

# PERFORMANCE: Use fast JSON implementation (orjson if available, stdlib json fallback)
from chuk_mcp.protocol import fast_json as json

# BaseExceptionGroup is Python 3.11+
try:
    from builtins import BaseExceptionGroup  # type: ignore[attr-defined]
except (ImportError, AttributeError):
    BaseExceptionGroup = Exception  # type: ignore[misc,assignment]

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

        # FIXED: Don't create streams in __init__ - defer to __aenter__
        # These will be initialized when entering async context
        self._notify_send: Optional[MemoryObjectSendStream] = None
        self.notifications: Optional[MemoryObjectReceiveStream] = None

        self._incoming_send: Optional[MemoryObjectSendStream] = None
        self._incoming_recv: Optional[MemoryObjectReceiveStream] = None

        self._outgoing_send: Optional[MemoryObjectSendStream] = None
        self._outgoing_recv: Optional[MemoryObjectReceiveStream] = None

        # Per-request streams; key = request id - for test compatibility
        self._pending: Dict[str, MemoryObjectSendStream] = {}

        self.process: Optional[anyio.abc.Process] = None
        self.tg: Optional[anyio.abc.TaskGroup] = None

        self._streams_initialized: bool = False

        # Version-aware batch processing
        self.batch_processor = BatchProcessor()
        logger.debug(
            "StdioClient initialized (streams will be created in async context)"
        )

    def _ensure_streams_initialized(self):
        """Ensure streams are initialized before use."""
        if not self._streams_initialized:
            raise RuntimeError(
                "Streams not initialized. StdioClient must be used as async context manager."
            )

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version and update batching behavior."""
        self.batch_processor.update_protocol_version(version)
        logger.debug(
            f"Protocol version set to: {version}, batching enabled: {self.batch_processor.batching_enabled}"
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _route_message(self, msg: JSONRPCMessage) -> None:
        """Fast routing with minimal overhead.

        PERFORMANCE OPTIMIZED:
        - Single attribute access for msg_id (cached)
        - Early return for notifications (skip unnecessary stream sends)
        - Direct dict lookup instead of pop+check for legacy streams
        """
        self._ensure_streams_initialized()

        # PERFORMANCE: Cache msg_id access (single getattr instead of multiple)
        msg_id = getattr(msg, "id", None)

        # PERFORMANCE: Fast path for notifications - skip main stream if only notification needed
        if msg_id is None:
            # Notification path: send to notification stream first, then main stream
            try:
                self._notify_send.send_nowait(msg)  # type: ignore[union-attr]
            except (anyio.WouldBlock, anyio.BrokenResourceError):
                pass

            # Also send to main stream for general listeners
            try:
                await self._incoming_send.send(msg)  # type: ignore[union-attr]
            except anyio.BrokenResourceError:
                pass

            return  # Early return - no legacy stream handling needed

        # PERFORMANCE: Check legacy streams first (more specific routing)
        # Use get() instead of pop() to avoid KeyError and allow dict reuse
        msg_id_str = str(msg_id)
        legacy_stream = self._pending.get(msg_id_str)

        if legacy_stream:
            # PERFORMANCE: Remove from pending dict only after confirming it exists
            del self._pending[msg_id_str]

            # Send to legacy stream (for backward compatibility with old test patterns)
            try:
                await legacy_stream.send(msg)
                await legacy_stream.aclose()
            except anyio.BrokenResourceError:
                pass
        else:
            # No legacy stream - just log for debugging
            logger.debug(f"Received message for unknown id: {msg_id}")

        # Send to main stream for general message handling
        try:
            await self._incoming_send.send(msg)  # type: ignore[union-attr]
        except anyio.BrokenResourceError:
            pass

    async def _stdout_reader(self) -> None:
        """Read server stdout and route JSON-RPC messages with version-aware batch support."""
        try:
            assert self.process and self.process.stdout

            buffer = ""
            logger.debug("stdout_reader started")

            async for chunk in self.process.stdout:
                # Handle both bytes and string chunks
                if isinstance(chunk, bytes):
                    buffer += chunk.decode("utf-8")
                else:
                    buffer += chunk

                # Split on newlines
                lines = buffer.split("\n")
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
            logger.warning(
                f"Rejecting batch message in protocol version {self.batch_processor.protocol_version}"
            )

            # Send error response back to server
            error_response = self.batch_processor.create_batch_rejection_error()
            await self._send_error_response(error_response)
            return

        # Handle JSON-RPC batch messages (if supported by version)
        if isinstance(data, list):
            if self.batch_processor.batching_enabled:
                logger.debug(
                    f"Processing batch with {len(data)} messages (protocol: {self.batch_processor.protocol_version})"
                )
                for item in data:
                    try:
                        # Import parse_message to handle unions properly
                        from chuk_mcp.protocol.messages.json_rpc_message import (
                            parse_message,
                        )

                        msg = parse_message(item)  # type: ignore[arg-type]
                        await self._route_message(msg)  # type: ignore[arg-type]
                        msg_method = getattr(msg, "method", None)
                        msg_id = getattr(msg, "id", None)
                        logger.debug(
                            f"Batch item: {msg_method or 'response'} (id: {msg_id})"
                        )
                    except Exception as exc:
                        logger.error("Error processing batch item: %s", exc)
                        logger.debug("Invalid batch item: %.120s", json.dumps(item))
            else:
                # This should not happen as we check can_process_batch above
                logger.error(
                    f"Unexpected batch message in version {self.batch_processor.protocol_version}"
                )
        else:
            # Single message
            try:
                # Import parse_message to handle unions properly
                from chuk_mcp.protocol.messages.json_rpc_message import parse_message

                msg = parse_message(data)  # type: ignore[arg-type]
                await self._route_message(msg)  # type: ignore[arg-type]
                msg_method = getattr(msg, "method", None)
                msg_id = getattr(msg, "id", None)
                logger.debug(f"Received: {msg_method or 'response'} (id: {msg_id})")
            except Exception as exc:
                logger.error("Error processing single message: %s", exc)

    async def _send_error_response(self, error_response: Dict) -> None:
        """Send an error response back to the server."""
        try:
            if self.process and self.process.stdin:
                json_str = json.dumps(error_response)
                await self.process.stdin.send(f"{json_str}\n".encode())
                logger.debug(
                    f"Sent error response: {error_response.get('error', {}).get('message', 'Unknown error')}"
                )
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")

    async def _stdin_writer(self) -> None:
        """Forward outgoing JSON-RPC messages to the server's stdin.

        PERFORMANCE OPTIMIZED:
        - Fast-path type checking using isinstance() before hasattr()
        - Direct model_dump_json() call (single pass) instead of model_dump() → json.dumps() (two passes)
        - Cached method lookups to avoid repeated attribute access
        """
        self._ensure_streams_initialized()

        try:
            assert self.process and self.process.stdin
            logger.debug("stdin_writer started")

            async for message in self._outgoing_recv:  # type: ignore[union-attr]
                try:
                    # PERFORMANCE: Fast-path checks using isinstance() before hasattr()
                    # This avoids expensive attribute lookups for common types

                    if isinstance(message, str):
                        # Raw string message (already JSON)
                        json_str = message
                        msg_method = None
                        msg_id = None
                    elif isinstance(message, dict):
                        # Plain dict - serialize directly (common case)
                        json_str = json.dumps(message)
                        msg_method = message.get("method")
                        msg_id = message.get("id")
                    else:
                        # PERFORMANCE: Cache method lookups to avoid repeated hasattr() calls
                        model_dump_json_method = getattr(
                            message, "model_dump_json", None
                        )

                        if model_dump_json_method is not None:
                            # Pydantic model - use direct model_dump_json (FAST: single pass)
                            json_str = model_dump_json_method(exclude_none=True)
                        else:
                            model_dump_method = getattr(message, "model_dump", None)
                            if model_dump_method is not None:
                                # Fallback: model_dump then json.dumps (SLOWER: two passes)
                                # This path should be rare in practice
                                json_str = json.dumps(
                                    model_dump_method(exclude_none=True)
                                )
                            else:
                                # Last resort: try to serialize as-is
                                json_str = json.dumps(message)

                        # Cache attribute access for logging
                        msg_method = getattr(message, "method", None)
                        msg_id = getattr(message, "id", None)

                    # Send the JSON string
                    await self.process.stdin.send(f"{json_str}\n".encode())

                    # Enhanced logging for debugging (optimized attribute access)
                    if msg_method is not None:
                        if msg_id is not None:
                            logger.debug(
                                f"Sent: {msg_method or 'response'} (id: {msg_id})"
                            )
                        else:
                            logger.debug(f"Sent notification: {msg_method}")
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
        send_s: MemoryObjectSendStream
        recv_s: MemoryObjectReceiveStream
        send_s, recv_s = anyio.create_memory_object_stream(1)
        self._pending[req_id] = send_s
        return recv_s

    async def send_json(self, msg: JSONRPCMessage) -> None:
        """
        Queue *msg* for transmission.
        """
        self._ensure_streams_initialized()

        try:
            # Ensure the message is properly queued - no pre-serialization here
            await self._outgoing_send.send(msg)  # type: ignore[union-attr]
        except anyio.BrokenResourceError:
            logger.warning("Cannot send message - outgoing stream is closed")

    # ------------------------------------------------------------------ #
    # New API for stdio_client context manager
    # ------------------------------------------------------------------ #
    def get_streams(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get the read and write streams for communication."""
        self._ensure_streams_initialized()
        return self._incoming_recv, self._outgoing_send  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Version information methods
    # ------------------------------------------------------------------ #
    def get_protocol_version(self) -> Optional[str]:
        """Get the current protocol version."""
        return self.batch_processor.protocol_version

    def is_batching_enabled(self) -> bool:
        """Check if batching is currently enabled."""
        return self.batch_processor.batching_enabled

    def get_batching_info(self) -> Dict[str, Any]:
        """Get information about batching support."""
        return {
            "protocol_version": self.batch_processor.protocol_version,
            "batching_enabled": self.batch_processor.batching_enabled,
            "supports_batch_function": supports_batching(
                self.batch_processor.protocol_version
            ),
        }

    # ------------------------------------------------------------------ #
    # async context-manager interface
    # ------------------------------------------------------------------ #
    async def __aenter__(self):
        try:
            # FIXED: Create streams here in async context, not in __init__
            logger.debug("Creating memory streams in async context...")

            # Global broadcast stream for notifications (id == None)
            self._notify_send, self.notifications = anyio.create_memory_object_stream(
                100
            )

            # Main communication streams
            self._incoming_send, self._incoming_recv = (
                anyio.create_memory_object_stream(100)
            )
            self._outgoing_send, self._outgoing_recv = (
                anyio.create_memory_object_stream(100)
            )

            self._streams_initialized = True
            logger.debug("Memory streams created successfully")

            # Determine stderr handling based on LOG_LEVEL in subprocess environment
            # If LOG_LEVEL is ERROR or higher, suppress subprocess stderr
            import subprocess

            env = self.server.env or get_default_environment()

            # Check LOG_LEVEL in the environment being passed to subprocess
            log_level = env.get("LOG_LEVEL", "").upper()
            logging_level = env.get("LOGGING_LEVEL", "").upper()

            # Suppress stderr if LOG_LEVEL or LOGGING_LEVEL is set to ERROR or CRITICAL
            suppress_stderr = log_level in ("ERROR", "CRITICAL") or logging_level in (
                "ERROR",
                "CRITICAL",
            )

            self.process = await anyio.open_process(
                [self.server.command, *self.server.args],
                env=env,
                stderr=subprocess.DEVNULL if suppress_stderr else sys.stderr,
                start_new_session=True,
            )
            logger.debug(
                "Subprocess PID %s (%s) [stderr: %s]",
                self.process.pid,
                self.server.command,
                "suppressed" if suppress_stderr else "pass-through",
            )

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
            if self._outgoing_send:
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
                                logger.debug(
                                    f"Cancel scope issue during shutdown (expected): {exc}"
                                )
                            elif "json object must be str" in error_msg.lower():
                                # JSON serialization errors are actual bugs
                                logger.error(
                                    f"JSON serialization error during shutdown: {exc}"
                                )
                            else:
                                # Only real errors should be logged as ERROR
                                logger.error(f"Task error during shutdown: {exc}")

                except Exception as e:
                    # Handle regular exceptions for older anyio versions
                    if not isinstance(e, anyio.get_cancelled_exc_class()):
                        error_msg = str(e)
                        if "cancel scope" in error_msg.lower():
                            # CRITICAL: Log cancel scope issues as DEBUG, not ERROR
                            logger.debug(
                                f"Cancel scope issue during shutdown (expected): {e}"
                            )
                        elif "json object must be str" in error_msg.lower():
                            # JSON serialization errors are actual bugs
                            logger.error(
                                f"JSON serialization error during shutdown: {e}"
                            )
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
                    logger.debug("Graceful term timed out - killing …")
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
async def stdio_client(
    server: StdioParameters,
) -> AsyncGenerator[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream], None]:
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
                    logger.debug(
                        f"stdio_client cancel scope issue (expected during shutdown): {exc}"
                    )
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
                logger.debug(
                    f"stdio_client cancel scope issue (expected during shutdown): {e}"
                )
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
    from chuk_mcp.protocol.messages.initialize.send_messages import (
        send_initialize_with_client_tracking,
    )

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
                    logger.debug(
                        f"stdio_client_with_initialize cancel scope issue (expected): {exc}"
                    )
                elif "json object must be str" in error_msg.lower():
                    logger.error(
                        f"JSON serialization error in stdio_client_with_initialize: {exc}"
                    )
                    raise  # Re-raise JSON errors as they indicate bugs
                else:
                    logger.error(f"stdio_client_with_initialize error: {exc}")
                    raise  # Re-raise non-cancel-scope errors
    except Exception as e:
        # Handle regular exceptions
        if not isinstance(e, anyio.get_cancelled_exc_class()):
            error_msg = str(e)
            if "cancel scope" in error_msg.lower():
                logger.debug(
                    f"stdio_client_with_initialize cancel scope issue (expected): {e}"
                )
            elif "json object must be str" in error_msg.lower():
                logger.error(
                    f"JSON serialization error in stdio_client_with_initialize: {e}"
                )
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
        stacklevel=2,
    )
    return supports_batching(protocol_version)
