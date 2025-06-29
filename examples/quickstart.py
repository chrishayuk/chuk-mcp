#!/usr/bin/env python3
"""
chuk-mcp Quickstart Script

Updated to use the new protocol layer structure.
"""

import asyncio
import tempfile
import os
import json
import sys
import logging
from pathlib import Path

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG)

# Import chuk-mcp with fallback for import paths
print("🔧 Loading chuk-mcp...")
try:
    import anyio
    
    # Transport layer imports (these should be stable)
    from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
    from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters
    
    # Try the new centralized protocol imports first
    try:
        from chuk_mcp.protocol.messages import (
            send_initialize,
            send_ping,
            send_tools_list,
            send_tools_call,
        )
        print("✅ Using centralized protocol imports")
    except ImportError:
        # Fallback to individual module imports
        try:
            from chuk_mcp.protocol.messages.initialize import send_initialize
            from chuk_mcp.protocol.messages.ping import send_ping
            from chuk_mcp.protocol.messages.tools import send_tools_list, send_tools_call
            print("✅ Using individual module imports")
        except ImportError:
            # Last resort - try the old paths
            from chuk_mcp.protocol.messages.initialize.send_messages import send_initialize
            from chuk_mcp.protocol.messages.ping.send_messages import send_ping
            from chuk_mcp.protocol.messages.tools.send_messages import send_tools_list, send_tools_call
            print("✅ Using legacy import paths")
    
    print("✅ chuk-mcp imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n🔍 Troubleshooting:")
    print("   • Make sure chuk-mcp is installed: pip install -e .")
    print("   • Check that you're in the right directory")
    print("   • Verify the package structure matches the imports")
    sys.exit(1)


def create_minimal_server():
    """Create a minimal MCP server for testing."""
    return '''#!/usr/bin/env python3
import asyncio
import json
import sys
import logging

# Set up logging for the server
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)

class MinimalMCPServer:
    def __init__(self):
        self.server_info = {
            "name": "quickstart-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}
        }
    
    async def handle_message(self, message):
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
                        "serverInfo": self.server_info
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
                response = {
                    "jsonrpc": "2.0", 
                    "id": msg_id,
                    "result": {
                        "tools": [{
                            "name": "hello",
                            "description": "Say hello",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"}
                                },
                                "required": ["name"]
                            }
                        }]
                    }
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
                                "text": f"Hello, {name}! 👋"
                            }]
                        }
                    }
                    logger.debug(f"Tool call response: {response}")
                    return response
            
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
    
    async def run(self):
        logger.info("Starting MCP server...")
        
        while True:
            try:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
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
                break
        
        logger.info("MCP server shutting down")

if __name__ == "__main__":
    try:
        asyncio.run(MinimalMCPServer().run())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"Server failed: {e}")
'''


async def quickstart_demo():
    """Run a quick demonstration with better error handling."""
    print("🚀 chuk-mcp Quickstart Demo")
    print("=" * 40)
    
    # Create temporary server
    print("📝 Creating minimal MCP server...")
    server_code = create_minimal_server()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(server_code)
        server_file = f.name
    
    print(f"📄 Server file: {server_file}")
    
    try:
        print("🔧 Setting up server parameters...")
        server_params = StdioServerParameters(
            command="python",
            args=[server_file],
            env=None  # Use default environment
        )
        
        print("📡 Connecting to server...")
        print("   (This may take a few seconds...)")
        
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("   ✅ Connection established!")
            
            # Test 1: Initialize
            print("\\n1️⃣  Testing initialization...")
            try:
                init_result = await send_initialize(read_stream, write_stream, timeout=10.0)
                print(f"   ✅ Server: {init_result.serverInfo.name}")
                print(f"   📋 Protocol: {init_result.protocolVersion}")
            except Exception as e:
                print(f"   ❌ Initialization failed: {e}")
                raise
            
            # Test 2: Ping
            print("\\n2️⃣  Testing ping...")
            try:
                ping_success = await send_ping(read_stream, write_stream, timeout=10.0)
                print(f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}")
            except Exception as e:
                print(f"   ❌ Ping failed: {e}")
                # Continue anyway
            
            # Test 3: List tools
            print("\\n3️⃣  Testing tools...")
            try:
                tools_response = await send_tools_list(read_stream, write_stream, timeout=10.0)
                tools = tools_response["tools"]
                print(f"   📋 Found {len(tools)} tool(s):")
                for tool in tools:
                    print(f"      • {tool['name']}: {tool['description']}")
            except Exception as e:
                print(f"   ❌ Tools list failed: {e}")
                raise
            
            # Test 4: Call tool
            print("\\n4️⃣  Testing tool execution...")
            try:
                hello_response = await send_tools_call(
                    read_stream, write_stream,
                    "hello", {"name": "chuk-mcp User"},
                    timeout=10.0
                )
                result_text = hello_response["content"][0]["text"]
                print(f"   📤 Tool result: {result_text}")
            except Exception as e:
                print(f"   ❌ Tool call failed: {e}")
                raise
            
            print("\\n🎉 Quickstart demo completed successfully!")
            print("\\n💡 Your chuk-mcp installation is working correctly!")
            print("\\n📊 Summary:")
            print("   ✅ Protocol layer: Working")
            print("   ✅ Transport layer: Working") 
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
        except ImportError:
            print("   • chuk_mcp not found in Python path")
        
        raise
    
    finally:
        # Clean up
        if os.path.exists(server_file):
            try:
                os.unlink(server_file)
                print(f"🧹 Cleaned up temporary file")
            except Exception as e:
                print(f"⚠️  Could not clean up {server_file}: {e}")


def main():
    """Main entry point."""
    print("🚀 chuk-mcp Quickstart")
    print("=" * 50)
    print("Testing your restructured chuk-mcp implementation...")
    print("=" * 50)
    
    try:
        anyio.run(quickstart_demo)
        print("\\n" + "=" * 50)
        print("🎉 Success! Your restructured chuk-mcp is working correctly!")
        print("\\n📚 What this validates:")
        print("   ✅ New protocol layer structure")
        print("   ✅ Import path compatibility")
        print("   ✅ Core MCP functionality")
        print("   ✅ Transport layer stability")
        print("\\n📚 Next steps:")
        print("   • Update your E2E tests with new import paths")
        print("   • Try the full feature demos")
        print("   • Build your own MCP integrations")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\\n\\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\\n💥 Demo failed: {str(e)}")
        print("\\n🔧 This suggests an issue with:")
        print("   • Import path configuration")
        print("   • Protocol layer restructuring")
        print("   • Or a missing file/module")
        print("\\nPlease check the error messages above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()