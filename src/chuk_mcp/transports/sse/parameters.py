# chuk_mcp/transports/sse/parameters.py
from typing import Optional, Dict
from pydantic import field_validator, model_validator
from ..base import TransportParameters
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase


class SSEParameters(TransportParameters, McpPydanticBase):
    """Parameters for SSE (Server-Sent Events) transport."""
    
    url: str
    """Base URL for the SSE server (e.g., 'http://localhost:3000')"""
    
    headers: Optional[Dict[str, str]] = None
    """Optional HTTP headers to send with requests"""
    
    timeout: float = 60.0
    """Request timeout in seconds"""
    
    bearer_token: Optional[str] = None
    """Optional bearer token for authentication (added to Authorization header)"""
    
    session_id: Optional[str] = None
    """Optional session ID for reconnecting to existing sessions"""
    
    auto_reconnect: bool = True
    """Whether to automatically reconnect on connection loss"""
    
    max_reconnect_attempts: int = 5
    """Maximum number of reconnection attempts"""
    
    reconnect_delay: float = 1.0
    """Delay between reconnection attempts in seconds"""
    
    model_config = {"extra": "allow"}
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v:
            raise ValueError("SSE URL cannot be empty")
        if not v.startswith(('http://', 'https://')):
            raise ValueError("SSE URL must start with http:// or https://")
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v
    
    @field_validator('max_reconnect_attempts')
    @classmethod
    def validate_max_reconnect_attempts(cls, v):
        """Validate max reconnect attempts is non-negative."""
        if v < 0:
            raise ValueError("Max reconnect attempts must be non-negative")
        return v
    
    @field_validator('reconnect_delay')
    @classmethod
    def validate_reconnect_delay(cls, v):
        """Validate reconnect delay is non-negative."""
        if v < 0:
            raise ValueError("Reconnect delay must be non-negative")
        return v
    
    @model_validator(mode='after')
    def setup_auth_headers(self):
        """Set up authentication headers after model creation."""
        if self.bearer_token:
            if not self.headers:
                self.headers = {}
            
            # Add Authorization header if not already present
            if not any(key.lower() == 'authorization' for key in self.headers.keys()):
                if self.bearer_token.startswith('Bearer '):
                    self.headers['Authorization'] = self.bearer_token
                else:
                    self.headers['Authorization'] = f'Bearer {self.bearer_token}'
        
        return self