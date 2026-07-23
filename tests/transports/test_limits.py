# tests/transports/test_limits.py
"""
Tests for transport buffer-size limits.

A malicious or compromised MCP server can withhold the newline that delimits a
message and stream indefinitely. These tests pin the cap that stops each
transport from accumulating that data without bound.
"""

import json
import logging

import pytest

from chuk_mcp.transports.limits import (
    DEFAULT_MAX_BUFFER_SIZE,
    MessageTooLargeError,
    aread_text_bounded,
    check_buffer_size,
    resolve_max_buffer_size,
)


def _max_chunks(limit: int, chunk_len: int) -> int:
    """First chunk count at which accumulated bytes exceed ``limit``."""
    return limit // chunk_len + 1


class _FakeStreamingResponse:
    """Minimal stand-in for a streaming httpx response."""

    def __init__(self, chunk: bytes, repeat: int, encoding: str = "utf-8"):
        self._chunk = chunk
        self._repeat = repeat
        self.encoding = encoding
        self.chunks_yielded = 0

    async def aiter_bytes(self, chunk_size=None):
        for _ in range(self._repeat):
            self.chunks_yielded += 1
            yield self._chunk


###############################################################################
# Helper-level behaviour
###############################################################################


def test_check_buffer_size_allows_buffer_at_limit():
    check_buffer_size(b"x" * 100, 100)  # must not raise


def test_check_buffer_size_rejects_oversized_buffer():
    with pytest.raises(MessageTooLargeError) as exc:
        check_buffer_size(b"x" * 101, 100, "SSE event")

    assert exc.value.size == 101
    assert exc.value.limit == 100
    assert "SSE event" in str(exc.value)


def test_check_buffer_size_disabled_by_zero():
    check_buffer_size(b"x" * 10_000, 0)  # must not raise


def test_resolve_max_buffer_size_falls_back_to_default():
    class NoAttr:
        pass

    assert resolve_max_buffer_size(NoAttr()) == DEFAULT_MAX_BUFFER_SIZE


def test_resolve_max_buffer_size_honours_parameter():
    class WithAttr:
        max_buffer_size = 4096

    assert resolve_max_buffer_size(WithAttr()) == 4096


def test_resolve_max_buffer_size_rejects_negative():
    """A typo must not silently disable the cap; 0 is the explicit opt-out."""

    class Negative:
        max_buffer_size = -1

    with pytest.raises(ValueError, match="max_buffer_size"):
        resolve_max_buffer_size(Negative())


@pytest.mark.asyncio
async def test_aread_text_bounded_returns_small_body():
    response = _FakeStreamingResponse(b"hello ", repeat=3)
    assert await aread_text_bounded(response, 1024) == "hello hello hello "


@pytest.mark.asyncio
async def test_aread_text_bounded_aborts_before_consuming_everything():
    """The read must stop early rather than buffering the whole hostile body."""
    chunk, limit = b"A" * 100, 500
    response = _FakeStreamingResponse(chunk, repeat=1000)

    with pytest.raises(MessageTooLargeError):
        await aread_text_bounded(response, limit)

    # Aborted after crossing the limit, not after draining all 1000 chunks.
    assert response.chunks_yielded <= _max_chunks(limit, len(chunk))


###############################################################################
# SSE transport
###############################################################################


@pytest.mark.asyncio
async def test_sse_stream_aborts_on_newline_free_stream():
    """A server that never sends a newline must not grow the buffer forever."""
    pytest.importorskip("httpx")
    from chuk_mcp.transports.sse.parameters import SSEParameters
    from chuk_mcp.transports.sse.transport import SSETransport

    chunk, limit = b"A" * 100, 1000
    params = SSEParameters(url="http://localhost:3000", max_buffer_size=limit)
    transport = SSETransport(params)
    response = _FakeStreamingResponse(chunk, repeat=1000)
    transport._sse_response = response

    with pytest.raises(MessageTooLargeError):
        await transport._process_sse_stream()

    assert response.chunks_yielded <= _max_chunks(limit, len(chunk))


@pytest.mark.asyncio
async def test_sse_stream_cap_counts_bytes_not_characters():
    """Multi-byte characters must count at their encoded size, not per character."""
    pytest.importorskip("httpx")
    from chuk_mcp.transports.sse.parameters import SSEParameters
    from chuk_mcp.transports.sse.transport import SSETransport

    # 25 four-byte characters: 100 bytes but only 25 characters per chunk. A
    # character-counting cap would tolerate 4x more chunks before tripping.
    chunk, limit = "\U0001f389".encode("utf-8") * 25, 1000
    params = SSEParameters(url="http://localhost:3000", max_buffer_size=limit)
    transport = SSETransport(params)
    response = _FakeStreamingResponse(chunk, repeat=1000)
    transport._sse_response = response

    with pytest.raises(MessageTooLargeError):
        await transport._process_sse_stream()

    assert response.chunks_yielded <= _max_chunks(limit, len(chunk))


