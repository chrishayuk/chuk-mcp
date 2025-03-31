# chuk_mcp/mcp_client/transport/stdio/stdio_server_parameters.py
from typing import Dict, List, Optional
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field

class StdioServerParameters(McpPydanticBase):
    """
    Parameters for starting an stdio server.
    
    Attributes:
        command (str): The command to execute.
        args (List[str], optional): Command line arguments. Defaults to an empty list.
        env (Dict[str, str], optional): Environment variables. Defaults to None.
    """
    command: str
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None