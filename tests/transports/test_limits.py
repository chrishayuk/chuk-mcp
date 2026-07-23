# tests/transports/test_limits.py
"""
Tests for transport buffer-size limits.

A malicious or compromised MCP server can withhold the newline that delimits a
message and stream indefinitely. These tests pin the cap that stops each
transport from accumulating that data without bound.
"""

import logging

import pytest

from chuk_mcp.transports.limits import (
    DEFAULT_MAX_BUFFER_SIZE,
    MessageTooLargeError,
    aread_text_bounded,
    check_buffer_size,
    resolve_max_buffer_size,
)


class _FakeStreamingResponse:
    """Minimal stand-in for a streaming httpx response."""

    def __init__(self, chunk: bytes, repeat: int, encoding: str = "utf-8"):
        self._chunk = chunk
        self._repeat = repeat
        self.encoding = encoding
        self.chunks_yielded = 0

    async def aiter_bytes(self):
        for _ in range(self._repeat):
            self.chunks_yielded += 1
            yield self._chunk

    async def aiter_text(self, chunk_size=None):
        async for chunk in self.aiter_bytes():
            yield chunk.decode(self.encoding)


###############################################################################
# Helper-level behaviour
###############################################################################


def test_check_buffer_size_allows_buffer_at_limit():
    check_buffer_size("x" * 100, 100)  # must not raise


def test_check_buffer_size_rejects_oversized_buffer():
    with pytest.raises(MessageTooLargeError) as exc:
        check_buffer_size("x" * 101, 100, "SSE event")

    assert exc.value.size == 101
    assert exc.value.limit == 100
    assert "SSE event" in str(exc.value)


def test_check_buffer_size_disabled_by_zero():
    check_buffer_size("x" * 10_000, 0)  # must not raise


def test_resolve_max_buffer_size_falls_back_to_default():
    class NoAttr:
        pass

    assert resolve_max_buffer_size(NoAttr()) == DEFAULT_MAX_BUFFER_SIZE


def test_resolve_max_buffer_size_honours_parameter():
    class WithAttr:
        max_buffer_size = 4096

    assert resolve_max_buffer_size(WithAttr()) == 4096


@pytest.mark.asyncio
async def test_aread_text_bounded_returns_small_body():
    response = _FakeStreamingResponse(b"hello ", repeat=3)
    assert await aread_text_bounded(response, 1024) == "hello hello hello "


@pytest.mark.asyncio
async def test_aread_text_bounded_aborts_before_consuming_everything():
    """The read must stop early rather than buffering the whole hostile body."""
    response = _FakeStreamingResponse(b"A" * 100, repeat=1000)

    with pytest.raises(MessageTooLargeError):
        await aread_text_bounded(response, 500)

    # Aborted after crossing the limit, not after draining all 1000 chunks.
    assert response.chunks_yielded <= 6


###############################################################################
# SSE transport
###############################################################################


@pytest.mark.asyncio
async def test_sse_stream_aborts_on_newline_free_stream():
    """A server that never sends a newline must not grow the buffer forever."""
    pytest.importorskip("httpx")
    from chuk_mcp.transports.sse.parameters import SSEParameters
    from chuk_mcp.transports.sse.transport import SSETransport

    params = SSEParameters(url="http://localhost:3000", max_buffer_size=1000)
    transport = SSETransport(params)
    response = _FakeStreamingResponse(b"A" * 100, repeat=1000)
    transport._sse_response = response

    with pytest.raises(MessageTooLargeError):
        await transport._process_sse_stream()

    assert response.chunks_yielded <= 12


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

    params = StreamableHTTPParameters(
        url="http://localhost:3000/mcp", max_buffer_size=1000
    )
    transport = StreamableHTTPTransport(params)

    routed = []

    async def _capture(data):
        routed.append(data)

    transport._route_response = _capture  # type: ignore[assignment]

    response = _UnreadResponse(b"A" * 100, repeat=1000)
    await transport._process_sse_response(response, "msg-1")  # type: ignore[arg-type]

    # The oversized stream is reported as a JSON-RPC error, not buffered.
    assert len(routed) == 1
    assert "maximum buffered size" in routed[0]["error"]["message"]
    assert response.chunks_yielded <= 12


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
    """Stand-in for an anyio subprocess whose stdout never terminates a line."""

    def __init__(self, chunk: bytes, repeat: int):
        self.stdout = self._Stdout(chunk, repeat)

    class _Stdout:
        def __init__(self, chunk: bytes, repeat: int):
            self._chunk = chunk
            self._repeat = repeat
            self.chunks_yielded = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.chunks_yielded >= self._repeat:
                raise StopAsyncIteration
            self.chunks_yielded += 1
            return self._chunk


@pytest.mark.asyncio
async def test_stdio_reader_aborts_on_newline_free_output(caplog):
    """A server process that never terminates a line must not grow the buffer."""
    from chuk_mcp.transports.stdio.parameters import StdioParameters
    from chuk_mcp.transports.stdio.stdio_client import StdioClient

    client = StdioClient(StdioParameters(command="echo", args=[], max_buffer_size=1000))
    process = _FakeProcess(b"A" * 100, repeat=1000)
    client.process = process  # type: ignore[assignment]

    with caplog.at_level(logging.ERROR):
        await client._stdout_reader()

    # The reader stops instead of draining all 1000 chunks into memory.
    assert process.stdout.chunks_yielded <= 12
    assert any("maximum buffered size" in record.message for record in caplog.records)


def test_stdio_parameters_default_cap():
    from chuk_mcp.transports.stdio.parameters import StdioParameters

    assert StdioParameters(command="echo").max_buffer_size == DEFAULT_MAX_BUFFER_SIZE
