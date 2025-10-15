#!/usr/bin/env python3
"""
Streamable HTTP MCP Server Example

This server demonstrates the modern Streamable HTTP transport for MCP (spec 2025-03-26).
It replaces the deprecated SSE transport with a cleaner, more flexible approach.

Usage:
    pip install fastapi uvicorn
    python streamable_http_server.py
"""

import asyncio
import json
import uuid
import datetime
import sys
from typing import Dict, Any, Optional
import logging

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("❌ FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Streamable HTTP MCP Server", version="1.0.0")

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
        self.server_info = {"name": "streamable-http-server", "version": "1.0.0"}
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True},
            "prompts": {"listChanged": True},
        }


state = ServerState()


@app.get("/")
async def root():
    return {
        "message": "Streamable HTTP MCP Server",
        "version": "1.0.0",
        "transport": "streamable_http",
        "spec_version": "2025-03-26",
        "endpoints": {"mcp": "/mcp"},
    }


@app.post("/mcp")
async def handle_mcp_request(request: Request, response: Response):
    """
    Main MCP endpoint for Streamable HTTP transport.

    Supports both immediate JSON responses and streaming SSE responses
    based on the client's Accept header and the complexity of the operation.
    """

    # Get or create session
    session_id = request.headers.get("mcp-session-id")
    if not session_id or session_id not in state.sessions:
        session_id = str(uuid.uuid4())
        state.sessions[session_id] = {
            "id": session_id,
            "created": datetime.datetime.now().isoformat(),
            "counter": 0,
            "messages": [],
            "initialized": False,
        }
        logger.info(f"Created new session: {session_id}")

    # Set session ID in response
    response.headers["Mcp-Session-Id"] = session_id

    session = state.sessions[session_id]

    try:
        message = await request.json()
        method = message.get("method")
        msg_id = message.get("id")

        logger.info(f"📨 Received: {method} (session: {session_id})")

        # Check if client accepts streaming
        accept_header = request.headers.get("accept", "")
        supports_streaming = "text/event-stream" in accept_header

        # Determine response strategy
        use_streaming = supports_streaming and _should_use_streaming(method, message)

        if use_streaming:
            # Return streaming SSE response
            logger.info(f"📡 Using streaming response for {method}")
            return await _create_streaming_response(message, session, response)
        else:
            # Return immediate JSON response
            logger.info(f"📄 Using immediate JSON response for {method}")
            mcp_response = await handle_mcp_message(message, session)

            if mcp_response:
                return JSONResponse(content=mcp_response)
            else:
                # Notification - no response content
                return JSONResponse(content={"status": "accepted"}, status_code=202)

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id") if "message" in locals() else None,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
        }
        return JSONResponse(content=error_response, status_code=500)


def _should_use_streaming(method: str, message: Dict[str, Any]) -> bool:
    """
    Determine if a request should use streaming response.

    This is where the server decides between immediate JSON vs SSE streaming.
    """
    # Use streaming for potentially long-running operations
    streaming_methods = [
        "tools/call",  # Tool calls might take time
        "resources/read",  # Large resources
        "prompts/get",  # Complex prompts
    ]

    # For demo purposes, we'll stream some operations
    return method in streaming_methods


