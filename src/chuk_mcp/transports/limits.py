# chuk_mcp/transports/limits.py
"""
Shared buffer-size limits for transport message framing.

Every transport reads a peer's response incrementally and accumulates it until a
delimiter marks a complete message. Without an upper bound, a malicious or
compromised server can simply withhold that delimiter and grow the client's
memory until the process dies. These helpers give every transport a single,
configurable cap.
"""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024
"""Maximum bytes buffered for a single undelimited message (10 MB).

Comfortably above any normal JSON-RPC message while still bounding a hostile
peer. Override per-connection via the transport's parameters object.
"""

STREAM_READ_CHUNK_SIZE = 1024
"""Chunk size for incremental reads of a size-capped stream.

Bounds how far a read can overshoot ``max_buffer_size`` before the cap check
runs: peak buffered data is at most the cap plus one chunk.
"""

TEXT_ENCODING = "utf-8"
"""Wire encoding for transport payloads (mandated by both JSON-RPC and SSE)."""


def decode_text(data: bytes, encoding: str = TEXT_ENCODING) -> str:
    """Decode peer-supplied bytes, replacing invalid sequences.

    Replacement (U+FFFD) rather than raising means a hostile peer cannot kill a
    reader loop with deliberately malformed bytes; the mangled message then
    fails JSON parsing and is reported through the normal error path.
    """
    return data.decode(encoding, errors="replace")


class MessageTooLargeError(Exception):
    """Raised when a peer sends more undelimited data than the transport allows."""

    def __init__(self, size: int, limit: int, context: str = "Message") -> None:
        self.size = size
        self.limit = limit
        super().__init__(
            f"{context} exceeded the maximum buffered size: {size} bytes accumulated "
            f"without a complete message (limit: {limit} bytes). "
            "Aborting to avoid unbounded memory growth."
        )


def check_buffer_size(buffer: Any, max_size: int, context: str = "Message") -> None:
    """Raise MessageTooLargeError if ``buffer`` has outgrown ``max_size``.

    ``buffer`` should be bytes so the cap counts bytes, not characters. A
    ``max_size`` of 0 disables the check.
    """
    if max_size > 0 and len(buffer) > max_size:
        raise MessageTooLargeError(len(buffer), max_size, context)


def resolve_max_buffer_size(parameters: Any) -> int:
    """Read ``max_buffer_size`` off a parameters object, falling back to the default.

    Negative values raise ValueError so a typo cannot silently disable the cap;
    0 is the explicit opt-out.
    """
    value: Optional[int] = getattr(parameters, "max_buffer_size", None)
    if value is None:
        return DEFAULT_MAX_BUFFER_SIZE
    size = int(value)
    if size < 0:
        raise ValueError(
            f"max_buffer_size must be >= 0 (got {size}); use 0 to disable the cap"
        )
    return size


async def aread_text_bounded(
    response: Any, max_size: int, context: str = "HTTP response"
) -> str:
    """Read an httpx response body incrementally, aborting past ``max_size``.

    ``httpx``'s own non-streaming read applies no size limit, so responses must be
    consumed chunk-by-chunk to enforce one.
    """
    chunks: list[bytes] = []
    total = 0

    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if max_size > 0 and total > max_size:
            raise MessageTooLargeError(total, max_size, context)
        chunks.append(chunk)

    encoding = getattr(response, "encoding", None) or TEXT_ENCODING
    return decode_text(b"".join(chunks), encoding)
