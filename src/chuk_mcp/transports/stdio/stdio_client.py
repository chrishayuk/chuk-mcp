# chuk_mcp/transports/stdio/stdio_client.py
import json
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple, List

import anyio
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

# Import from the correct locations for the new structure
from chuk_mcp.mcp_client.host.environment import get_default_environment
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
from .parameters import StdioParameters

__all__ = ["StdioClient", "stdio_client", "stdio_client_with_initialize"]


def _supports_batch_processing(protocol_version: Optional[str]) -> bool:
    """
    Check if the protocol version supports JSON-RPC batch processing.
    
    Batch processing was removed in version 2025-06-18.
    
    Args:
        protocol_version: The negotiated protocol version
        
    Returns:
        True if batch processing is supported, False otherwise
    """
    if not protocol_version:
        # Default to supporting batch for backward compatibility
        return True
    
    # Parse version and check if it's before 2025-06-18
    try:
        # Versions are in YYYY-MM-DD format, but be flexible with zero-padding
        version_parts = protocol_version.split('-')
        
        # We need exactly 3 parts for a valid version
        if len(version_parts) != 3:
            # Treat versions with extra parts as invalid/malformed
            raise ValueError("Invalid version format")
            
        year = int(version_parts[0])
        month = int(version_parts[1])
        day = int(version_parts[2])
        
        # 2025-06-18 and later don't support batching
        if year > 2025:
            return False
        elif year == 2025 and month > 6:
            return False
        elif year == 2025 and month == 6 and day >= 18:
            return False
            
        # All earlier versions support batching
        return True
    except (ValueError, TypeError, IndexError):
        # If we can't parse the version, default to supporting batch
        logging.warning(f"Could not parse protocol version '{protocol_version}', assuming batch support")
        return True


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
        
        # Track negotiated protocol version for feature support
        self._protocol_version: Optional[str] = None

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        self._protocol_version = version
        logging.debug(f"Protocol version set to: {version}")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    
    # Performance-optimized version with minimal logging
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
            logging.debug(f"Received message for unknown id: {msg.id}")

    async def _stdout_reader(self) -> None:
        """Read server stdout and route JSON-RPC messages with version-aware batch support."""
        try:
            assert self.process and self.process.stdout

            buffer = ""
            logging.debug("stdout_reader started")

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
                        
                        # Handle JSON-RPC batch messages only if version supports it
                        if isinstance(data, list) and _supports_batch_processing(self._protocol_version):
                            # Process each message in the batch
                            logging.debug(f"Received batch with {len(data)} messages (protocol: {self._protocol_version})")
                            for item in data:
                                try:
                                    msg = JSONRPCMessage.model_validate(item)
                                    await self._route_message(msg)
                                    logging.debug(f"Batch item: {msg.method or 'response'} (id: {msg.id})")
                                except Exception as exc:
                                    logging.error("Error processing batch item: %s", exc)
                                    logging.debug("Invalid batch item: %.120s", json.dumps(item))
                        elif isinstance(data, list):
                            # Batch received but not supported in this protocol version
                            logging.warning(f"Received batch message but protocol version {self._protocol_version} does not support batching")
                            # Try to process individual items anyway for compatibility
                            for item in data:
                                try:
                                    msg = JSONRPCMessage.model_validate(item)
                                    await self._route_message(msg)
                                    logging.debug(f"Individual item from unsupported batch: {msg.method or 'response'} (id: {msg.id})")
                                except Exception as exc:
                                    logging.error("Error processing item from unsupported batch: %s", exc)
                        else:
                            # Single message
                            msg = JSONRPCMessage.model_validate(data)
                            await self._route_message(msg)
                            logging.debug(f"Received: {msg.method or 'response'} (id: {msg.id})")
                            
                    except json.JSONDecodeError as exc:
                        logging.error("JSON decode error: %s  [line: %.120s]", exc, line)
                    except Exception as exc:
                        logging.error("Error processing message: %s", exc)
                        logging.debug("Traceback:\n%s", traceback.format_exc())

            logging.debug("stdout_reader exiting")
        except Exception as e:
            logging.error(f"stdout_reader error: {e}")
            logging.debug("Traceback:\n%s", traceback.format_exc())
            

    async def _stdin_writer(self) -> None:
        """Forward outgoing JSON-RPC messages to the server's stdin."""
        try:
            assert self.process and self.process.stdin
            logging.debug("stdin_writer started")

            async for message in self._outgoing_recv:
                try:
                    json_str = (
                        message
                        if isinstance(message, str)
                        else message.model_dump_json(exclude_none=True)
                    )
                    await self.process.stdin.send(f"{json_str}\n".encode())
                    logging.debug(f"Sent: {message.method or 'response'} (id: {message.id})")
                except Exception as exc:
                    logging.error("Unexpected error in stdin_writer: %s", exc)
                    logging.debug("Traceback:\n%s", traceback.format_exc())
                    continue

            logging.debug("stdin_writer exiting; closing server stdin")
            if self.process and self.process.stdin:
                await self.process.stdin.aclose()
        except Exception as e:
            logging.error(f"stdin_writer error: {e}")
            logging.debug("Traceback:\n%s", traceback.format_exc())

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
            await self._outgoing_send.send(msg)
        except anyio.BrokenResourceError:
            logging.warning("Cannot send message - outgoing stream is closed")

    # ------------------------------------------------------------------ #
    # New API for stdio_client context manager
    # ------------------------------------------------------------------ #
    def get_streams(self) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get the read and write streams for communication."""
        return self._incoming_recv, self._outgoing_send

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
            logging.debug("Subprocess PID %s (%s)", self.process.pid, self.server.command)

            self.tg = anyio.create_task_group()
            await self.tg.__aenter__()
            self.tg.start_soon(self._stdout_reader)
            self.tg.start_soon(self._stdin_writer)

            return self
        except Exception as e:
            logging.error(f"Error starting stdio client: {e}")
            raise

    async def __aexit__(self, exc_type, exc, tb):
        try:
            # Close outgoing stream to signal stdin_writer to exit
            await self._outgoing_send.aclose()
            
            if self.tg:
                # Cancel all tasks
                self.tg.cancel_scope.cancel()
                
                # Handle task group exceptions properly
                try:
                    await self.tg.__aexit__(None, None, None)
                except BaseExceptionGroup as eg:
                    # Handle exception groups from anyio
                    for exc in eg.exceptions:
                        if not isinstance(exc, anyio.get_cancelled_exc_class()):
                            logging.error(f"Task error during shutdown: {exc}")
                except Exception as e:
                    # Handle regular exceptions for older anyio versions
                    if not isinstance(e, anyio.get_cancelled_exc_class()):
                        logging.error(f"Task error during shutdown: {e}")
                
            if self.process and self.process.returncode is None:
                await self._terminate_process()
                
        except Exception as e:
            logging.error(f"Error during stdio client shutdown: {e}")
            
        return False

    async def _terminate_process(self) -> None:
        """Terminate the helper process gracefully, then force-kill if needed."""
        if not self.process:
            return
        try:
            if self.process.returncode is None:
                logging.debug("Terminating subprocess…")
                self.process.terminate()
                try:
                    with anyio.fail_after(5):
                        await self.process.wait()
                except TimeoutError:
                    logging.warning("Graceful term timed out – killing …")
                    self.process.kill()
                    with anyio.fail_after(5):
                        await self.process.wait()
        except Exception as e:
            logging.error(f"Error during process termination: {e}")
            logging.debug("Traceback:\n%s", traceback.format_exc())


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
        # Handle exception groups from anyio task groups
        for exc in eg.exceptions:
            if not isinstance(exc, anyio.get_cancelled_exc_class()):
                logging.error(f"stdio_client error: {exc}")
        raise
    except Exception as e:
        # Handle regular exceptions
        if not isinstance(e, anyio.get_cancelled_exc_class()):
            logging.error(f"stdio_client error: {e}")
        raise


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
        # Handle exception groups from anyio task groups
        for exc in eg.exceptions:
            if not isinstance(exc, anyio.get_cancelled_exc_class()):
                logging.error(f"stdio_client_with_initialize error: {exc}")
        raise
    except Exception as e:
        # Handle regular exceptions
        if not isinstance(e, anyio.get_cancelled_exc_class()):
            logging.error(f"stdio_client_with_initialize error: {e}")
        raise