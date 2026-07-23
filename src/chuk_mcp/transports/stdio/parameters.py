# chuk_mcp/transports/stdio/parameters.py
from typing import List, Optional, Dict
from ..base import TransportParameters
from ..limits import DEFAULT_MAX_BUFFER_SIZE
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class StdioParameters(TransportParameters, McpPydanticBase):
    """Parameters for stdio transport."""

    command: str
    args: List[str] = []
    env: Optional[Dict[str, str]] = None
    max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE
    """Maximum bytes buffered for a single undelimited message (>= 0; 0 disables the cap)"""
