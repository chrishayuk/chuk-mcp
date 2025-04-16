# chuk_mcp/mcp_client/transport/stdio/stdio_client.py
# chuk_mcp/mcp_client/transport/stdio/stdio_client.py
import json
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional

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

    Features:
      * **Router**: per‑request queues so responses never get “stolen”.
      * **Robust line parsing** via simple chunk buffering.
      * **Resilient writer**: per‑message errors are logged and swallowed.
    """

    def __init__(self, server: StdioServerParameters):
        if not server.command:
            raise ValueError("Server command must not be empty.")
        if not isinstance(server.args, (list, tuple)):
            raise ValueError("Server arguments must be a list or tuple.")

        self.server = server

        # Global broadcast stream for notifications (id == None)
        self._notify_send: MemoryObjectSendStream
        self.notifications: MemoryObjectReceiveStream
        self._notify_send, self.notifications = anyio.create_memory_object_stream(0)

        # Per‑request streams; key = request id
        self._pending: Dict[str, MemoryObjectSendStream] = {}

        self.process: Optional[anyio.abc.Process] = None
        self.tg: Optional[anyio.abc.TaskGroup] = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    async def _route_message(self, msg: JSONRPCMessage) -> None:
        if msg.id is None:
            # notification → broadcast
            await self._notify_send.send(msg)
            return

        send_stream = self._pending.pop(msg.id, None)
        if send_stream:
            await send_stream.send(msg)
            await send_stream.aclose()
        else:
            logging.warning("Received response with unknown id: %s", msg.id)

    async def _stdout_reader(self) -> None:
        """Read server stdout and route JSON‑RPC messages via simple buffering."""
        assert self.process and self.process.stdout

        buffer = ""
        logging.debug("stdout_reader started")

        # Directly consume whatever async iterator stdout provides
        async for chunk in self.process.stdout:
            buffer += chunk

            # Split on any newline variant
            for line in buffer.splitlines(keepends=False):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    msg = JSONRPCMessage.model_validate(data)
                    await self._route_message(msg)
                except json.JSONDecodeError as exc:
                    logging.error("JSON decode error: %s  [line: %.120s]", exc, line)
                except Exception as exc:
                    logging.error("Error processing message: %s", exc)
                    logging.debug("Traceback:\n%s", traceback.format_exc())

            # Retain any trailing incomplete fragment
            if buffer and not buffer.endswith(("\n", "\r")):
                buffer = buffer.rsplit("\n", 1)[-1]
            else:
                buffer = ""

        logging.debug("stdout_reader exiting")

    async def _stdin_writer(self) -> None:
        """Forward outgoing JSON‑RPC messages to the server's stdin."""
        assert self.process and self.process.stdin
        logging.debug("stdin_writer started")

        # _client_out yields (req_id, message) pairs
        async for req_id, message in self._client_out():
            try:
                json_str = (
                    message
                    if isinstance(message, str)
                    else message.model_dump_json(exclude_none=True)
                )
                await self.process.stdin.send(f"{json_str}\n".encode())
            except Exception as exc:
                logging.error("Unexpected error in stdin_writer: %s", exc)
                logging.debug("Traceback:\n%s", traceback.format_exc())
                # swallow and continue
                continue

        logging.debug("stdin_writer exiting; closing server stdin")
        await self.process.stdin.aclose()

    async def _client_out(self):
        """
        Internal generator stub: yields (req_id, JSONRPCMessage or str).
        Replace with your own queuing mechanism.
        """
        # Block forever by default
        await anyio.sleep(1e9)
        if False:
            yield ("", "")

    # ------------------------------------------------------------------ #
    # Public API for request lifecycle
    # ------------------------------------------------------------------ #
    def new_request_stream(self, req_id: str) -> MemoryObjectReceiveStream:
        """
        Create a one‑shot receive stream for *req_id*.
        The caller can await .receive() to get the JSONRPCMessage.
        """
        send_s, recv_s = anyio.create_memory_object_stream(1)
        self._pending[req_id] = send_s
        return recv_s

    async def send_json(self, msg: JSONRPCMessage) -> None:
        """
        Queue *msg* for transmission.
        Under the hood you need to pump it into _client_out.
        """
        send_s, _ = anyio.create_memory_object_stream(1)
        await send_s.send((msg.id, msg))
        await send_s.aclose()

    # ------------------------------------------------------------------ #
    # async context‑manager interface
    # ------------------------------------------------------------------ #
    async def __aenter__(self):
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

    async def __aexit__(self, exc_type, exc, tb):
        if self.tg:
            self.tg.cancel_scope.cancel()
            await self.tg.__aexit__(None, None, None)
        if self.process and self.process.returncode is None:
            await self._terminate_process()
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
        except Exception:
            logging.error("Error during process termination")
            logging.debug("Traceback:\n%s", traceback.format_exc())


# ---------------------------------------------------------------------- #
# Convenience context‑manager                                           #
# ---------------------------------------------------------------------- #
@asynccontextmanager
async def stdio_client(server: StdioServerParameters):
    """
    Usage:
        async with stdio_client(server_params) as client:
            # client is a StdioClient instance
    """
    client = StdioClient(server)
    try:
        yield await client.__aenter__()
    finally:
        await client.__aexit__(None, None, None)
