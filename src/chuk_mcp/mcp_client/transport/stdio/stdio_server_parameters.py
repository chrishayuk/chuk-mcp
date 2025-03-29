# chuk_mcp/mcp_client/transport/stdio/stdio_server_parameters.py
from typing import Any, Dict, Optional
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field

class StdioServerParameters(McpPydanticBase):
    command: str
    args: list[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None