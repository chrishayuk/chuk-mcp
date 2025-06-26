# chuk_mcp/mcp_client/transport/stdio/stdio_client.py
import json
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple

import anyio
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

# host imports
from chuk_mcp.mcp_client.host.environment import get_default_environment

# mcp imports
from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

__all__ = ["StdioClient", "stdio_client"]


class StdioClient:
    """
    A newline‑delimited JSON‑RPC client speaking over stdio to a subprocess.

    Maintains compatibility with existing tests while providing working
    message transmission functionality.
    """

    def __init__(self, server: StdioServerParameters):
        if not server.command:
            raise ValueError("Server command must not be empty.")
        if not isinstance(server.args, (list, tuple)):
            raise ValueError("Server arguments must be a list or tuple.")

        self.server = server

        # Global broadcast stream for notifications (id == None) - use buffer to prevent deadlock
        self._notify_send: MemoryObjectSendStream
        self.notifications: MemoryObjectReceiveStream
        self._notify_send, self.notifications = anyio.create_memory_object_stream(100)

        # Per‑request streams; key = request id - for test compatibility
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

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    async def _route_message(self, msg: JSONRPCMessage) -> None:
        """Route messages for both new stream API and old request-specific API."""
        # Send to main incoming stream for stdio_client() context manager
        try:
            await self._incoming_send.send(msg)
        except anyio.BrokenResourceError:
            pass  # Stream might be closed during shutdown

        # Route for legacy API compatibility
        if msg.id is None:
            # notification → broadcast - use nowait to avoid blocking
            try:
                self._notify_send.send_nowait(msg)
            except (anyio.WouldBlock, anyio.BrokenResourceError):
                # If buffer is full or stream is closed, drop the notification
                logging.debug("Dropped notification due to full buffer or closed stream")
            return

        # Response to specific request
        send_stream = self._pending.pop(str(msg.id), None)
        if send_stream:
            try:
                await send_stream.send(msg)
                await send_stream.aclose()
            except anyio.BrokenResourceError:
                pass
        else:
            logging.warning("Received response with unknown id: %s", msg.id)

    async def _stdout_reader(self) -> None:
        """Read server stdout and route JSON-RPC messages with batch support."""
        try:
            assert self.process and self.process.stdout

            buffer = ""
            logging.debug("stdout_reader started")

            async for chunk in self.process.stdout:
                buffer += chunk

                # Split on newlines
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line
                
                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        
                        # Handle JSON-RPC batch messages (MUST support per spec)
                        if isinstance(data, list):
                            # Process each message in the batch
                            logging.debug(f"Received batch with {len(data)} messages")
                            for item in data:
                                try:
                                    msg = JSONRPCMessage.model_validate(item)
                                    await self._route_message(msg)
                                    logging.debug(f"Batch item: {msg.method or 'response'} (id: {msg.id})")
                                except Exception as exc:
                                    logging.error("Error processing batch item: %s", exc)
                                    logging.debug("Invalid batch item: %.120s", json.dumps(item))
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
        """Forward outgoing JSON‑RPC messages to the server's stdin."""
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
        Create a one‑shot receive stream for *req_id*.
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
    # async context‑manager interface
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
        """Terminate the helper process gracefully, then force‑kill if needed."""
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
# Convenience context‑manager that returns streams for send_message
# ---------------------------------------------------------------------- #
@asynccontextmanager
async def stdio_client(server: StdioServerParameters) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
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