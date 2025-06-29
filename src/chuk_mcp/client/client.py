# chuk_mcp/client/client.py
"""
High-level MCP client for easy server communication.
"""
from typing import Dict, Any, List, Optional, Union
import logging

from ..transports.base import Transport
from ..protocol.messages import (
    send_initialize, send_tools_list, send_tools_call,
    send_resources_list, send_resources_read, send_prompts_list, send_prompts_get
)


class MCPClient:
    """High-level MCP client."""
    
    def __init__(self, transport: Transport):
        self.transport = transport
        self.initialized = False
        self.server_info = None
        self.capabilities = None
        self._streams = None
    
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
            
            logging.info(f"Initialized connection to {self.server_info.name}")
        
        return result
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        response = await send_tools_list(read_stream, write_stream)
        return response.get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        return await send_tools_call(read_stream, write_stream, name, arguments or {})
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        response = await send_resources_list(read_stream, write_stream)
        return response.get("resources", [])
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        return await send_resources_read(read_stream, write_stream, uri)
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        response = await send_prompts_list(read_stream, write_stream)
        return response.get("prompts", [])
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a prompt."""
        await self._ensure_initialized()
        read_stream, write_stream = self._streams
        
        return await send_prompts_get(read_stream, write_stream, name, arguments)
    
    async def _ensure_initialized(self):
        """Ensure client is initialized."""
        if not self.initialized:
            await self.initialize()