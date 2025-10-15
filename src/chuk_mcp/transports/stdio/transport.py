# chuk_mcp/transports/stdio/transport.py
"""
Stdio transport implementation that wraps the legacy stdio client.
"""

from typing import Tuple, Optional
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..base import Transport
from .parameters import StdioParameters
from .stdio_client import StdioClient


class StdioTransport(Transport):
    """Stdio transport wrapper for the new transport interface."""

    def __init__(self, parameters: StdioParameters):
        super().__init__(parameters)
        self._client: Optional[StdioClient] = None

    async def get_streams(
        self,
    ) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        if not self._client:
            raise RuntimeError("Transport not started - use as async context manager")
        return self._client.get_streams()

    async def __aenter__(self):
        """Enter async context."""
        self._client = StdioClient(self.parameters)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            result = await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None
            return result
        return False

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version."""
        if self._client:
            self._client.set_protocol_version(version)
