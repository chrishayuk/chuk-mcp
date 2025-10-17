# chuk_mcp/client/client.py
"""
High-level MCP client for easy server communication.
"""

from typing import Dict, Any, List, Tuple, Optional
import logging

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ..transports.base import Transport
from ..protocol.messages import (
    send_initialize,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
)
from ..protocol.messages.tools import Tool, ToolResult
from ..protocol.messages.resources import Resource, ReadResourceResult
from ..protocol.messages.prompts import Prompt, GetPromptResult


class MCPClient:
    """High-level MCP client."""

    def __init__(self, transport: Transport):
        from ..protocol.types.info import ServerInfo
        from ..protocol.types.capabilities import ServerCapabilities

        self.transport = transport
        self.initialized = False
        self.server_info: Optional[ServerInfo] = None
        self.capabilities: Optional[ServerCapabilities] = None
        self._streams: Optional[
            Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]
        ] = None

    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection with server."""
        if self.initialized:
            return {"server_info": self.server_info, "capabilities": self.capabilities}

        self._streams = await self.transport.get_streams()
        read_stream, write_stream = self._streams

        result = await send_initialize(read_stream, write_stream)
        if result:
            self.initialized = True
            self.server_info = result.serverInfo
            self.capabilities = result.capabilities

            # Set protocol version on transport for feature detection
            self.transport.set_protocol_version(result.protocolVersion)

            assert self.server_info is not None
            logging.info(f"Initialized connection to {self.server_info.name}")

        return result  # type: ignore[return-value]

    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        result = await send_tools_list(read_stream, write_stream)
        return result.tools

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Call a tool."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        return await send_tools_call(read_stream, write_stream, name, arguments or {})

    async def list_resources(self) -> List[Resource]:
        """List available resources."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        result = await send_resources_list(read_stream, write_stream)
        return result.resources

    async def read_resource(self, uri: str) -> ReadResourceResult:
        """Read a resource."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        return await send_resources_read(read_stream, write_stream, uri)

    async def list_prompts(self) -> List[Prompt]:
        """List available prompts."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        result = await send_prompts_list(read_stream, write_stream)
        return result.prompts

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> GetPromptResult:
        """Get a prompt."""
        await self._ensure_initialized()
        assert self._streams is not None
        read_stream, write_stream = self._streams

        return await send_prompts_get(read_stream, write_stream, name, arguments)

    async def _ensure_initialized(self):
        """Ensure client is initialized."""
        if not self.initialized:
            await self.initialize()
