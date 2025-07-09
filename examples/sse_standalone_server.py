#!/usr/bin/env python3
"""
SSE MCP Server - Complete Fixed Implementation

This server demonstrates the correct SSE transport for MCP protocol
with all methods implemented including resources/read.

Usage:
    pip install fastapi uvicorn
    python complete_fixed_sse_server.py
"""

import asyncio
import json
import uuid
import datetime
import sys
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
        # Track active SSE streams for sending responses
        self.active_streams: Dict[str, Any] = {}

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
    
    # Create a queue for this session's messages
    message_queue = asyncio.Queue()
    state.active_streams[session_id] = message_queue
    
    async def event_stream():
        try:
            print(f"🔗 Starting SSE stream for session {session_id}")
            
            # Send the message endpoint URL (must end with /mcp for MCP protocol compliance)
            endpoint_url = f"/mcp?session_id={session_id}"
            print(f"📤 Sending endpoint event: {endpoint_url}")
            
            yield f"event: endpoint\n"
            yield f"data: {endpoint_url}\n\n"
            
            # Listen for messages and keepalives
            while True:
                try:
                    # Wait for either a message or timeout for keepalive
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    print(f"📤 Sending message event: {message}")
                    # Send message back to client
                    yield f"event: message\n"
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    keepalive_data = {'timestamp': datetime.datetime.now().isoformat()}
                    print(f"📤 Sending keepalive: {keepalive_data}")
                    yield f"event: keepalive\n"
                    yield f"data: {json.dumps(keepalive_data)}\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for session {session_id}")
        finally:
            # Clean up when connection closes
            if session_id in state.active_streams:
                del state.active_streams[session_id]
            if session_id in state.sessions:
                del state.sessions[session_id]
    
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
        logger.info(f"📨 Received message: {message.get('method')} (session: {session_id})")
        
        response = await handle_mcp_message(message, session)
        if response:
            logger.info(f"📤 Sending response via SSE: {response.get('result', response.get('error'))}")
            
            # Send response back via SSE stream
            if session_id in state.active_streams:
                await state.active_streams[session_id].put(response)
            
            # Return 202 Accepted since response is sent via SSE
            return JSONResponse(status_code=202, content={"status": "accepted"})
        else:
            # Notification - no response needed
            return JSONResponse(status_code=202, content={"status": "accepted"})
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id") if 'message' in locals() else None,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }
        
        # Send error response via SSE if possible
        if session_id in state.active_streams:
            await state.active_streams[session_id].put(error_response)
        
        return JSONResponse(status_code=202, content={"status": "error_sent_via_sse"})

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
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
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
                            "name": "Current Session Info",
                            "description": "Detailed information about the current SSE session",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }
        
        elif method == "resources/read":
            uri = params.get("uri")
            
            if uri == "sse://server-status":
                # Generate current server status
                status_data = {
                    "server": state.server_info,
                    "transport": "sse",
                    "active_sessions": len(state.sessions),
                    "capabilities": state.capabilities,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "session_details": {
                        session_id: {
                            "created": session_data["created"],
                            "counter": session_data["counter"], 
                            "initialized": session_data["initialized"]
                        }
                        for session_id, session_data in state.sessions.items()
                    }
                }
                
                content = json.dumps(status_data, indent=2)
                mime_type = "application/json"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "contents": [{"uri": uri, "mimeType": mime_type, "text": content}]
                    }
                }
            
            elif uri == f"sse://session-{session['id']}":
                # Return detailed current session info
                session_data = {
                    "session": session,
                    "transport": "sse",
                    "endpoint": f"/mcp?session_id={session['id']}",
                    "stream_active": session['id'] in state.active_streams,
                    "server_info": state.server_info
                }
                
                content = json.dumps(session_data, indent=2)
                mime_type = "application/json"
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "contents": [{"uri": uri, "mimeType": mime_type, "text": content}]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"}
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
                            "name": "session_analysis",
                            "description": "Analyze current session performance",
                            "arguments": []
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
                    prompt_text = f"Please create a comprehensive status report for the SSE MCP server, including analysis of {len(state.sessions)} active sessions, performance metrics, and recommendations for optimization."
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
            
            elif prompt_name == "session_analysis":
                prompt_text = f"Please analyze the performance and behavior of the current SSE session {session['id']}, including message count, connection stability, and usage patterns."
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "description": "Session performance analysis prompt",
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
    print("🌊 Starting COMPLETE FIXED SSE MCP Server...")
    print("📡 Server will be available at: http://localhost:8000")
    print("🔗 SSE endpoint: http://localhost:8000/sse")
    print("📬 Messages endpoint: http://localhost:8000/mcp")
    print("✅ All MCP methods implemented including resources/read")
    print("\n🚀 Starting server...")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server error: {e}")
        sys.exit(1)