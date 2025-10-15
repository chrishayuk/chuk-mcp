#!/usr/bin/env python3
"""
chuk-mcp Quickstart Script

Updated to use the new transport and protocol APIs exclusively.
"""

import tempfile
import os
import sys
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)

# Import new chuk-mcp APIs
print("🔧 Loading chuk-mcp with new APIs...")
try:
    import anyio

    # New transport layer imports
    from chuk_mcp.transports.stdio import stdio_client
    from chuk_mcp.transports.stdio.parameters import StdioParameters

    # New protocol layer imports
    from chuk_mcp.protocol.messages import (
        send_initialize,
        send_ping,
        send_tools_list,
        send_tools_call,
    )

    print("✅ New chuk-mcp APIs loaded successfully!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n🔍 Troubleshooting:")
    print("   • Make sure chuk-mcp is installed: pip install -e .")
    print("   • Check that you're in the right directory")
    print("   • Verify the new transport structure exists")
    sys.exit(1)


def create_modern_server():
    """Create a modern MCP server using the new framework."""
    return '''#!/usr/bin/env python3
import asyncio
import json
import sys
import logging

# Set up logging for the server
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

class QuickstartMCPServer:
    """Simple MCP server for quickstart demo."""
    
    def __init__(self):
        self.server_info = {
            "name": "quickstart-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {"listChanged": True}
        }
    
    async def handle_message(self, message):
        """Handle JSON-RPC messages."""
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
                        "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                        "capabilities": self.capabilities,
                        "serverInfo": self.server_info,
                        "instructions": "Welcome to the chuk-mcp quickstart server! 🚀"
                    }
                }
                logger.debug(f"Initialize response: {response}")
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
                logger.debug(f"Ping response: {response}")
                return response
                
            elif method == "tools/list":
                tools = [
                    {
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
                    },
                    {
                        "name": "echo",
                        "description": "Echo back a message",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Message to echo"
                                }
                            },
                            "required": ["message"]
                        }
                    }
                ]
                
                response = {
                    "jsonrpc": "2.0", 
                    "id": msg_id,
                    "result": {"tools": tools}
                }
                logger.debug(f"Tools list response: {response}")
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
                                "text": f"Hello, {name}! 👋 Welcome to chuk-mcp!"
                            }]
                        }
                    }
                    logger.debug(f"Hello tool response: {response}")
                    return response
                    
                elif tool_name == "echo":
                    message = arguments.get("message", "")
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"Echo: {message}"
                            }]
                        }
                    }
                    logger.debug(f"Echo tool response: {response}")
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
            logger.debug(f"Error response: {error_response}")
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
        logger.info("🚀 Starting quickstart MCP server...")
        
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
                    logger.error(f"JSON decode error: {e}")
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
            logger.info("Quickstart MCP server shutting down")

if __name__ == "__main__":
    try:
        server = QuickstartMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)
'''


