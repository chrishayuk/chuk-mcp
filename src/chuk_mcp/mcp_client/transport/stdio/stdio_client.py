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
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import (
    StdioServerParameters,
)

__all__ = ["StdioClient", "stdio_client"]


class StdioClient:
    """
    A newline‑delimited JSON‑RPC client speaking over stdio to a subprocess.

    - Maintains `self.notifications` for notifications (id=None).
    - Per-request streams via `new_request_stream`.
    - Robust CRLF-normalized line splitting.
    - _stdin_writer pulls from `self._client_out()` (a stub you can override).
    """

    def __init__(self, server: StdioServerParameters):
        if not server.command:
            raise ValueError("Server command must not be empty.")
        if not isinstance(server.args, (list, tuple)):
            raise ValueError("Server arguments must be a list or tuple.")

        self.server = server

        # Notification broadcast stream (id == None)
        self._notify_send: MemoryObjectSendStream
        self.notifications: MemoryObjectReceiveStream
        self._notify_send, self.notifications = anyio.create_memory_object_stream(0)

        # Per-request pending response streams
        self._pending: Dict[str, MemoryObjectSendStream] = {}

        # Placeholder for writing
        self.process: Optional[anyio.abc.Process] = None
        self.tg: Optional[anyio.abc.TaskGroup] = None

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _route_message(self, msg: JSONRPCMessage) -> None:
        # Notifications
        if msg.id is None:
            await self._notify_send.send(msg)
            return

        # Matched responses
        send_stream = self._pending.pop(msg.id, None)
        if send_stream:
            await send_stream.send(msg)
            await send_stream.aclose()
        else:
            logging.warning("Received response with unknown id: %s", msg.id)

    async def _stdout_reader(self) -> None:
        """
        Read lines from process.stdout (async iterator of str or bytes),
        normalize CRLF, split on '\n', and route valid JSON‑RPC messages.
        """
        assert self.process and self.process.stdout
        buffer = ""
        try:
            async for chunk in self.process.stdout:
                # Accept either str or bytes
                if isinstance(chunk, (bytes, bytearray)):
                    chunk = chunk.decode()
                # Normalize CRLF → LF
                chunk = chunk.replace("\r\n", "\n")
                buffer += chunk

                # Process all complete lines
                lines = buffer.split("\n")
                # Keep last fragment in buffer if no trailing '\n'
                if buffer.endswith("\n"):
                    to_process, buffer = lines, ""
                else:
                    to_process, buffer = lines[:-1], lines[-1]

                for line in to_process:
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
        except Exception:
            logging.error("Unexpected error in stdout_reader")
            logging.debug("Traceback:\n%s", traceback.format_exc())
            raise

    async def _stdin_writer(self) -> None:
        """
        Pull (req_id, message) pairs from self._client_out(),
        serialize to JSON (or pass raw string), and send to stdin.
        Per‑message errors are logged and swallowed.
        """
        assert self.process and self.process.stdin
        logging.debug("stdin_writer started")
        try:
            async for req_id, message in self._client_out():
                try:
                    json_str = message if isinstance(message, str) else message.model_dump_json(exclude_none=True)
                    await self.process.stdin.send(f"{json_str}\n".encode())
                except Exception:
                    logging.error("Unexpected error in stdin_writer")
                    logging.debug("Traceback:\n%s", traceback.format_exc())
                    # swallow and continue
        finally:
            logging.debug("stdin_writer exiting; closing server stdin")
            # ensure the subprocess sees EOF on its stdin
            await self.process.stdin.aclose()

    async def _client_out(self):
        """
        Stub generator for outgoing messages.
        Tests can monkey‑patch `self._client_out = my_async_gen`.
        """
        await anyio.sleep(1e9)
        if False:
            yield ("", "")  # pragma: no cover

    # ─── Public API ────────────────────────────────────────────────────────────

    def new_request_stream(self, req_id: str) -> MemoryObjectReceiveStream:
        """
        Returns a 1‑slot receive stream for the given request ID.
        Use `await stream.receive()` to get your JSONRPCMessage.
        """
        send_s, recv_s = anyio.create_memory_object_stream(1)
        self._pending[req_id] = send_s
        return recv_s

    # ─── Async context‑manager ──────────────────────────────────────────────────

    async def __aenter__(self) -> "StdioClient":
        self.process = await anyio.open_process(
            [self.server.command, *self.server.args],
            env=self.server.env or get_default_environment(),
            stderr=sys.stderr,
            start_new_session=True,
        )
        # Kick off I/O tasks
        self.tg = anyio.create_task_group()
        await self.tg.__aenter__()
        self.tg.start_soon(self._stdout_reader)
        self.tg.start_soon(self._stdin_writer)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self.tg:
            self.tg.cancel_scope.cancel()
            await self.tg.__aexit__(None, None, None)
        if self.process and self.process.returncode is None:
            await self._terminate_process()
        return False

    async def _terminate_process(self) -> None:
        """Gracefully terminate the subprocess, then kill on timeout."""
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


@asynccontextmanager
async def stdio_client(server: StdioServerParameters):
    """
    Convenience wrapper:

        async with stdio_client(params) as client:
            # client is a StdioClient instance
    """
    client = StdioClient(server)
    await client.__aenter__()
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)
