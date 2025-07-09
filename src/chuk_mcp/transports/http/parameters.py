# chuk_mcp/transports/http/parameters.py
from typing import Optional, Dict
from ..base import TransportParameters
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class HTTPParameters(TransportParameters, McpPydanticBase):
    """Parameters for HTTP transport."""
    url: str
    headers: Optional[Dict[str, str]] = None
    timeout: float = 60.0  # Default timeout in seconds
    method: str = "POST"   # HTTP method to use