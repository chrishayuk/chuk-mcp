#!/usr/bin/env python3
"""
E2E Prompts Server - Powered by chuk-mcp
Demonstrates server-side prompt templates using chuk-mcp framework.
"""

import asyncio
import logging
import sys

from chuk_mcp.server import MCPServer
from chuk_mcp.protocol.types import ServerCapabilities
from server_helpers import run_stdio_server

# Configure logging to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


async def main():
    """Create and run prompts demo server."""
    capabilities = ServerCapabilities(prompts={"listChanged": True})
    server = MCPServer(
        name="prompts-demo-server", version="1.0.0", capabilities=capabilities
    )

    # Register prompts handlers
    async def handle_prompts_list(message, session_id):
        """
        Handle prompts/list request.

        Returns list of available prompt templates that can be used by clients.
        """
        prompts = [
            {
                "name": "summarize_code",
                "description": "Generate a summary of code functionality",
                "arguments": [
                    {
                        "name": "code",
                        "description": "The code to summarize",
                        "required": True,
                    },
                    {
                        "name": "language",
                        "description": "Programming language",
                        "required": False,
                    },
                ],
            },
            {
                "name": "write_tests",
                "description": "Generate unit tests for a function",
                "arguments": [
                    {
                        "name": "function_code",
                        "description": "The function to write tests for",
                        "required": True,
                    },
                    {
                        "name": "test_framework",
                        "description": "Testing framework (e.g., pytest, jest)",
                        "required": False,
                    },
                ],
            },
            {
                "name": "explain_error",
                "description": "Explain an error message and suggest fixes",
                "arguments": [
                    {
                        "name": "error_message",
                        "description": "The error message to explain",
                        "required": True,
                    }
                ],
            },
        ]
        result = {"prompts": prompts}
        return server.protocol_handler.create_response(message.id, result), None

    async def handle_prompts_get(message, session_id):
        """
        Handle prompts/get request.

        Returns specific prompt with arguments applied.
        """
        params = message.params if hasattr(message, "params") else {}
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments", {}) if isinstance(params, dict) else {}

        # Generate prompt based on name and arguments
        if name == "summarize_code":
            code = arguments.get("code", "")
            language = arguments.get("language", "unknown")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please provide a clear, concise summary of the following {language} code:\n\n{code}\n\nInclude:\n1. Main purpose\n2. Key functionality\n3. Important implementation details",
                    },
                }
            ]
        elif name == "write_tests":
            function_code = arguments.get("function_code", "")
            test_framework = arguments.get("test_framework", "pytest")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Write comprehensive unit tests for this function using {test_framework}:\n\n{function_code}\n\nInclude:\n1. Happy path tests\n2. Edge cases\n3. Error conditions",
                    },
                }
            ]
        elif name == "explain_error":
            error_message = arguments.get("error_message", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please explain this error message and suggest how to fix it:\n\n{error_message}\n\nInclude:\n1. What the error means\n2. Common causes\n3. Step-by-step fix",
                    },
                }
            ]
        else:
            messages = [
                {
                    "role": "user",
                    "content": {"type": "text", "text": f"Unknown prompt: {name}"},
                }
            ]

        result = {"description": f"Prompt for {name}", "messages": messages}
        return server.protocol_handler.create_response(message.id, result), None

    # Register protocol handlers
    server.protocol_handler.register_method("prompts/list", handle_prompts_list)
    server.protocol_handler.register_method("prompts/get", handle_prompts_get)

    # Run server using stdio transport helper
    await run_stdio_server(server)


if __name__ == "__main__":
    asyncio.run(main())
