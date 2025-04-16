# chuk_mcp/mcp_client/transport/stdio/stdio_client.py
import json
import logging
import sys
import traceback
from contextlib import asynccontextmanager

import anyio
from anyio.streams.text import TextReceiveStream

# host imports
from chuk_mcp.mcp_client.host.environment import get_default_environment

# mcp imports
from chuk_mcp.mcp_client.messages.json_rpc_message import JSONRPCMessage
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import (
    StdioServerParameters,
)


class StdioClient:
    """
    A lightweight stdio JSON‑RPC client that launches a helper server as a
    subprocess and shuttles messages back and forth over stdin/stdout.

    The helper process is now started with `start_new_session=True` so it no
    longer receives SIGINT when the user presses Ctrl‑C in the parent CLI.
    """

    def __init__(self, server: StdioServerParameters):
        if not server.command:
            raise ValueError("Server command must not be empty.")
        if not isinstance(server.args, (list, tuple)):
            raise ValueError("Server arguments must be a list or tuple.")

        self.server = server

        # in‑memory object streams are enough for our use‑case
        self.read_stream_writer, self.read_stream = anyio.create_memory_object_stream(0)
        self.write_stream, self.write_stream_reader = anyio.create_memory_object_stream(
            0
        )

        self.process: anyio.abc.Process | None = None
        self.tg: anyio.abc.TaskGroup | None = None

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    async def _process_json_line(self, line: str) -> None:
        try:
            data = json.loads(line)
            message = JSONRPCMessage.model_validate(data)
            await self.read_stream_writer.send(message)
        except json.JSONDecodeError as exc:
            logging.error("JSON decode error: %s  [line: %s]", exc, line.strip())
        except Exception as exc:
            logging.error("Error processing message: %s", exc)
            logging.debug("Traceback:\n%s", traceback.format_exc())

    async def _stdout_reader(self) -> None:
        """Read JSON‑RPC messages from the server's stdout."""
        assert self.process and self.process.stdout

        buffer = ""
        logging.debug("stdout_reader started")
        try:
            async with self.read_stream_writer:
                async for chunk in TextReceiveStream(self.process.stdout):
                    lines = (buffer + chunk).split("\n")
                    buffer = lines.pop()
                    for line in lines:
                        if line.strip():
                            await self._process_json_line(line)
                if buffer.strip():
                    await self._process_json_line(buffer)
        except anyio.ClosedResourceError:
            logging.debug("Read stream closed.")
        except Exception:
            logging.error("Unexpected error in stdout_reader")
            logging.debug("Traceback:\n%s", traceback.format_exc())
            raise
        finally:
            logging.debug("stdout_reader exiting")

    async def _stdin_writer(self) -> None:
        """Forward outgoing JSON‑RPC messages to the server's stdin."""
        assert self.process and self.process.stdin

        logging.debug("stdin_writer started")
        try:
            async with self.write_stream_reader:
                async for message in self.write_stream_reader:
                    json_str = (
                        message
                        if isinstance(message, str)
                        else message.model_dump_json(exclude_none=True)
                    )
                    await self.process.stdin.send(f"{json_str}\n".encode())
        except anyio.ClosedResourceError:
            logging.debug("Write stream closed.")
        except Exception:
            logging.error("Unexpected error in stdin_writer")
            logging.debug("Traceback:\n%s", traceback.format_exc())
            raise
        finally:
            logging.debug("stdin_writer exiting")

    async def _terminate_process(self) -> None:
        """Terminate the subprocess gracefully, then force‑kill if needed."""
        if self.process is None:
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

    # ------------------------------------------------------------------ #
    # async context‑manager interface
    # ------------------------------------------------------------------ #
    async def __aenter__(self):
        # Launch helper in its *own* session so Ctrl‑C in the parent CLI
        # doesn’t interrupt the child.
        self.process = await anyio.open_process(
            [self.server.command, *self.server.args],
            env=self.server.env or get_default_environment(),
            stderr=sys.stderr,
            start_new_session=True,  # ← critical line: detach from tty SIGINT
        )
        logging.debug("Subprocess PID %s (%s)", self.process.pid, self.server.command)

        # Start background I/O tasks
        self.tg = anyio.create_task_group()
        await self.tg.__aenter__()
        self.tg.start_soon(self._stdout_reader)
        self.tg.start_soon(self._stdin_writer)

        return self.read_stream, self.write_stream

    async def __aexit__(self, exc_type, exc, tb):
        if self.tg is not None:
            self.tg.cancel_scope.cancel()
            try:
                await self.tg.__aexit__(None, None, None)
            except RuntimeError as re:
                if "Attempted to exit cancel scope" in str(re):
                    logging.debug("Suppressed cancel‑scope RuntimeError: %s", re)
                else:
                    raise
        await self._terminate_process()
        return False


# ---------------------------------------------------------------------- #
# Public convenience context‑manager
# ---------------------------------------------------------------------- #
@asynccontextmanager
async def stdio_client(server: StdioServerParameters):
    """
    Usage:
        async with stdio_client(server_params) as (read_stream, write_stream):
            ...
    """
    client = StdioClient(server)
    try:
        yield await client.__aenter__()
    finally:
        await client.__aexit__(None, None, None)