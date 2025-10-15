# chuk_mcp/transports/stdio/parameters.py
from typing import List, Optional, Dict
from ..base import TransportParameters
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class StdioParameters(TransportParameters, McpPydanticBase):
    """Parameters for stdio transport."""

    command: str
    args: List[str] = []
    env: Optional[Dict[str, str]] = None
