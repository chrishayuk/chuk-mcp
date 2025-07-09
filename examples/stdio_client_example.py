#!/usr/bin/env python3
"""
E2E Example: Stdio Client with MCP Server

This script demonstrates a complete working example of using the chuk-mcp
stdio client to connect to and interact with an MCP server process.
"""

import asyncio
import tempfile
import os
import sys
import logging
from pathlib import Path

import anyio

# chuk-mcp imports
from chuk_mcp.transports.stdio import stdio_client
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
    send_resources_list,
    send_resources_read,
    send_prompts_list,
    send_prompts_get,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_example_server():
    """Create a working MCP server for testing."""
    return '''#!/usr/bin/env python3
import asyncio
import json
import sys
import logging
import datetime
import random
import uuid

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

class ExampleMCPServer:
    def __init__(self):
        self.server_info = {
            "name": "stdio-example-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True}, 
            "prompts": {"listChanged": True}
        }
        self.session_id = str(uuid.uuid4())
        self.counter = 0
        self.notes = []

    async def handle_message(self, message):
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                        "capabilities": self.capabilities,
                        "serverInfo": self.server_info,
                        "instructions": f"Stdio MCP Server - Session: {self.session_id}"
                    }
                }
            
            elif method == "notifications/initialized":
                logger.info("Client initialization complete")
                return None
            
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "greet",
                                "description": "Greet someone with a personalized message",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Name to greet"},
                                        "style": {"type": "string", "enum": ["formal", "casual", "enthusiastic"], "default": "casual"}
                                    },
                                    "required": ["name"]
                                }
                            },
                            {
                                "name": "add_note",
                                "description": "Add a note to the server's memory",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string", "description": "Note content"},
                                        "category": {"type": "string", "default": "general"}
                                    },
                                    "required": ["content"]
                                }
                            },
                            {
                                "name": "increment_counter",
                                "description": "Increment the server counter",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "amount": {"type": "integer", "default": 1}
                                    }
                                }
                            },
                            {
                                "name": "generate_uuid",
                                "description": "Generate a new UUID",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "version": {"type": "integer", "enum": [1, 4], "default": 4}
                                    }
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "greet":
                    name = arguments.get("name", "Anonymous")
                    style = arguments.get("style", "casual")
                    
                    greetings = {
                        "formal": f"Good day, {name}. It is a pleasure to make your acquaintance.",
                        "casual": f"Hey {name}! 👋 Nice to meet you!",
                        "enthusiastic": f"🎉 HELLO {name.upper()}! 🚀 This is AMAZING! Welcome aboard! ✨"
                    }
                    
                    message = greetings.get(style, greetings["casual"])
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": message}]
                        }
                    }
                
                elif tool_name == "add_note":
                    content = arguments.get("content", "")
                    category = arguments.get("category", "general")
                    
                    note = {
                        "id": len(self.notes) + 1,
                        "content": content,
                        "category": category,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    self.notes.append(note)
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"📝 Added note #{note['id']} in category '{category}': {content}"}]
                        }
                    }
                
                elif tool_name == "increment_counter":
                    amount = arguments.get("amount", 1)
                    self.counter += amount
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"🔢 Counter incremented by {amount}. New value: {self.counter}"}]
                        }
                    }
                
                elif tool_name == "generate_uuid":
                    version = arguments.get("version", 4)
                    
                    if version == 1:
                        new_uuid = str(uuid.uuid1())
                    else:
                        new_uuid = str(uuid.uuid4())
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"🆔 Generated UUID v{version}: {new_uuid}"}]
                        }
                    }
            
            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "resources": [
                            {
                                "uri": "stdio://server-status",
                                "name": "Server Status",
                                "description": "Current server status and session information",
                                "mimeType": "application/json"
                            },
                            {
                                "uri": "stdio://notes",
                                "name": "Notes Collection",
                                "description": "All notes stored in this session",
                                "mimeType": "application/json"
                            },
                            {
                                "uri": "stdio://statistics",
                                "name": "Server Statistics",
                                "description": "Runtime statistics and metrics",
                                "mimeType": "text/plain"
                            }
                        ]
                    }
                }
            
            elif method == "resources/read":
                uri = params.get("uri")
                
                if uri == "stdio://server-status":
                    status = {
                        "server": self.server_info,
                        "session_id": self.session_id,
                        "counter": self.counter,
                        "notes_count": len(self.notes),
                        "timestamp": datetime.datetime.now().isoformat(),
                        "transport": "stdio"
                    }
                    content = json.dumps(status, indent=2)
                    mime_type = "application/json"
                
                elif uri == "stdio://notes":
                    if not self.notes:
                        notes_data = {"notes": [], "message": "No notes yet"}
                    else:
                        notes_data = {"notes": self.notes, "total": len(self.notes)}
                    
                    content = json.dumps(notes_data, indent=2)
                    mime_type = "application/json"
                
                elif uri == "stdio://statistics":
                    stats = f"""📊 Stdio MCP Server Statistics
Session ID: {self.session_id}
Counter Value: {self.counter}
Notes Count: {len(self.notes)}
Server Version: {self.server_info['version']}
Transport: stdio (subprocess communication)
Uptime: Running since session start
Features: Tools ✅ Resources ✅ Prompts ✅
"""
                    content = stats
                    mime_type = "text/plain"
                
                else:
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"}
                    }
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "contents": [{"uri": uri, "mimeType": mime_type, "text": content}]
                    }
                }
            
            elif method == "prompts/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "prompts": [
                            {
                                "name": "note_summary",
                                "description": "Generate a summary of all notes",
                                "arguments": [
                                    {"name": "format", "description": "Summary format (brief/detailed)", "required": False}
                                ]
                            },
                            {
                                "name": "greeting_template",
                                "description": "Generate a greeting template",
                                "arguments": [
                                    {"name": "occasion", "description": "Type of occasion", "required": True},
                                    {"name": "formality", "description": "Level of formality", "required": False}
                                ]
                            }
                        ]
                    }
                }
            
            elif method == "prompts/get":
                prompt_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if prompt_name == "note_summary":
                    format_type = arguments.get("format", "brief")
                    
                    if format_type == "detailed":
                        prompt_text = f"Please provide a detailed analysis and summary of the following {len(self.notes)} notes, including themes, categories, and insights:"
                    else:
                        prompt_text = f"Please provide a brief summary of these {len(self.notes)} notes:"
                    
                    # Add actual notes as context
                    if self.notes:
                        prompt_text += "\\n\\nNotes:\\n"
                        for note in self.notes:
                            prompt_text += f"- [{note['category']}] {note['content']}\\n"
                    else:
                        prompt_text += "\\n\\n(No notes to summarize yet)"
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "description": f"Notes summary prompt ({format_type} format)",
                            "messages": [
                                {"role": "user", "content": {"type": "text", "text": prompt_text}}
                            ]
                        }
                    }
                
                elif prompt_name == "greeting_template":
                    occasion = arguments.get("occasion", "meeting")
                    formality = arguments.get("formality", "professional")
                    
                    prompt_text = f"Please create a {formality} greeting template suitable for a {occasion}. The greeting should be warm, appropriate, and include space for personalization."
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "description": f"Greeting template for {occasion} ({formality} style)",
                            "messages": [
                                {"role": "user", "content": {"type": "text", "text": prompt_text}}
                            ]
                        }
                    }
        
        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
        
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

    async def read_stdin(self):
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                line_str = line.decode('utf-8').strip()
                if line_str:
                    yield line_str
            except Exception as e:
                logger.error(f"Error reading stdin: {e}")
                break

    async def run(self):
        logger.info("🚀 Starting Stdio MCP Example Server...")
        try:
            async for line in self.read_stdin():
                try:
                    message = json.loads(line)
                    response = await self.handle_message(message)
                    if response:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    print(json.dumps({
                        "jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "Parse error"}
                    }), flush=True)
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("Stdio MCP server shutting down")

if __name__ == "__main__":
    asyncio.run(ExampleMCPServer().run())
'''


