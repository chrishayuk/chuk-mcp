# chuk_mcp/server/server.py
"""
High-level MCP server implementation.
"""

from typing import Dict, Any, Callable, Optional
import logging

# PERFORMANCE: Use fast JSON implementation (orjson if available, stdlib json fallback)
from ..protocol import fast_json as json

from ..protocol.types.info import ServerInfo
from ..protocol.types.capabilities import ServerCapabilities
from .protocol_handler import ProtocolHandler


class MCPServer:
    """High-level MCP server implementation."""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        capabilities: Optional[ServerCapabilities] = None,
    ):
        self.server_info = ServerInfo(name=name, version=version)
        self.capabilities = capabilities or ServerCapabilities()

        self.protocol_handler = ProtocolHandler(self.server_info, self.capabilities)

        # Component registries
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}

        # Register default handlers
        self._register_default_handlers()

        logging.info(f"Initialized MCP server: {name} v{version}")

    def _register_default_handlers(self):
        """Register default protocol handlers."""
        self.protocol_handler.register_method("tools/list", self._handle_tools_list)
        self.protocol_handler.register_method("tools/call", self._handle_tools_call)
        self.protocol_handler.register_method(
            "resources/list", self._handle_resources_list
        )
        self.protocol_handler.register_method(
            "resources/read", self._handle_resources_read
        )

    def register_tool(
        self,
        name: str,
        handler: Callable,
        schema: Dict[str, Any],
        description: str = "",
    ):
        """Register a tool handler."""
        self._tools[name] = {
            "handler": handler,
            "schema": schema,
            "description": description,
        }
        logging.debug(f"Registered tool: {name}")

    def register_resource(
        self,
        uri: str,
        handler: Callable,
        name: str = "",
        description: str = "",
        mime_type: str = "text/plain",
    ):
        """Register a resource handler."""
        self._resources[uri] = {
            "handler": handler,
            "name": name or uri.split("/")[-1],
            "description": description,
            "mime_type": mime_type,
        }
        logging.debug(f"Registered resource: {uri}")

    async def _handle_tools_list(self, message, session_id):
        """Handle tools/list request."""
        tools_list = []
        for tool_name, tool_info in self._tools.items():
            tools_list.append(
                {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "inputSchema": tool_info["schema"],
                }
            )

        result = {"tools": tools_list}
        return self.protocol_handler.create_response(message.id, result), None

    async def _handle_tools_call(self, message, session_id):
        """Handle tools/call request."""
        params = message.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            return self.protocol_handler.create_error_response(
                message.id, -32602, f"Unknown tool: {tool_name}"
            ), None

        try:
            tool_info = self._tools[tool_name]
            result = await tool_info["handler"](**arguments)

            # Format result for MCP
            content = self._format_content(result)
            response_result = {"content": content}

            return self.protocol_handler.create_response(
                message.id, response_result
            ), None

        except Exception as e:
            logging.error(f"Tool execution error for {tool_name}: {e}")
            return self.protocol_handler.create_error_response(
                message.id, -32603, f"Tool execution error: {str(e)}"
            ), None

    async def _handle_resources_list(self, message, session_id):
        """Handle resources/list request."""
        resources_list = []
        for uri, resource_info in self._resources.items():
            resources_list.append(
                {
                    "uri": uri,
                    "name": resource_info["name"],
                    "description": resource_info["description"],
                    "mimeType": resource_info["mime_type"],
                }
            )

        result = {"resources": resources_list}
        return self.protocol_handler.create_response(message.id, result), None

    async def _handle_resources_read(self, message, session_id):
        """Handle resources/read request."""
        params = message.params or {}
        uri = params.get("uri")

        if uri not in self._resources:
            return self.protocol_handler.create_error_response(
                message.id, -32602, f"Unknown resource: {uri}"
            ), None

        try:
            resource_info = self._resources[uri]
            content = await resource_info["handler"]()

            # Format as resource content
            result = {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": resource_info["mime_type"],
                        "text": str(content),
                    }
                ]
            }

            return self.protocol_handler.create_response(message.id, result), None

        except Exception as e:
            logging.error(f"Resource read error for {uri}: {e}")
            return self.protocol_handler.create_error_response(
                message.id, -32603, f"Resource read error: {str(e)}"
            ), None

    def _format_content(self, result):
        """Format result as MCP content."""
        if isinstance(result, str):
            return [{"type": "text", "text": result}]
        elif isinstance(result, dict):
            return [{"type": "text", "text": json.dumps(result, indent=2)}]
        elif isinstance(result, list):
            formatted = []
            for item in result:
                formatted.extend(self._format_content(item))
            return formatted
        else:
            return [{"type": "text", "text": str(result)}]