async def quickstart_demo():
    """Run a quick demonstration using the new APIs."""
    print("🚀 chuk-mcp Quickstart Demo")
    print("=" * 40)
    print("🎯 Using NEW APIs:")
    print("   • chuk_mcp.transports.stdio")
    print("   • chuk_mcp.protocol.messages")
    print("=" * 40)

    # Create temporary server
    print("📝 Creating quickstart MCP server...")
    server_code = create_modern_server()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(server_code)
        server_file = f.name

    print(f"📄 Server file: {server_file}")

    try:
        print("🔧 Setting up server parameters...")
        # Use new StdioParameters class
        server_params = StdioParameters(command="python", args=[server_file])

        print("📡 Connecting to server...")
        print("   (Using new stdio_client transport...)")

        # Use new stdio_client context manager
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("   ✅ Connection established!")

            # Test 1: Initialize
            print("\\n1️⃣  Testing initialization...")
            try:
                init_result = await send_initialize(read_stream, write_stream)
                print(f"   ✅ Server: {init_result.serverInfo.name}")
                print(f"   📋 Protocol: {init_result.protocolVersion}")
                if hasattr(init_result, "instructions") and init_result.instructions:
                    print(f"   💡 Instructions: {init_result.instructions}")
            except Exception as e:
                print(f"   ❌ Initialization failed: {e}")
                raise

            # Test 2: Ping
            print("\\n2️⃣  Testing ping...")
            try:
                ping_success = await send_ping(read_stream, write_stream)
                print(
                    f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}"
                )
            except Exception as e:
                print(f"   ❌ Ping failed: {e}")
                # Continue anyway

            # Test 3: List tools
            print("\\n3️⃣  Testing tools...")
            try:
                tools_response = await send_tools_list(read_stream, write_stream)
                tools = tools_response["tools"]
                print(f"   📋 Found {len(tools)} tool(s):")
                for tool in tools:
                    print(f"      • {tool['name']}: {tool['description']}")
            except Exception as e:
                print(f"   ❌ Tools list failed: {e}")
                raise

            # Test 4: Call hello tool
            print("\\n4️⃣  Testing tool execution...")
            try:
                hello_response = await send_tools_call(
                    read_stream, write_stream, "hello", {"name": "New API User"}
                )
                result_text = hello_response["content"][0]["text"]
                print(f"   📤 Hello result: {result_text}")
            except Exception as e:
                print(f"   ❌ Hello tool failed: {e}")
                raise

            # Test 5: Call echo tool
            print("\\n5️⃣  Testing echo tool...")
            try:
                echo_response = await send_tools_call(
                    read_stream,
                    write_stream,
                    "echo",
                    {"message": "Testing new chuk-mcp APIs!"},
                )
                echo_text = echo_response["content"][0]["text"]
                print(f"   📤 Echo result: {echo_text}")
            except Exception as e:
                print(f"   ❌ Echo tool failed: {e}")
                raise

            print("\\n🎉 Quickstart demo completed successfully!")
            print("\\n💡 Your new chuk-mcp APIs are working correctly!")
            print("\\n📊 Summary:")
            print("   ✅ New transport layer: Working")
            print("   ✅ New protocol messages: Working")
            print("   ✅ StdioParameters: Working")
            print("   ✅ stdio_client context manager: Working")
            print("   ✅ Message handling: Working")
            print("   ✅ Tool execution: Working")

    except Exception as e:
        print(f"\\n❌ Error during demo: {str(e)}")
        print("\\n🔍 Troubleshooting:")
        print(f"   • Server file: {server_file}")
        print("   • Try running the server manually:")
        print(f"     python {server_file}")
        print("   • Check for any error messages above")

        # Show some debugging info
        print("\\n🔧 Debug info:")
        print(f"   • Python path: {sys.executable}")
        print(f"   • Working directory: {os.getcwd()}")
        print(f"   • Server file exists: {os.path.exists(server_file)}")

        # Show import status
        print("\\n📦 Import status:")
        try:
            import chuk_mcp

            print(f"   • chuk_mcp location: {chuk_mcp.__file__}")
            print("   • New transport APIs: Available")
            print("   • New protocol APIs: Available")
        except ImportError:
            print("   • chuk_mcp not found in Python path")

        raise

    finally:
        # Clean up
        if os.path.exists(server_file):
            try:
                os.unlink(server_file)
                print("🧹 Cleaned up temporary file")
            except Exception as e:
                print(f"⚠️  Could not clean up {server_file}: {e}")


def main():
    """Main entry point."""
    print("🚀 chuk-mcp Quickstart - New APIs")
    print("=" * 50)
    print("Testing your new chuk-mcp transport and protocol APIs...")
    print("=" * 50)

    try:
        anyio.run(quickstart_demo)
        print("\\n" + "=" * 50)
        print("🎉 Success! Your new chuk-mcp APIs are working perfectly!")
        print("\\n📚 What this validates:")
        print("   ✅ New transport layer (chuk_mcp.transports.stdio)")
        print("   ✅ New protocol messages (chuk_mcp.protocol.messages)")
        print("   ✅ StdioParameters class")
        print("   ✅ stdio_client context manager")
        print("   ✅ Core MCP functionality")
        print("\\n📚 Next steps:")
        print("   • Try the full E2E smoke tests")
        print("   • Explore the modern server framework")
        print("   • Build your own MCP integrations")
        print("   • Test the new server APIs")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\\n\\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\\n💥 Demo failed: {str(e)}")
        print("\\n🔧 This suggests an issue with:")
        print("   • New transport layer setup")
        print("   • New protocol message imports")
        print("   • API compatibility")
        print("\\nPlease check the error messages above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
