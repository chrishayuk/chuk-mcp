# chuk_mcp/transports/base.py
from abc import ABC, abstractmethod
from typing import Tuple
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


class TransportParameters(ABC):
    """Base class for transport parameters."""

    pass


class Transport(ABC):
    """Base transport interface for MCP communication."""

    def __init__(self, parameters: TransportParameters):
        self.parameters = parameters

    @abstractmethod
    async def get_streams(
        self,
    ) -> Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]:
        """Get read/write streams for message communication."""
        pass

    @abstractmethod
    async def __aenter__(self):
        """Enter async context."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

    def set_protocol_version(self, version: str) -> None:
        """Set the negotiated protocol version (optional)."""
        pass
