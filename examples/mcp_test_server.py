#!/usr/bin/env python3
"""
Working MCP Test Server - New APIs Only

This server demonstrates the new chuk-mcp server framework with clean,
modern tool registration and protocol handling.
"""

import asyncio
import json
import sys
import logging
import argparse
from typing import Dict, Any

# New chuk-mcp server APIs
from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities
from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage

# Set up logging to stderr so it doesn't interfere with JSON-RPC
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)


class ModernMCPServer:
    """
    Modern MCP test server using the new chuk-mcp framework.
    
    Demonstrates:
    - Clean tool registration
    - Automatic protocol handling
    - Session management
    - Type-safe message processing
    """
    
    def __init__(self):
        # Create server with new framework
        capabilities = ServerCapabilities(
            tools={"listChanged": True},
            resources={"listChanged": True},
            prompts={"listChanged": True}
        )
        
        self.mcp_server = MCPServer(
            name="modern-test-server", 
            version="2.0.0",
            capabilities=capabilities
        )
        
        # Register all our tools
        self._register_tools()
        self._register_resources()
        
        logger.info("Modern MCP server initialized with new framework")
    
    def _register_tools(self):
        """Register tools using the new framework API."""
        
        # Hello tool
        async def hello_tool(name: str = "World") -> str:
            return f"Hello, {name}! 👋 Greetings from the modern MCP server framework!"
        
        self.mcp_server.register_tool(
            name="hello",
            handler=hello_tool,
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"}
                },
                "required": ["name"]
            },
            description="Say hello to someone using the modern framework"
        )
        
        # Echo tool for testing
        async def echo_tool(message: str) -> str:
            return f"🔄 Echo: {message}"
        
        self.mcp_server.register_tool(
            name="echo",
            handler=echo_tool,
            schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to echo back"}
                },
                "required": ["message"]
            },
            description="Echo back a message"
        )
        
        # Calculator tool for demonstration
        async def calculate_tool(operation: str, a: float, b: float) -> str:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return "❌ Error: Division by zero"
                result = a / b
            else:
                return f"❌ Error: Unknown operation '{operation}'"
            
            return f"🧮 {a} {operation} {b} = {result}"
        
        self.mcp_server.register_tool(
            name="calculate",
            handler=calculate_tool,
            schema={
                "type": "object", 
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            },
            description="Perform basic mathematical operations"
        )
        
        logger.info("Registered 3 tools with modern framework")
    
    def _register_resources(self):
        """Register resources using the new framework API."""
        
        # Server status resource
        async def server_status() -> str:
            status = {
                "server": "modern-test-server",
                "version": "2.0.0",
                "framework": "chuk-mcp",
                "features": ["tools", "resources", "modern-apis"],
                "status": "running"
            }
            return json.dumps(status, indent=2)
        
        self.mcp_server.register_resource(
            uri="server://status",
            handler=server_status,
            name="Server Status",
            description="Current server status and information",
            mime_type="application/json"
        )
        
        # Server info resource
        async def server_info() -> str:
            return """🚀 Modern MCP Test Server

Framework: chuk-mcp v2.0
Features:
  ✅ Modern tool registration
  ✅ Automatic protocol handling  
  ✅ Session management
  ✅ Type-safe operations
  ✅ Resource management

This server demonstrates the new chuk-mcp server framework
with clean APIs and modern Python patterns.
"""
        
        self.mcp_server.register_resource(
            uri="server://info",
            handler=server_info,
            name="Server Information", 
            description="Detailed server information and capabilities",
            mime_type="text/plain"
        )
        
        logger.info("Registered 2 resources with modern framework")

    async def read_stdin(self):
        """Async generator for reading JSON-RPC messages from stdin."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        # Connect stdin to the reader
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    logger.info("EOF on stdin, shutting down")
                    break
                
                line_str = line.decode('utf-8').strip()
                if line_str:
                    yield line_str
                    
            except Exception as e:
                logger.error(f"Error reading stdin: {e}")
                break

    async def run(self):
        """Main server loop using the modern framework."""
        logger.info("🚀 Starting modern MCP server...")
        logger.info("Using chuk-mcp server framework with new APIs")
        
        try:
            async for line in self.read_stdin():
                logger.debug(f"Received: {line}")
                
                try:
                    # Parse JSON-RPC message
                    message_dict = json.loads(line)
                    json_rpc_msg = JSONRPCMessage.model_validate(message_dict)
                    
                    # Handle using modern framework
                    response_msg, session_id = await self.mcp_server.protocol_handler.handle_message(
                        json_rpc_msg, session_id=None
                    )
                    
                    if response_msg:
                        # Send response
                        response_dict = response_msg.model_dump(exclude_none=True)
                        response_json = json.dumps(response_dict)
                        print(response_json, flush=True)
                        logger.debug(f"Sent: {response_json}")
                    else:
                        logger.debug("No response (notification)")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    print(json.dumps(error_response), flush=True)
                    
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    error_response = {
                        "jsonrpc": "2.0", 
                        "id": message_dict.get("id") if 'message_dict' in locals() else None,
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                    }
                    print(json.dumps(error_response), flush=True)
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("Modern MCP server shutting down")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Modern MCP Test Server (New APIs Only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python modern_mcp_server.py           # Run server
  python modern_mcp_server.py --verbose # Enable debug logging
  python modern_mcp_server.py --quiet   # Minimal logging
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )
    
    parser.add_argument(
        "--quiet", "-q", 
        action="store_true",
        help="Minimal logging output"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    try:
        server = ModernMCPServer()
        logger.info("✨ Modern MCP server framework loaded")
        logger.info("🎯 Features: Protocol handling, tool registration, session management")
        
        asyncio.run(server.run())
        
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted by user")
    except Exception as e:
        logger.error(f"💥 Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()