async def run_stdio_example():
    """Run the complete stdio client example."""
    print("🚀 Stdio Client E2E Example")
    print("=" * 50)
    
    # Create the server
    print("📝 Creating example MCP server...")
    server_code = create_example_server()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(server_code)
        server_file = f.name
    
    print(f"📄 Server file: {server_file}")
    
    try:
        # Set up stdio parameters
        print("🔧 Setting up stdio parameters...")
        server_params = StdioParameters(
            command="python",
            args=[server_file]
        )
        
        print(f"   Command: {server_params.command}")
        print(f"   Args: {server_params.args}")
        
        # Connect and run example
        print("\\n📡 Connecting to stdio server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("   ✅ Connection established!")
            
            # 1. Initialize
            print("\\n1️⃣  Initializing connection...")
            init_result = await send_initialize(read_stream, write_stream)
            print(f"   ✅ Server: {init_result.serverInfo.name}")
            print(f"   📋 Protocol: {init_result.protocolVersion}")
            print(f"   💡 Instructions: {init_result.instructions}")
            
            # 2. Test ping
            print("\\n2️⃣  Testing connectivity...")
            ping_success = await send_ping(read_stream, write_stream)
            print(f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}")
            
            # 3. Explore tools
            print("\\n3️⃣  Exploring available tools...")
            tools_response = await send_tools_list(read_stream, write_stream)
            tools = tools_response["tools"]
            print(f"   📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description']}")
            
            # 4. Use tools
            print("\\n4️⃣  Using tools...")
            
            # Greet with different styles
            print("   🤝 Testing greeting tool...")
            for style in ["casual", "formal", "enthusiastic"]:
                greet_response = await send_tools_call(
                    read_stream, write_stream,
                    "greet", {"name": "Alice", "style": style}
                )
                result = greet_response["content"][0]["text"]
                print(f"      {style}: {result}")
            
            # Add some notes
            print("   📝 Adding notes...")
            notes = [
                {"content": "Remember to test all transport types", "category": "development"},
                {"content": "SSE support is working great", "category": "progress"},
                {"content": "Documentation needs updating", "category": "todo"}
            ]
            
            for note in notes:
                note_response = await send_tools_call(
                    read_stream, write_stream,
                    "add_note", note
                )
                print(f"      {note_response['content'][0]['text']}")
            
            # Increment counter
            print("   🔢 Testing counter...")
            counter_response = await send_tools_call(
                read_stream, write_stream,
                "increment_counter", {"amount": 5}
            )
            print(f"      {counter_response['content'][0]['text']}")
            
            # Generate UUID
            print("   🆔 Generating UUID...")
            uuid_response = await send_tools_call(
                read_stream, write_stream,
                "generate_uuid", {"version": 4}
            )
            print(f"      {uuid_response['content'][0]['text']}")
            
            # 5. Explore resources
            print("\\n5️⃣  Exploring resources...")
            resources_response = await send_resources_list(read_stream, write_stream)
            resources = resources_response["resources"]
            print(f"   📂 Found {len(resources)} resources:")
            for resource in resources:
                print(f"      • {resource['name']}: {resource['description']}")
            
            # Read resources
            print("   📖 Reading resources...")
            for resource in resources:
                uri = resource["uri"]
                content_response = await send_resources_read(read_stream, write_stream, uri)
                content = content_response["contents"][0]["text"]
                print(f"      {resource['name']}:")
                if resource.get("mimeType") == "application/json":
                    # Pretty print JSON
                    import json
                    data = json.loads(content)
                    print(f"         {json.dumps(data, indent=8)}")
                else:
                    # Show first few lines of text
                    lines = content.split('\\n')[:3]
                    for line in lines:
                        print(f"         {line}")
                    if len(content.split('\\n')) > 3:
                        print("         ...")
            
            # 6. Explore prompts
            print("\\n6️⃣  Exploring prompts...")
            prompts_response = await send_prompts_list(read_stream, write_stream)
            prompts = prompts_response["prompts"]
            print(f"   📝 Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"      • {prompt['name']}: {prompt['description']}")
            
            # Get prompts
            print("   💬 Getting prompts...")
            
            # Note summary prompt
            summary_prompt = await send_prompts_get(
                read_stream, write_stream,
                "note_summary", {"format": "detailed"}
            )
            print(f"      Notes Summary: {summary_prompt['description']}")
            print(f"         Content: {summary_prompt['messages'][0]['content']['text'][:100]}...")
            
            # Greeting template prompt
            greeting_prompt = await send_prompts_get(
                read_stream, write_stream,
                "greeting_template", {"occasion": "birthday", "formality": "casual"}
            )
            print(f"      Greeting Template: {greeting_prompt['description']}")
            print(f"         Content: {greeting_prompt['messages'][0]['content']['text']}")
        
        print("\\n🎉 Stdio client example completed successfully!")
        print("\\n📊 Summary:")
        print("   ✅ Connection via subprocess stdio")
        print("   ✅ Protocol initialization and handshake")
        print("   ✅ Tool discovery and execution")
        print("   ✅ Resource listing and reading")
        print("   ✅ Prompt listing and retrieval")
        print("   ✅ Clean connection teardown")
        
    except Exception as e:
        print(f"\\n❌ Error during stdio example: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # Clean up
        if os.path.exists(server_file):
            try:
                os.unlink(server_file)
                print(f"🧹 Cleaned up server file")
            except Exception as e:
                print(f"⚠️  Could not clean up {server_file}: {e}")


def main():
    """Main entry point."""
    print("🚀 chuk-mcp Stdio Client E2E Example")
    print("=" * 60)
    print("Demonstrating complete stdio transport functionality")
    print("=" * 60)
    
    try:
        anyio.run(run_stdio_example)
        print("\\n" + "=" * 60)
        print("🎉 Success! Stdio transport is working perfectly!")
        print("\\n📚 What this demonstrates:")
        print("   ✅ StdioParameters configuration")
        print("   ✅ stdio_client context manager")
        print("   ✅ Subprocess server communication")
        print("   ✅ Full MCP protocol implementation")
        print("   ✅ Tools, resources, and prompts")
        print("   ✅ Error handling and cleanup")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\\n\\n👋 Example interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\\n💥 Example failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()