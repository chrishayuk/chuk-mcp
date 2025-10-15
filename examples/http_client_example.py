#!/usr/bin/env python3
"""
E2E Example: HTTP Client with MCP Server

This script demonstrates a complete working example of using the chuk-mcp
HTTP client to connect to and interact with an MCP server via HTTP requests.
"""

import sys
import logging
import time

import anyio

# chuk-mcp imports
from chuk_mcp.transports.http import http_client
from chuk_mcp.transports.http.parameters import HTTPParameters
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


def create_http_server_example():
    """Create an example HTTP MCP server implementation using FastAPI."""
    return '''#!/usr/bin/env python3
"""
Example HTTP MCP Server using FastAPI

This server demonstrates HTTP transport for MCP protocol with stateless request/response.
Run this server first, then run the HTTP client example.

Usage:
    pip install fastapi uvicorn
    python http_server_example.py
    # Then run the HTTP client example
"""

import json
import uuid
import datetime
from typing import Dict, Any, Optional
import logging

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("❌ FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HTTP MCP Server Example", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global server state (in real implementation, use database or cache)
class ServerState:
    def __init__(self):
        self.server_info = {
            "name": "http-example-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True},
            "prompts": {"listChanged": True}
        }
        self.counters = {}  # session_id -> counter value
        self.data_store = {}  # session_id -> session data
        self.request_count = 0

state = ServerState()

@app.get("/")
async def root():
    return {
        "message": "HTTP MCP Server", 
        "version": "1.0.0", 
        "transport": "http",
        "requests_handled": state.request_count
    }

@app.post("/mcp")
async def handle_mcp_message(request: Request):
    """Handle MCP JSON-RPC messages via HTTP POST."""
    
    state.request_count += 1
    
    try:
        message = await request.json()
        logger.info(f"Received HTTP MCP message: {message.get('method')} (request #{state.request_count})")
        
        # Extract session info from headers or generate new one
        session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
        
        response = await handle_mcp_message_logic(message, session_id)
        
        if response:
            logger.info(f"Sending HTTP response: {response.get('result', response.get('error'))}")
            return response
        else:
            # Notification - return accepted status
            return JSONResponse(status_code=202, content={"status": "accepted"})
            
    except Exception as e:
        logger.error(f"Error handling HTTP MCP message: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if 'message' in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
        )

async def handle_mcp_message_logic(message: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    """Handle MCP protocol messages with HTTP-specific logic."""
    
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})
    
    # Initialize session data if needed
    if session_id not in state.data_store:
        state.data_store[session_id] = {
            "created": datetime.datetime.now().isoformat(),
            "requests": 0,
            "notes": []
        }
        state.counters[session_id] = 0
    
    session_data = state.data_store[session_id]
    session_data["requests"] += 1
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": state.capabilities,
                    "serverInfo": state.server_info,
                    "instructions": f"HTTP MCP Server - Session: {session_id}"
                }
            }
        
        elif method == "notifications/initialized":
            logger.info(f"Client initialization complete for HTTP session {session_id}")
            return None
        
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"timestamp": datetime.datetime.now().isoformat()}}
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "http_greet",
                            "description": "Greet someone via HTTP transport",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name to greet"},
                                    "style": {"type": "string", "enum": ["formal", "casual", "technical"], "default": "casual"}
                                },
                                "required": ["name"]
                            }
                        },
                        {
                            "name": "http_counter",
                            "description": "HTTP session counter operations",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string", "enum": ["increment", "decrement", "reset", "get"], "default": "increment"},
                                    "amount": {"type": "integer", "default": 1}
                                }
                            }
                        },
                        {
                            "name": "add_http_note",
                            "description": "Add a note to HTTP session storage",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string", "description": "Note content"},
                                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "http_request_info",
                            "description": "Get information about HTTP requests",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "detail_level": {"type": "string", "enum": ["basic", "detailed"], "default": "basic"}
                                }
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "http_greet":
                name = arguments.get("name", "Anonymous")
                style = arguments.get("style", "casual")
                
                greetings = {
                    "formal": f"Greetings, {name}. This message was delivered via HTTP transport.",
                    "casual": f"Hey {name}! 🚀 HTTP delivery in action! 📡",
                    "technical": f"HTTP 200 OK: Greeting payload for user '{name}' successfully processed via RESTful MCP transport layer."
                }
                
                greeting = greetings.get(style, greetings["casual"])
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": greeting}]
                    }
                }
            
            elif tool_name == "http_counter":
                action = arguments.get("action", "increment")
                amount = arguments.get("amount", 1)
                
                if action == "increment":
                    state.counters[session_id] += amount
                    result_text = f"🔢 HTTP Counter incremented by {amount}. New value: {state.counters[session_id]}"
                elif action == "decrement":
                    state.counters[session_id] -= amount
                    result_text = f"🔢 HTTP Counter decremented by {amount}. New value: {state.counters[session_id]}"
                elif action == "reset":
                    state.counters[session_id] = 0
                    result_text = f"🔢 HTTP Counter reset to 0"
                elif action == "get":
                    result_text = f"🔢 HTTP Counter current value: {state.counters[session_id]}"
                else:
                    result_text = f"❌ Unknown counter action: {action}"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}]
                    }
                }
            
            elif tool_name == "add_http_note":
                content = arguments.get("content", "")
                priority = arguments.get("priority", "medium")
                
                note = {
                    "id": len(session_data["notes"]) + 1,
                    "content": content,
                    "priority": priority,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "transport": "http"
                }
                session_data["notes"].append(note)
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"📝 HTTP Note #{note['id']} added with {priority} priority: {content}"}]
                    }
                }
            
            elif tool_name == "http_request_info":
                detail_level = arguments.get("detail_level", "basic")
                
                if detail_level == "detailed":
                    info = {
                        "session_id": session_id,
                        "total_server_requests": state.request_count,
                        "session_requests": session_data["requests"],
                        "session_created": session_data["created"],
                        "counter_value": state.counters[session_id],
                        "notes_count": len(session_data["notes"]),
                        "transport": "http",
                        "protocol": "JSON-RPC 2.0 over HTTP",
                        "active_sessions": len(state.data_store)
                    }
                    result_text = f"📊 Detailed HTTP Info:\\n{json.dumps(info, indent=2)}"
                else:
                    result_text = f"📊 HTTP Info: Session {session_id[:8]}..., Request #{session_data['requests']}, Counter: {state.counters[session_id]}"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}]
                    }
                }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "http://server-metrics",
                            "name": "HTTP Server Metrics",
                            "description": "Performance and usage metrics for the HTTP MCP server",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": f"http://session-{session_id}",
                            "name": "HTTP Session Data",
                            "description": "Data specific to this HTTP session",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "http://server-info",
                            "name": "HTTP Server Information",
                            "description": "Technical details about the HTTP MCP server",
                            "mimeType": "text/plain"
                        }
                    ]
                }
            }
        
        elif method == "resources/read":
            uri = params.get("uri")
            
            if uri == "http://server-metrics":
                metrics = {
                    "server": state.server_info,
                    "transport": "http",
                    "total_requests": state.request_count,
                    "active_sessions": len(state.data_store),
                    "capabilities": state.capabilities,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "uptime_info": "Server running since startup"
                }
                content = json.dumps(metrics, indent=2)
                mime_type = "application/json"
            
            elif uri == f"http://session-{session_id}":
                session_info = {
                    "session_id": session_id,
                    "session_data": session_data,
                    "counter": state.counters[session_id],
                    "transport": "http",
                    "last_request": datetime.datetime.now().isoformat()
                }
                content = json.dumps(session_info, indent=2)
                mime_type = "application/json"
            
            elif uri == "http://server-info":
                server_details = f"""🌐 HTTP MCP Server Information

Server: {state.server_info['name']} v{state.server_info['version']}
Transport: HTTP/1.1 with JSON-RPC 2.0
Protocol: Model Context Protocol (MCP)

📊 Statistics:
• Total Requests: {state.request_count}
• Active Sessions: {len(state.data_store)}
• Current Session: {session_id}
• Session Requests: {session_data['requests']}

🔧 Capabilities:
• Tools: ✅ ({len([t for t in []])})
• Resources: ✅ 
• Prompts: ✅
• HTTP Transport: ✅
• Session Management: ✅
• Stateless Operations: ✅

🚀 Features:
• RESTful MCP communication
• Session-based state management
• Concurrent request handling
• JSON-RPC 2.0 compliance
• CORS enabled for web clients
"""
                content = server_details
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
                            "name": "http_session_summary",
                            "description": "Generate a summary of HTTP session activity",
                            "arguments": [
                                {"name": "include_notes", "description": "Whether to include notes in summary", "required": False}
                            ]
                        },
                        {
                            "name": "api_documentation",
                            "description": "Generate API documentation for HTTP endpoints",
                            "arguments": [
                                {"name": "format", "description": "Documentation format (markdown/json)", "required": False}
                            ]
                        }
                    ]
                }
            }
        
        elif method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if prompt_name == "http_session_summary":
                include_notes = arguments.get("include_notes", "true").lower() == "true"
                
                base_prompt = f"Please create a summary of this HTTP MCP session with {session_data['requests']} requests and counter value {state.counters[session_id]}."
                
                if include_notes and session_data["notes"]:
                    base_prompt += f" The session includes {len(session_data['notes'])} notes. "
                    base_prompt += "Notes:\\n"
                    for note in session_data["notes"]:
                        base_prompt += f"- [{note['priority']}] {note['content']}\\n"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "description": f"HTTP session summary ({'with' if include_notes else 'without'} notes)",
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": base_prompt}}
                        ]
                    }
                }
            
            elif prompt_name == "api_documentation":
                format_type = arguments.get("format", "markdown")
                
                if format_type == "json":
                    prompt_text = f"Please create JSON-formatted API documentation for this HTTP MCP server, including all {len(state.capabilities)} capabilities and endpoint specifications."
                else:
                    prompt_text = f"Please create comprehensive Markdown documentation for this HTTP MCP server API, covering all endpoints, request/response formats, and usage examples."
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "description": f"API documentation prompt ({format_type} format)",
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": prompt_text}}
                        ]
                    }
                }
    
    except Exception as e:
        logger.error(f"Error in handle_mcp_message_logic: {e}")
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }
    
    return {
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }

if __name__ == "__main__":
    print("🌐 Starting HTTP MCP Server Example...")
    print("📡 Server will be available at: http://localhost:8001")
    print("🔗 MCP endpoint: http://localhost:8001/mcp")
    print("🏠 Server info: http://localhost:8001/")
    print("\\n🚀 Starting server...")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server error: {e}")
        sys.exit(1)
'''


