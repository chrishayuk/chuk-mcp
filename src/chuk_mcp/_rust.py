"""
Bridge to the Rust-backed core (``chuk_mcp_rs``).

The behavioural / IO layer of chuk-mcp — transports, the high- and low-level
client, the server, and every ``send_*`` protocol operation — is implemented in
Rust in the ``chuk-mcp-rs`` project and exposed here through its ``chuk_mcp_rs``
Python extension. The pure-data model layer (``JSONRPCMessage``,
``MessageMethod``, capabilities/info models) remains in Python.

Everything in this module is re-exported from the public ``chuk_mcp`` namespace
so existing import paths keep working, now backed by Rust.
"""

from __future__ import annotations

import chuk_mcp_rs as _rs

# --- Transport parameters -------------------------------------------------
StdioParameters = _rs.StdioParameters
# Legacy alias used across the existing examples/tests.
StdioServerParameters = _rs.StdioParameters

# --- Transport context managers ------------------------------------------
stdio_client = _rs.stdio_client

# --- Streamable HTTP transport -------------------------------------------
StreamableHTTPParameters = _rs.StreamableHTTPParameters
StreamableHTTPTransport = _rs.StreamableHTTPTransport

# --- High-level client / server ------------------------------------------
MCPClient = _rs.MCPClient
connect_to_server = _rs.connect_to_server
MCPServer = _rs.MCPServer

# --- Low-level message operations ----------------------------------------
send_message = _rs.send_message
send_initialize = _rs.send_initialize
send_initialized_notification = _rs.send_initialized_notification
send_tools_list = _rs.send_tools_list
send_tools_call = _rs.send_tools_call
send_resources_list = _rs.send_resources_list
send_resources_read = _rs.send_resources_read
send_prompts_list = _rs.send_prompts_list
send_prompts_get = _rs.send_prompts_get
send_ping = _rs.send_ping

# --- Result / data types produced by the Rust layer ----------------------
Tool = _rs.Tool
ToolResult = _rs.ToolResult
Resource = _rs.Resource
ResourceContent = _rs.ResourceContent
ReadResourceResult = _rs.ReadResourceResult
Prompt = _rs.Prompt
PromptArgument = _rs.PromptArgument
PromptMessage = _rs.PromptMessage
GetPromptResult = _rs.GetPromptResult
InitializeResult = _rs.InitializeResult
ListToolsResult = _rs.ListToolsResult
ListResourcesResult = _rs.ListResourcesResult
ListPromptsResult = _rs.ListPromptsResult
ServerInfo = _rs.ServerInfo

# --- Errors --------------------------------------------------------------
McpError = _rs.McpError
RetryableError = _rs.RetryableError
NonRetryableError = _rs.NonRetryableError
VersionMismatchError = _rs.VersionMismatchError
ValidationError = _rs.ValidationError

# --- Environment / versions ----------------------------------------------
get_default_environment = _rs.get_default_environment
supported_versions = _rs.supported_versions
CURRENT_VERSION = _rs.CURRENT_VERSION
core_version = _rs.core_version

__all__ = [
    "StdioParameters",
    "StdioServerParameters",
    "stdio_client",
    "StreamableHTTPParameters",
    "StreamableHTTPTransport",
    "MCPClient",
    "connect_to_server",
    "MCPServer",
    "send_message",
    "send_initialize",
    "send_initialized_notification",
    "send_tools_list",
    "send_tools_call",
    "send_resources_list",
    "send_resources_read",
    "send_prompts_list",
    "send_prompts_get",
    "send_ping",
    "Tool",
    "ToolResult",
    "Resource",
    "ResourceContent",
    "ReadResourceResult",
    "Prompt",
    "PromptArgument",
    "PromptMessage",
    "GetPromptResult",
    "InitializeResult",
    "ListToolsResult",
    "ListResourcesResult",
    "ListPromptsResult",
    "ServerInfo",
    "McpError",
    "RetryableError",
    "NonRetryableError",
    "VersionMismatchError",
    "ValidationError",
    "get_default_environment",
    "supported_versions",
    "CURRENT_VERSION",
    "core_version",
]
