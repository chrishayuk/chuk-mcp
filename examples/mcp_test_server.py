#!/usr/bin/env python3
"""
Working MCP Test Server

This server properly handles async stdin/stdout communication.
"""

import asyncio
import json
import sys
import logging

# Set up logging to stderr so it doesn't interfere with JSON-RPC
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)

class WorkingMCPServer:
    def __init__(self):
        self.server_info = {
            "name": "working-test-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}
        }

    async def handle_message(self, message):
        """Handle incoming JSON-RPC message."""
        logger.debug(f"Handling message: {message}")
        
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                        "capabilities": self.capabilities,
                        "serverInfo": self.server_info
                    }
                }
                logger.debug(f"Sending initialize response: {response}")
                return response
                
            elif method == "notifications/initialized":
                logger.debug("Received initialized notification")
                return None  # No response for notifications
                
            elif method == "ping":
                response = {
                    "jsonrpc": "2.0", 
                    "id": msg_id, 
                    "result": {}
                }
                logger.debug(f"Sending ping response: {response}")
                return response
                
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0", 
                    "id": msg_id,
                    "result": {
                        "tools": [{
                            "name": "hello",
                            "description": "Say hello to someone",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name to greet"
                                    }
                                },
                                "required": ["name"]
                            }
                        }]
                    }
                }
                logger.debug(f"Sending tools list response: {response}")
                return response
                
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "hello":
                    name = arguments.get("name", "World")
                    response = {
                        "jsonrpc": "2.0", 
                        "id": msg_id,
                        "result": {
                            "content": [{
                                "type": "text", 
                                "text": f"Hello, {name}! 👋 This message comes from the working MCP test server."
                            }]
                        }
                    }
                    logger.debug(f"Sending tool call response: {response}")
                    return response
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32602,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            
            # Unknown method
            error_response = {
                "jsonrpc": "2.0", 
                "id": msg_id,
                "error": {
                    "code": -32601, 
                    "message": f"Method not found: {method}"
                }
            }
            logger.debug(f"Sending error response: {error_response}")
            return error_response
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {
                "jsonrpc": "2.0", 
                "id": msg_id,
                "error": {
                    "code": -32603, 
                    "message": f"Internal error: {str(e)}"
                }
            }

    async def read_stdin(self):
        """Async generator for reading from stdin."""
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
        """Main server loop."""
        logger.info("Starting working MCP server...")
        
        try:
            async for line in self.read_stdin():
                logger.debug(f"Received line: {line}")
                
                try:
                    message = json.loads(line)
                    response = await self.handle_message(message)
                    
                    if response:
                        response_json = json.dumps(response)
                        print(response_json, flush=True)
                        logger.debug(f"Sent response: {response_json}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e} for line: {line}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("Working MCP server shutting down")

if __name__ == "__main__":
    try:
        server = WorkingMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)