async def run_http_example():
    """Run the complete HTTP client example."""
    print("🌐 HTTP Client E2E Example")
    print("=" * 50)

    # Check if server is running
    print("🔍 Checking if HTTP server is available...")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/", timeout=5.0)
            if response.status_code == 200:
                server_info = response.json()
                print(f"   ✅ Server found: {server_info.get('message', 'Unknown')}")
                print(
                    f"   📊 Requests handled: {server_info.get('requests_handled', 0)}"
                )
            else:
                raise Exception(f"Server returned status {response.status_code}")
    except Exception as e:
        print("   ❌ HTTP server not available at http://localhost:8001")
        print(f"   Error: {e}")
        print("\\n💡 To run this example:")
        print("   1. Install FastAPI and uvicorn: pip install fastapi uvicorn")
        print("   2. Save the HTTP server code to 'http_server_example.py'")
        print("   3. Run: python http_server_example.py")
        print("   4. Then run this client example")
        print("\\n📄 HTTP Server code:")
        print("-" * 50)
        print(create_http_server_example())
        return

    try:
        # Set up HTTP parameters
        print("🔧 Setting up HTTP parameters...")
        http_params = HTTPParameters(
            url="http://localhost:8001/mcp",
            timeout=30.0,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Session-ID": f"http-client-{int(time.time())}",
            },
        )

        print(f"   URL: {http_params.url}")
        print(f"   Method: {http_params.method}")
        print(f"   Timeout: {http_params.timeout}s")
        print(f"   Session ID: {http_params.headers.get('X-Session-ID')}")

        # Connect and run example
        print("\\n📡 Connecting to HTTP server...")
        async with http_client(http_params) as (read_stream, write_stream):
            print("   ✅ HTTP connection established!")

            # 1. Initialize
            print("\\n1️⃣  Initializing connection...")
            init_result = await send_initialize(read_stream, write_stream)
            print(f"   ✅ Server: {init_result.serverInfo.name}")
            print(f"   📋 Protocol: {init_result.protocolVersion}")
            print(f"   💡 Instructions: {init_result.instructions}")

            # 2. Test ping
            print("\\n2️⃣  Testing connectivity...")
            ping_success = await send_ping(read_stream, write_stream)
            print(
                f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}"
            )

            # 3. Explore tools
            print("\\n3️⃣  Exploring HTTP-specific tools...")
            tools_response = await send_tools_list(read_stream, write_stream)
            tools = tools_response["tools"]
            print(f"   📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description']}")

            # 4. Use HTTP-specific tools
            print("\\n4️⃣  Using HTTP tools...")

            # HTTP Greeting with different styles
            print("   👋 Testing HTTP greeting...")
            for style in ["casual", "formal", "technical"]:
                greet_response = await send_tools_call(
                    read_stream,
                    write_stream,
                    "http_greet",
                    {"name": f"HTTP-{style.title()}-User", "style": style},
                )
                result = greet_response["content"][0]["text"]
                print(f"      {style}: {result}")

            # Counter operations
            print("   🔢 Testing HTTP counter operations...")
            operations = [
                {"action": "increment", "amount": 5},
                {"action": "increment", "amount": 3},
                {"action": "get"},
                {"action": "decrement", "amount": 2},
                {"action": "get"},
            ]

            for op in operations:
                counter_response = await send_tools_call(
                    read_stream, write_stream, "http_counter", op
                )
                print(f"      {counter_response['content'][0]['text']}")

            # Add notes
            print("   📝 Adding HTTP notes...")
            notes = [
                {"content": "HTTP transport working perfectly", "priority": "high"},
                {"content": "Session management is stateful", "priority": "medium"},
                {"content": "Need to test concurrent requests", "priority": "low"},
            ]

            for note in notes:
                note_response = await send_tools_call(
                    read_stream, write_stream, "add_http_note", note
                )
                print(f"      {note_response['content'][0]['text']}")

            # Request information
            print("   📊 Getting HTTP request information...")
            for detail_level in ["basic", "detailed"]:
                info_response = await send_tools_call(
                    read_stream,
                    write_stream,
                    "http_request_info",
                    {"detail_level": detail_level},
                )
                print(
                    f"      {detail_level}: {info_response['content'][0]['text'][:100]}..."
                )

            # 5. Explore resources
            print("\\n5️⃣  Exploring HTTP resources...")
            resources_response = await send_resources_list(read_stream, write_stream)
            resources = resources_response["resources"]
            print(f"   📂 Found {len(resources)} resources:")
            for resource in resources:
                print(f"      • {resource['name']}: {resource['description']}")

            # Read resources
            print("   📖 Reading HTTP resources...")
            for resource in resources:
                uri = resource["uri"]
                content_response = await send_resources_read(
                    read_stream, write_stream, uri
                )
                content = content_response["contents"][0]["text"]
                print(f"      {resource['name']}:")
                if resource.get("mimeType") == "application/json":
                    # Pretty print JSON
                    import json

                    data = json.loads(content)
                    # Show first few keys for brevity
                    preview = {k: v for i, (k, v) in enumerate(data.items()) if i < 3}
                    print(f"         {json.dumps(preview, indent=8)}")
                    if len(data) > 3:
                        print("         ... (more data)")
                else:
                    # Show first few lines of text
                    lines = content.split("\\n")[:4]
                    for line in lines:
                        if line.strip():
                            print(f"         {line}")
                    if len(content.split("\\n")) > 4:
                        print("         ...")

            # 6. Explore prompts
            print("\\n6️⃣  Exploring HTTP prompts...")
            prompts_response = await send_prompts_list(read_stream, write_stream)
            prompts = prompts_response["prompts"]
            print(f"   📝 Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"      • {prompt['name']}: {prompt['description']}")

            # Get prompts
            print("   💬 Getting HTTP prompts...")

            # Session summary prompt
            session_prompt = await send_prompts_get(
                read_stream,
                write_stream,
                "http_session_summary",
                {"include_notes": "true"},
            )
            print(f"      Session Summary: {session_prompt['description']}")
            print(
                f"         Content: {session_prompt['messages'][0]['content']['text'][:150]}..."
            )

            # API documentation prompt
            api_prompt = await send_prompts_get(
                read_stream, write_stream, "api_documentation", {"format": "markdown"}
            )
            print(f"      API Documentation: {api_prompt['description']}")
            print(
                f"         Content: {api_prompt['messages'][0]['content']['text'][:100]}..."
            )

            # 7. Test concurrent HTTP operations
            print("\\n7️⃣  Testing concurrent HTTP operations...")

            start_time = time.time()

            async with anyio.create_task_group() as tg:
                results = []

                async def concurrent_ping():
                    result = await send_ping(read_stream, write_stream)
                    results.append(f"Ping: {'✅' if result else '❌'}")

                async def concurrent_counter():
                    _response = await send_tools_call(
                        read_stream,
                        write_stream,
                        "http_counter",
                        {"action": "increment", "amount": 1},
                    )
                    results.append("Counter: ✅")

                async def concurrent_info():
                    _response = await send_tools_call(
                        read_stream,
                        write_stream,
                        "http_request_info",
                        {"detail_level": "basic"},
                    )
                    results.append("Info: ✅")

                async def concurrent_tools():
                    response = await send_tools_list(read_stream, write_stream)
                    results.append(f"Tools: ✅ ({len(response['tools'])})")

                # Start concurrent operations
                for _ in range(2):  # Run each operation twice
                    tg.start_soon(concurrent_ping)
                    tg.start_soon(concurrent_counter)
                    tg.start_soon(concurrent_info)
                    tg.start_soon(concurrent_tools)

            elapsed = time.time() - start_time
            print(f"   📊 Concurrent operation results (completed in {elapsed:.2f}s):")
            for result in sorted(results):
                print(f"      {result}")

            print(f"   ⚡ Throughput: {len(results)/elapsed:.1f} operations/second")

        print("\\n🎉 HTTP client example completed successfully!")
        print("\\n📊 Summary:")
        print("   ✅ Connection via HTTP POST requests")
        print("   ✅ RESTful JSON-RPC communication")
        print("   ✅ Session management via headers")
        print("   ✅ Stateless request/response model")
        print("   ✅ High-throughput concurrent operations")
        print("   ✅ Clean connection handling")

    except Exception as e:
        print(f"\\n❌ Error during HTTP example: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


def main():
    """Main entry point."""
    print("🌐 chuk-mcp HTTP Client E2E Example")
    print("=" * 60)
    print("Demonstrating complete HTTP transport functionality")
    print("=" * 60)

    try:
        anyio.run(run_http_example)
        print("\\n" + "=" * 60)
        print("🎉 Success! HTTP transport is working perfectly!")
        print("\\n📚 What this demonstrates:")
        print("   ✅ HTTPParameters configuration")
        print("   ✅ http_client context manager")
        print("   ✅ RESTful HTTP communication")
        print("   ✅ JSON-RPC over HTTP")
        print("   ✅ Session management via headers")
        print("   ✅ High-performance concurrent requests")
        print("   ✅ Stateless server architecture")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\\n\\n👋 Example interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\\n💥 Example failed: {str(e)}")
        print("\\nMake sure the HTTP server is running first!")
        sys.exit(1)


if __name__ == "__main__":
    main()