@pytest.mark.asyncio
async def test_sse_stream_still_processes_delimited_events():
    """The cap must not break normal, newline-delimited traffic."""
    pytest.importorskip("httpx")
    from chuk_mcp.transports.sse.parameters import SSEParameters
    from chuk_mcp.transports.sse.transport import SSETransport

    params = SSEParameters(url="http://localhost:3000", max_buffer_size=1000)
    transport = SSETransport(params)
    transport._sse_response = _FakeStreamingResponse(
        b"event: endpoint\ndata: /messages/?session_id=abc\n\n", repeat=1
    )

    await transport._process_sse_stream()

    assert transport._message_url == "http://localhost:3000/messages/?session_id=abc"
    assert transport._session_id == "abc"


def test_sse_parameters_default_cap():
    from chuk_mcp.transports.sse.parameters import SSEParameters

    assert (
        SSEParameters(url="http://localhost:3000").max_buffer_size
        == DEFAULT_MAX_BUFFER_SIZE
    )


###############################################################################
# Streamable HTTP transport
###############################################################################


@pytest.mark.asyncio
async def test_http_sse_response_aborts_on_newline_free_stream():
    pytest.importorskip("httpx")
    import httpx

    from chuk_mcp.transports.http.parameters import StreamableHTTPParameters
    from chuk_mcp.transports.http.transport import StreamableHTTPTransport

    class _UnreadResponse(_FakeStreamingResponse):
        @property
        def text(self):
            raise httpx.ResponseNotRead()

    chunk, limit = b"A" * 100, 1000
    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", max_buffer_size=limit
    )
    transport = StreamableHTTPTransport(params)

    routed = []

    async def _capture(data):
        routed.append(data)

    transport._route_response = _capture  # type: ignore[assignment]

    response = _UnreadResponse(chunk, repeat=1000)
    await transport._process_sse_response(response, "msg-1")  # type: ignore[arg-type]

    # The oversized stream is reported as a JSON-RPC error, not buffered.
    assert len(routed) == 1
    assert "maximum buffered size" in routed[0]["error"]["message"]
    assert response.chunks_yielded <= _max_chunks(limit, len(chunk))


@pytest.mark.asyncio
async def test_http_read_text_bounded_uses_buffered_body_when_available():
    """An already-read response is returned directly, without re-reading."""
    pytest.importorskip("httpx")
    import httpx

    from chuk_mcp.transports.http.parameters import StreamableHTTPParameters
    from chuk_mcp.transports.http.transport import StreamableHTTPTransport

    params = StreamableHTTPParameters(url="http://localhost:3000/mcp")
    transport = StreamableHTTPTransport(params)

    response = httpx.Response(200, content=b'{"jsonrpc":"2.0"}')
    assert await transport._read_text_bounded(response) == '{"jsonrpc":"2.0"}'


def test_http_parameters_default_cap():
    from chuk_mcp.transports.http.parameters import StreamableHTTPParameters

    assert (
        StreamableHTTPParameters(url="http://localhost:3000/mcp").max_buffer_size
        == DEFAULT_MAX_BUFFER_SIZE
    )


###############################################################################
# stdio transport
###############################################################################


class _FakeProcess:
    """Stand-in for an anyio subprocess with a scripted stdout."""

    def __init__(self, *chunks: bytes):
        self.stdout = self._Stdout(chunks)

    class _Stdout:
        def __init__(self, chunks):
            self._chunks = list(chunks)
            self.chunks_yielded = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.chunks_yielded >= len(self._chunks):
                raise StopAsyncIteration
            chunk = self._chunks[self.chunks_yielded]
            self.chunks_yielded += 1
            return chunk


@pytest.mark.asyncio
async def test_stdio_reader_aborts_on_newline_free_output(caplog):
    """A server process that never terminates a line must not grow the buffer."""
    from chuk_mcp.transports.stdio.parameters import StdioParameters
    from chuk_mcp.transports.stdio.stdio_client import StdioClient

    chunk, limit = b"A" * 100, 1000
    client = StdioClient(
        StdioParameters(command="echo", args=[], max_buffer_size=limit)
    )
    process = _FakeProcess(*[chunk] * 1000)
    client.process = process  # type: ignore[assignment]

    with caplog.at_level(logging.ERROR):
        await client._stdout_reader()

    # The reader stops instead of draining all 1000 chunks into memory.
    assert process.stdout.chunks_yielded <= _max_chunks(limit, len(chunk))
    assert any("maximum buffered size" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_stdio_reader_processes_complete_lines_before_aborting(caplog):
    """Delimited messages arriving alongside an oversized remainder still land."""
    from chuk_mcp.transports.stdio.parameters import StdioParameters
    from chuk_mcp.transports.stdio.stdio_client import StdioClient

    message = {"jsonrpc": "2.0", "id": "x", "result": {}}
    chunk = json.dumps(message).encode() + b"\n" + b"A" * 2000

    client = StdioClient(StdioParameters(command="echo", args=[], max_buffer_size=1000))
    client.process = _FakeProcess(chunk)  # type: ignore[assignment]

    processed = []

    async def _capture(data):
        processed.append(data)

    client._process_message_data = _capture  # type: ignore[assignment]

    with caplog.at_level(logging.ERROR):
        await client._stdout_reader()

    assert processed == [message]
    assert any("maximum buffered size" in record.message for record in caplog.records)


def test_stdio_parameters_default_cap():
    from chuk_mcp.transports.stdio.parameters import StdioParameters

    assert StdioParameters(command="echo").max_buffer_size == DEFAULT_MAX_BUFFER_SIZE
