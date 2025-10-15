#!/usr/bin/env python3
"""
E2E Example: SSE Client with MCP Server

This script demonstrates a complete working example of using the chuk-mcp
SSE client to connect to and interact with an MCP server via Server-Sent Events.
"""

import sys
import logging

import anyio

# chuk-mcp imports
from chuk_mcp.transports.sse import sse_client
from chuk_mcp.transports.sse.parameters import SSEParameters
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


def create_sse_server_example():
    """Create an example SSE server implementation using FastAPI."""
    return '''#!/usr/bin/env python3
"""
Example SSE MCP Server using FastAPI

This server demonstrates SSE transport for MCP protocol.
Run this server first, then run the SSE client example.

Usage:
    pip install fastapi uvicorn
    python sse_server_example.py
    # Then run the SSE client example
"""

import asyncio
import json
import uuid
import datetime
from typing import Dict, Any, Optional
import logging

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("❌ FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SSE MCP Server Example", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global server state
class ServerState:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.server_info = {
            "name": "sse-example-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True},
            "prompts": {"listChanged": True}
        }

state = ServerState()

@app.get("/")
async def root():
    return {"message": "SSE MCP Server", "version": "1.0.0", "transport": "sse"}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint that provides the message endpoint URL."""
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Initialize session
    state.sessions[session_id] = {
        "id": session_id,
        "created": datetime.datetime.now().isoformat(),
        "counter": 0,
        "messages": [],
        "initialized": False
    }
    
    logger.info(f"New SSE session: {session_id}")
    
    async def event_stream():
        # Send the message endpoint URL (must end with /mcp for MCP protocol compliance)
        endpoint_url = f"/mcp?session_id={session_id}"
        yield f"event: endpoint\\n"
        yield f"data: {endpoint_url}\\n\\n"
        
        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(30)  # Send keepalive every 30 seconds
                yield f"event: keepalive\\n"
                yield f"data: {json.dumps({'timestamp': datetime.datetime.now().isoformat()})}\\n\\n"
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for session {session_id}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/mcp")
async def handle_message(request: Request):
    """Handle MCP JSON-RPC messages via standard /mcp endpoint."""
    
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in state.sessions:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid or missing session_id"}
        )
    
    session = state.sessions[session_id]
    
    try:
        message = await request.json()
        logger.info(f"Received message: {message.get('method')} (session: {session_id})")
        
        response = await handle_mcp_message(message, session)
        if response:
            logger.info(f"Sending response: {response.get('result', response.get('error'))}")
            return response
        else:
            # Notification - no response
            return JSONResponse(status_code=202, content={"status": "accepted"})
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if 'message' in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
        )

async def handle_mcp_message(message: Dict[str, Any], session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle MCP protocol messages."""
    
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})
    
    try:
        if method == "initialize":
            session["initialized"] = True
            session["client_info"] = params.get("clientInfo", {})
            
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": state.capabilities,
                    "serverInfo": state.server_info,
                    "instructions": f"SSE MCP Server - Session: {session['id']}"
                }
            }
        
        elif method == "notifications/initialized":
            logger.info(f"Client initialization complete for session {session['id']}")
            return None
        
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "sse_greet",
                            "description": "Greet someone via SSE transport",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name to greet"},
                                    "message": {"type": "string", "description": "Custom message", "default": "Hello"}
                                },
                                "required": ["name"]
                            }
                        },
                        {
                            "name": "session_info",
                            "description": "Get current session information",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "sse_counter",
                            "description": "Increment session counter",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "increment": {"type": "integer", "default": 1}
                                }
                            }
                        },
                        {
                            "name": "broadcast_test",
                            "description": "Test SSE broadcasting capability",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string", "description": "Message to broadcast"}
                                },
                                "required": ["message"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "sse_greet":
                name = arguments.get("name", "Anonymous")
                custom_message = arguments.get("message", "Hello")
                
                greeting = f"🌊 {custom_message}, {name}! Greetings via SSE transport! 📡"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": greeting}]
                    }
                }
            
            elif tool_name == "session_info":
                info = {
                    "session_id": session["id"],
                    "created": session["created"],
                    "counter": session["counter"],
                    "transport": "sse",
                    "initialized": session["initialized"],
                    "total_sessions": len(state.sessions)
                }
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"📊 Session Info: {json.dumps(info, indent=2)}"}]
                    }
                }
            
            elif tool_name == "sse_counter":
                increment = arguments.get("increment", 1)
                session["counter"] += increment
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"🔢 SSE Counter: {session['counter']} (+{increment})"}]
                    }
                }
            
            elif tool_name == "broadcast_test":
                message_text = arguments.get("message", "Test message")
                
                # In a real implementation, this would broadcast to all connected clients
                broadcast_info = f"📢 Broadcasting: '{message_text}' to {len(state.sessions)} session(s)"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": broadcast_info}]
                    }
                }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "sse://server-status",
                            "name": "SSE Server Status",
                            "description": "Current SSE server status and metrics",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": f"sse://session-{session['id']}",
                            "name": "Current Session",
                            "description": "Information about the current SSE session",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "sse://connections",
                            "name": "Active Connections",
                            "description": "List of active SSE connections",
                            "mimeType": "text/plain"
                        }
                    ]
                }
            }
        
        elif method == "resources/read":
            uri = params.get("uri")
            
            if uri == "sse://server-status":
                status = {
                    "server": state.server_info,
                    "transport": "sse",
                    "active_sessions": len(state.sessions),
                    "capabilities": state.capabilities,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                content = json.dumps(status, indent=2)
                mime_type = "application/json"
            
            elif uri == f"sse://session-{session['id']}":
                session_data = {
                    "session": session,
                    "transport": "sse",
                    "endpoint": f"/mcp?session_id={session['id']}"
                }
                content = json.dumps(session_data, indent=2)
                mime_type = "application/json"
            
            elif uri == "sse://connections":
                connections_info = f"""🌐 SSE Server Connections

Active Sessions: {len(state.sessions)}
Server: {state.server_info['name']} v{state.server_info['version']}
Transport: Server-Sent Events (SSE)
Protocol: HTTP/1.1 with SSE extensions

Session Details:
"""
                for sid, sess in state.sessions.items():
                    connections_info += f"  • {sid}: Created {sess['created']} (Counter: {sess['counter']})\\n"
                
                content = connections_info
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
                            "name": "sse_status_report",
                            "description": "Generate an SSE connection status report",
                            "arguments": [
                                {"name": "detail_level", "description": "Level of detail (basic/detailed)", "required": False}
                            ]
                        },
                        {
                            "name": "realtime_prompt",
                            "description": "Generate a prompt about real-time communication",
                            "arguments": [
                                {"name": "topic", "description": "Communication topic", "required": True}
                            ]
                        }
                    ]
                }
            }
        
        elif method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if prompt_name == "sse_status_report":
                detail_level = arguments.get("detail_level", "basic")
                
                if detail_level == "detailed":
                    prompt_text = f"Please create a comprehensive status report for the SSE MCP server, including analysis of {len(state.sessions)} active sessions, performance metrics, and recommendations."
                else:
                    prompt_text = f"Please create a brief status summary for the SSE MCP server with {len(state.sessions)} active sessions."
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "description": f"SSE status report prompt ({detail_level})",
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": prompt_text}}
                        ]
                    }
                }
            
            elif prompt_name == "realtime_prompt":
                topic = arguments.get("topic", "communication")
                
                prompt_text = f"Please explain the benefits and implementation details of real-time {topic} using Server-Sent Events (SSE) technology, including best practices and common use cases."
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "description": f"Real-time communication prompt about {topic}",
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": prompt_text}}
                        ]
                    }
                }
    
    except Exception as e:
        logger.error(f"Error in handle_mcp_message: {e}")
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }
    
    return {
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }

if __name__ == "__main__":
    import sys
    
    print("🌊 Starting SSE MCP Server Example...")
    print("📡 Server will be available at: http://localhost:8000")
    print("🔗 SSE endpoint: http://localhost:8000/sse")
    print("📬 Messages endpoint: http://localhost:8000/mcp")
    print("\\n🚀 Starting server...")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server error: {e}")
        sys.exit(1)
'''