async def _create_streaming_response(
    message: Dict[str, Any], session: Dict[str, Any], response: Response
):
    """Create a streaming SSE response for complex operations."""

    async def generate_sse_response():
        try:
            # Process the message
            mcp_response = await handle_mcp_message(message, session)

            if mcp_response:
                # Send the response as SSE
                yield "event: message\n"
                yield f"data: {json.dumps(mcp_response)}\n\n"

            # Optional: Send completion event
            completion_event = {
                "type": "completion",
                "timestamp": datetime.datetime.now().isoformat(),
            }
            yield "event: completion\n"
            yield f"data: {json.dumps(completion_event)}\n\n"

        except Exception as e:
            # Send error via SSE
            error_response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": f"Stream error: {str(e)}"},
            }
            yield "event: error\n"
            yield f"data: {json.dumps(error_response)}\n\n"

    return StreamingResponse(
        generate_sse_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def handle_mcp_message(
    message: Dict[str, Any], session: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Handle MCP protocol messages."""

    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})

    try:
        if method == "initialize":
            session["initialized"] = True
            session["client_info"] = params.get("clientInfo", {})

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2025-03-26"),
                    "capabilities": state.capabilities,
                    "serverInfo": state.server_info,
                    "instructions": f"Streamable HTTP MCP Server - Session: {session['id']}",
                },
            }

        elif method == "notifications/initialized":
            logger.info(f"Client initialization complete for session {session['id']}")
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "http_greet",
                            "description": "Greet someone via Streamable HTTP",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name to greet",
                                    },
                                    "style": {
                                        "type": "string",
                                        "description": "Greeting style",
                                        "enum": ["formal", "casual"],
                                        "default": "casual",
                                    },
                                },
                                "required": ["name"],
                            },
                        },
                        {
                            "name": "session_info",
                            "description": "Get current session information",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "http_counter",
                            "description": "Increment session counter",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "increment": {"type": "integer", "default": 1}
                                },
                            },
                        },
                        {
                            "name": "slow_operation",
                            "description": "A deliberately slow operation to demonstrate streaming",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "duration": {
                                        "type": "integer",
                                        "description": "Duration in seconds",
                                        "default": 3,
                                    }
                                },
                            },
                        },
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "http_greet":
                name = arguments.get("name", "Anonymous")
                style = arguments.get("style", "casual")

                if style == "formal":
                    greeting = f"🌐 Good day, {name}. Welcome to our Streamable HTTP MCP server."
                else:
                    greeting = f"🌐 Hey {name}! Welcome to the HTTP MCP server! 🚀"

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": greeting}]},
                }

            elif tool_name == "session_info":
                info = {
                    "session_id": session["id"],
                    "created": session["created"],
                    "counter": session["counter"],
                    "transport": "streamable_http",
                    "initialized": session["initialized"],
                    "total_sessions": len(state.sessions),
                    "spec_version": "2025-03-26",
                }

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"📊 Session Info: {json.dumps(info, indent=2)}",
                            }
                        ]
                    },
                }

            elif tool_name == "http_counter":
                increment = arguments.get("increment", 1)
                session["counter"] += increment

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"🔢 HTTP Counter: {session['counter']} (+{increment})",
                            }
                        ]
                    },
                }

            elif tool_name == "slow_operation":
                duration = arguments.get("duration", 3)

                # Simulate slow operation
                await asyncio.sleep(duration)

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"⏱️ Slow operation completed after {duration} seconds via HTTP transport",
                            }
                        ]
                    },
                }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "http://server-status",
                            "name": "HTTP Server Status",
                            "description": "Current Streamable HTTP server status",
                            "mimeType": "application/json",
                        },
                        {
                            "uri": f"http://session-{session['id']}",
                            "name": "Current Session",
                            "description": "Current HTTP session information",
                            "mimeType": "application/json",
                        },
                        {
                            "uri": "http://transport-comparison",
                            "name": "Transport Comparison",
                            "description": "Comparison between SSE and Streamable HTTP",
                            "mimeType": "text/plain",
                        },
                    ]
                },
            }

        elif method == "resources/read":
            uri = params.get("uri")

            if uri == "http://server-status":
                status_data = {
                    "server": state.server_info,
                    "transport": "streamable_http",
                    "spec_version": "2025-03-26",
                    "active_sessions": len(state.sessions),
                    "capabilities": state.capabilities,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "advantages": [
                        "Single endpoint simplicity",
                        "Better infrastructure compatibility",
                        "Stateless operation support",
                        "Optional streaming when needed",
                    ],
                }

                content = json.dumps(status_data, indent=2)

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": content,
                            }
                        ]
                    },
                }

            elif uri == f"http://session-{session['id']}":
                session_data = {
                    "session": session,
                    "transport": "streamable_http",
                    "endpoint": "/mcp",
                    "supports_streaming": True,
                    "server_info": state.server_info,
                }

                content = json.dumps(session_data, indent=2)

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": content,
                            }
                        ]
                    },
                }

            elif uri == "http://transport-comparison":
                comparison_text = """🌐 MCP Transport Comparison

SSE Transport (Deprecated 2025-03-26):
❌ Requires separate /sse and /messages endpoints
❌ Complex connection management
❌ Infrastructure compatibility issues
❌ Limited to server-to-client streaming only

Streamable HTTP Transport (Current):
✅ Single /mcp endpoint for everything
✅ Works with standard HTTP infrastructure  
✅ Supports both immediate and streaming responses
✅ Stateless operation when streaming not needed
✅ Better error handling and retry logic
✅ Easier to implement and deploy
✅ Optional SSE streaming when beneficial

Migration Benefits:
• Simplified server implementation
• Better compatibility with load balancers
• Easier testing and debugging
• More flexible response strategies
• Future-proof architecture
"""

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "text/plain",
                                "text": comparison_text,
                            }
                        ]
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unknown resource URI: {uri}",
                    },
                }

        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {
                            "name": "http_status_report",
                            "description": "Generate a Streamable HTTP status report",
                            "arguments": [
                                {
                                    "name": "detail_level",
                                    "description": "Level of detail",
                                    "required": False,
                                }
                            ],
                        },
                        {
                            "name": "migration_guide",
                            "description": "Generate SSE to HTTP migration guidance",
                            "arguments": [],
                        },
                    ]
                },
            }

        elif method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})

            if prompt_name == "http_status_report":
                detail_level = arguments.get("detail_level", "basic")

                prompt_text = f"Generate a {detail_level} status report for the Streamable HTTP MCP server, including session analysis, performance metrics, and transport advantages."

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "description": f"HTTP status report ({detail_level})",
                        "messages": [
                            {
                                "role": "user",
                                "content": {"type": "text", "text": prompt_text},
                            }
                        ],
                    },
                }

            elif prompt_name == "migration_guide":
                prompt_text = "Create a detailed guide for migrating from SSE transport to Streamable HTTP transport in MCP, including code examples, benefits, and migration strategies."

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "description": "SSE to HTTP migration guide",
                        "messages": [
                            {
                                "role": "user",
                                "content": {"type": "text", "text": prompt_text},
                            }
                        ],
                    },
                }

    except Exception as e:
        logger.error(f"Error in handle_mcp_message: {e}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


if __name__ == "__main__":
    print("🌐 Starting Streamable HTTP MCP Server...")
    print("📡 Modern MCP transport (spec 2025-03-26)")
    print("🔗 MCP endpoint: http://localhost:8000/mcp")
    print("✅ Supports both immediate JSON and streaming SSE responses")
    print("🚀 Replaces deprecated SSE transport")
    print("\n🌟 Starting server...")

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", access_log=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server error: {e}")
        sys.exit(1)
