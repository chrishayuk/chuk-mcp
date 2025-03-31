# chuk_mcp/mcp_client/transport/stdio/stdio_server_parameters.py
from typing import Any, Dict, Optional, List
from chuk_mcp.mcp_client.mcp_pydantic_base import McpPydanticBase, Field, PYDANTIC_AVAILABLE, ValidationError

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
    
    if PYDANTIC_AVAILABLE:
        # Add Pydantic-specific validation
        from pydantic import field_validator
        
        @field_validator('args')
        def validate_args(cls, v):
            if not isinstance(v, list):
                raise ValueError("args must be a list")
            return v
            
        @field_validator('command')
        def validate_command(cls, v):
            if not isinstance(v, str):
                raise ValueError("command must be a string")
            return v
            
        @field_validator('env')
        def validate_env(cls, v):
            if v is not None and not isinstance(v, dict):
                raise ValueError("env must be a dictionary or None")
            return v
    else:
        # Custom validation for the fallback implementation
        def __post_init__(self):
            super().__post_init__()
            
            # Validate command is a string
            if not isinstance(self.command, str):
                raise ValidationError("command must be a string")
            
            # Validate args is a list
            if not isinstance(self.args, list):
                raise ValidationError("args must be a list")
                
            # Validate env is a dict if provided
            if self.env is not None and not isinstance(self.env, dict):
                raise ValidationError("env must be a dictionary or None")