async def run_sse_example():
    """Run the complete SSE client example."""
    print("🌊 SSE Client E2E Example")
    print("=" * 50)

    # Check if server is running
    print("🔍 Checking if SSE server is available...")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/", timeout=5.0)
            if response.status_code == 200:
                server_info = response.json()
                print(f"   ✅ Server found: {server_info.get('message', 'Unknown')}")
            else:
                raise Exception(f"Server returned status {response.status_code}")
    except Exception as e:
        print("   ❌ SSE server not available at http://localhost:8000")
        print(f"   Error: {e}")
        print("\\n💡 To run this example:")
        print("   1. Install FastAPI and uvicorn: pip install fastapi uvicorn")
        print("   2. Save the SSE server code to 'sse_server_example.py'")
        print("   3. Run: python sse_server_example.py")
        print("   4. Then run this client example")
        print("\\n📄 SSE Server code:")
        print("-" * 50)
        print(create_sse_server_example())
        return

    try:
        # Set up SSE parameters
        print("🔧 Setting up SSE parameters...")
        sse_params = SSEParameters(
            url="http://localhost:8000",
            timeout=30.0,
            auto_reconnect=True,
            max_reconnect_attempts=3,
        )

        print(f"   URL: {sse_params.url}")
        print(f"   Timeout: {sse_params.timeout}s")
        print(f"   Auto-reconnect: {sse_params.auto_reconnect}")

        # Connect and run example
        print("\\n📡 Connecting to SSE server...")
        async with sse_client(sse_params) as (read_stream, write_stream):
            print("   ✅ SSE connection established!")

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
            print("\\n3️⃣  Exploring SSE-specific tools...")
            tools_response = await send_tools_list(read_stream, write_stream)
            tools = tools_response["tools"]
            print(f"   📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description']}")

            # 4. Use SSE-specific tools
            print("\\n4️⃣  Using SSE tools...")

            # SSE Greeting
            print("   👋 Testing SSE greeting...")
            greet_response = await send_tools_call(
                read_stream,
                write_stream,
                "sse_greet",
                {"name": "SSE User", "message": "Welcome"},
            )
            result = greet_response["content"][0]["text"]
            print(f"      {result}")

            # Session info
            print("   📊 Getting session information...")
            session_response = await send_tools_call(
                read_stream, write_stream, "session_info", {}
            )
            session_info = session_response["content"][0]["text"]
            print(f"      {session_info}")

            # Counter test
            print("   🔢 Testing SSE counter...")
            counter_response = await send_tools_call(
                read_stream, write_stream, "sse_counter", {"increment": 3}
            )
            print(f"      {counter_response['content'][0]['text']}")

            # Broadcast test
            print("   📢 Testing broadcast capability...")
            broadcast_response = await send_tools_call(
                read_stream,
                write_stream,
                "broadcast_test",
                {"message": "Hello from SSE client!"},
            )
            print(f"      {broadcast_response['content'][0]['text']}")

            # 5. Explore resources
            print("\\n5️⃣  Exploring SSE resources...")
            resources_response = await send_resources_list(read_stream, write_stream)
            resources = resources_response["resources"]
            print(f"   📂 Found {len(resources)} resources:")
            for resource in resources:
                print(f"      • {resource['name']}: {resource['description']}")

            # Read resources
            print("   📖 Reading SSE resources...")
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
                    print(f"         {json.dumps(data, indent=8)}")
                else:
                    # Show first few lines of text
                    lines = content.split("\\n")[:3]
                    for line in lines:
                        if line.strip():
                            print(f"         {line}")
                    if len(content.split("\\n")) > 3:
                        print("         ...")

            # 6. Explore prompts
            print("\\n6️⃣  Exploring SSE prompts...")
            prompts_response = await send_prompts_list(read_stream, write_stream)
            prompts = prompts_response["prompts"]
            print(f"   📝 Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"      • {prompt['name']}: {prompt['description']}")

            # Get prompts
            print("   💬 Getting SSE prompts...")

            # Status report prompt
            status_prompt = await send_prompts_get(
                read_stream,
                write_stream,
                "sse_status_report",
                {"detail_level": "detailed"},
            )
            print(f"      Status Report: {status_prompt['description']}")
            print(
                f"         Content: {status_prompt['messages'][0]['content']['text'][:100]}..."
            )

            # Real-time prompt
            realtime_prompt = await send_prompts_get(
                read_stream,
                write_stream,
                "realtime_prompt",
                {"topic": "data streaming"},
            )
            print(f"      Real-time Prompt: {realtime_prompt['description']}")
            print(
                f"         Content: {realtime_prompt['messages'][0]['content']['text'][:100]}..."
            )

            # 7. Test concurrent operations over SSE
            print("\\n7️⃣  Testing concurrent SSE operations...")

            async with anyio.create_task_group() as tg:
                results = []

                async def concurrent_ping():
                    result = await send_ping(read_stream, write_stream)
                    results.append(f"Ping: {'✅' if result else '❌'}")

                async def concurrent_counter():
                    _response = await send_tools_call(
                        read_stream, write_stream, "sse_counter", {"increment": 1}
                    )
                    results.append("Counter: ✅")

                async def concurrent_tools_list():
                    response = await send_tools_list(read_stream, write_stream)
                    results.append(f"Tools: ✅ ({len(response['tools'])})")

                # Start concurrent operations
                tg.start_soon(concurrent_ping)
                tg.start_soon(concurrent_counter)
                tg.start_soon(concurrent_tools_list)

            print("   📊 Concurrent operation results:")
            for result in results:
                print(f"      {result}")

        print("\\n🎉 SSE client example completed successfully!")
        print("\\n📊 Summary:")
        print("   ✅ Connection via Server-Sent Events")
        print("   ✅ HTTP-based message posting")
        print("   ✅ Session management")
        print("   ✅ Real-time communication capabilities")
        print("   ✅ Concurrent operations over SSE")
        print("   ✅ Clean connection teardown")

    except Exception as e:
        print(f"\\n❌ Error during SSE example: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


def main():
    """Main entry point."""
    print("🌊 chuk-mcp SSE Client E2E Example")
    print("=" * 60)
    print("Demonstrating complete SSE transport functionality")
    print("=" * 60)

    try:
        anyio.run(run_sse_example)
        print("\\n" + "=" * 60)
        print("🎉 Success! SSE transport is working perfectly!")
        print("\\n📚 What this demonstrates:")
        print("   ✅ SSEParameters configuration")
        print("   ✅ sse_client context manager")
        print("   ✅ Server-Sent Events communication")
        print("   ✅ HTTP POST message handling")
        print("   ✅ Session management")
        print("   ✅ Real-time capabilities")
        print("   ✅ Error handling and reconnection")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\\n\\n👋 Example interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\\n💥 Example failed: {str(e)}")
        print("\\nMake sure the SSE server is running first!")
        sys.exit(1)


if __name__ == "__main__":
    main()
