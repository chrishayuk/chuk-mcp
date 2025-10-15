#!/usr/bin/env python3
"""
Working chuk-mcp E2E Smoke Test

Uses the new transport APIs and clean structure.
"""

import argparse
import tempfile
import os
import sys
import time

import anyio

# chuk-mcp imports - using new APIs
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


# ============================================================================
# Test MCP Servers
# ============================================================================


def create_comprehensive_server():
    """Create a comprehensive test server with tools, resources, and prompts."""
    return """#!/usr/bin/env python3
import asyncio
import json
import sys
import logging
import datetime
import random

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)

class ComprehensiveMCPServer:
    def __init__(self):
        self.server_info = {
            "name": "comprehensive-test-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True},
            "prompts": {"listChanged": True}
        }
        
        # Test data
        self.counter = 0
        self.todos = []

    async def handle_message(self, message):
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                        "capabilities": self.capabilities,
                        "serverInfo": self.server_info,
                        "instructions": "Comprehensive test server with tools, resources, and prompts"
                    }
                }
            
            elif method == "notifications/initialized":
                return None
            
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "counter",
                                "description": "Increment and return a counter",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "increment": {"type": "integer", "default": 1}
                                    }
                                }
                            },
                            {
                                "name": "add_todo",
                                "description": "Add a todo item",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "task": {"type": "string", "description": "Task description"}
                                    },
                                    "required": ["task"]
                                }
                            },
                            {
                                "name": "calculate",
                                "description": "Perform basic math operations",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "operation": {"type": "string", "enum": ["add", "multiply", "subtract", "divide"]},
                                        "a": {"type": "number"},
                                        "b": {"type": "number"}
                                    },
                                    "required": ["operation", "a", "b"]
                                }
                            },
                            {
                                "name": "random_number",
                                "description": "Generate a random number",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "min": {"type": "integer", "default": 1},
                                        "max": {"type": "integer", "default": 100}
                                    }
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "counter":
                    increment = arguments.get("increment", 1)
                    self.counter += increment
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Counter: {self.counter} (incremented by {increment})"}]
                        }
                    }
                
                elif tool_name == "add_todo":
                    task = arguments.get("task", "")
                    todo_id = len(self.todos) + 1
                    todo = {"id": todo_id, "task": task, "completed": False}
                    self.todos.append(todo)
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Added todo #{todo_id}: {task}"}]
                        }
                    }
                
                elif tool_name == "calculate":
                    operation = arguments.get("operation")
                    a = arguments.get("a", 0)
                    b = arguments.get("b", 0)
                    
                    if operation == "add":
                        result = a + b
                    elif operation == "subtract":
                        result = a - b
                    elif operation == "multiply":
                        result = a * b
                    elif operation == "divide":
                        if b == 0:
                            return {
                                "jsonrpc": "2.0", "id": msg_id,
                                "result": {
                                    "content": [{"type": "text", "text": "Error: Division by zero"}],
                                    "isError": True
                                }
                            }
                        result = a / b
                    else:
                        return {
                            "jsonrpc": "2.0", "id": msg_id,
                            "result": {
                                "content": [{"type": "text", "text": f"Unknown operation: {operation}"}],
                                "isError": True
                            }
                        }
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"{a} {operation} {b} = {result}"}]
                        }
                    }
                
                elif tool_name == "random_number":
                    min_val = arguments.get("min", 1)
                    max_val = arguments.get("max", 100)
                    number = random.randint(min_val, max_val)
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Random number between {min_val} and {max_val}: {number}"}]
                        }
                    }
            
            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "resources": [
                            {
                                "uri": "test://status",
                                "name": "Server Status",
                                "description": "Current server status and statistics"
                            },
                            {
                                "uri": "test://todos",
                                "name": "Todo List",
                                "description": "Current todo items"
                            },
                            {
                                "uri": "test://time",
                                "name": "Current Time",
                                "description": "Server current time"
                            }
                        ]
                    }
                }
            
            elif method == "resources/read":
                uri = params.get("uri")
                
                if uri == "test://status":
                    status = {
                        "server": self.server_info["name"],
                        "version": self.server_info["version"],
                        "counter": self.counter,
                        "todos_count": len(self.todos),
                        "uptime": "running"
                    }
                    content = json.dumps(status, indent=2)
                
                elif uri == "test://todos":
                    if not self.todos:
                        content = "No todos yet. Use the add_todo tool to create some!"
                    else:
                        content = "Todo List:\\n"
                        for todo in self.todos:
                            status = "✅" if todo["completed"] else "📝"
                            content += f"{status} #{todo['id']}: {todo['task']}\\n"
                
                elif uri == "test://time":
                    content = f"Current server time: {datetime.datetime.now().isoformat()}"
                
                else:
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32602, "message": f"Unknown resource: {uri}"}
                    }
                
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "contents": [{"uri": uri, "mimeType": "text/plain", "text": content}]
                    }
                }
            
            elif method == "prompts/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "prompts": [
                            {
                                "name": "summarize_todos",
                                "description": "Generate a summary of current todos",
                                "arguments": [
                                    {"name": "format", "description": "Summary format", "required": False}
                                ]
                            },
                            {
                                "name": "explain_math",
                                "description": "Explain a math operation",
                                "arguments": [
                                    {"name": "operation", "description": "Math operation to explain", "required": True}
                                ]
                            }
                        ]
                    }
                }
            
            elif method == "prompts/get":
                prompt_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if prompt_name == "summarize_todos":
                    format_type = arguments.get("format", "bullet")
                    count = len(self.todos)
                    
                    if format_type == "paragraph":
                        prompt_text = f"Please write a paragraph summary of the current {count} todo items, focusing on priorities and completion status."
                    else:
                        prompt_text = f"Please create a bullet-point summary of the current {count} todo items, organized by priority."
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "description": f"Todo summary prompt ({format_type} format)",
                            "messages": [
                                {"role": "user", "content": {"type": "text", "text": prompt_text}}
                            ]
                        }
                    }
                
                elif prompt_name == "explain_math":
                    operation = arguments.get("operation", "addition")
                    prompt_text = f"Please explain how {operation} works mathematically, including examples and real-world applications."
                    
                    return {
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "description": f"Math explanation prompt for {operation}",
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
                    break
                line_str = line.decode('utf-8').strip()
                if line_str:
                    yield line_str
            except Exception:
                break

    async def run(self):
        logger.info("Starting comprehensive MCP server...")
        try:
            async for line in self.read_stdin():
                try:
                    message = json.loads(line)
                    response = await self.handle_message(message)
                    if response:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), flush=True)
        except Exception as e:
            logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(ComprehensiveMCPServer().run())
"""


# ============================================================================
# Demo Functions
# ============================================================================


async def demo_basic_functionality():
    """Demonstrate basic MCP functionality."""
    print("🎯 Demo: Basic MCP Functionality")
    print("=" * 50)

    server_code = create_comprehensive_server()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(server_code)
        server_file = f.name

    try:
        server_params = StdioParameters(command="python", args=[server_file])

        async with stdio_client(server_params) as (read_stream, write_stream):
            print("📡 Connecting to comprehensive test server...")

            # 1. Initialization
            print("\\n1️⃣  Initializing connection...")
            init_result = await send_initialize(read_stream, write_stream)
            print(f"   ✅ Connected to: {init_result.serverInfo.name}")
            print(f"   📋 Protocol version: {init_result.protocolVersion}")
            if init_result.instructions:
                print(f"   💡 Instructions: {init_result.instructions}")

            # 2. Ping test
            print("\\n2️⃣  Testing ping...")
            ping_success = await send_ping(read_stream, write_stream)
            print(
                f"   {'✅' if ping_success else '❌'} Ping: {'Success' if ping_success else 'Failed'}"
            )

            # 3. List and call tools
            print("\\n3️⃣  Exploring tools...")
            tools_response = await send_tools_list(read_stream, write_stream)
            tools = tools_response["tools"]
            print(f"   📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description']}")

            print("\\n   🔧 Testing counter tool...")
            counter_response = await send_tools_call(
                read_stream, write_stream, "counter", {"increment": 5}
            )
            print(f"   📤 Counter result: {counter_response['content'][0]['text']}")

            print("\\n   🔧 Testing calculation tool...")
            calc_response = await send_tools_call(
                read_stream,
                write_stream,
                "calculate",
                {"operation": "multiply", "a": 7, "b": 8},
            )
            print(f"   📤 Calculation result: {calc_response['content'][0]['text']}")

            print("\\n   🔧 Adding a todo...")
            todo_response = await send_tools_call(
                read_stream,
                write_stream,
                "add_todo",
                {"task": "Test chuk-mcp implementation"},
            )
            print(f"   📤 Todo result: {todo_response['content'][0]['text']}")

            # 4. List and read resources
            print("\\n4️⃣  Exploring resources...")
            resources_response = await send_resources_list(read_stream, write_stream)
            resources = resources_response["resources"]
            print(f"   📂 Found {len(resources)} resources:")
            for resource in resources:
                print(f"      • {resource['name']}: {resource['description']}")

            print("\\n   📖 Reading server status...")
            status_response = await send_resources_read(
                read_stream, write_stream, "test://status"
            )
            print(f"   📄 Status:\\n{status_response['contents'][0]['text']}")

            print("\\n   📖 Reading todos...")
            todos_response = await send_resources_read(
                read_stream, write_stream, "test://todos"
            )
            print(f"   📄 Todos: {todos_response['contents'][0]['text']}")

            # 5. List and get prompts
            print("\\n5️⃣  Exploring prompts...")
            prompts_response = await send_prompts_list(read_stream, write_stream)
            prompts = prompts_response["prompts"]
            print(f"   📝 Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"      • {prompt['name']}: {prompt['description']}")

            print("\\n   💬 Getting math explanation prompt...")
            math_prompt_response = await send_prompts_get(
                read_stream,
                write_stream,
                "explain_math",
                {"operation": "multiplication"},
            )
            message_text = math_prompt_response["messages"][0]["content"]["text"]
            print(f"   📤 Prompt: {message_text}")

    finally:
        os.unlink(server_file)

    print("\\n🎉 Basic demo completed successfully!")


async def demo_concurrent_operations():
    """Demonstrate concurrent operations."""
    print("⚡ Demo: Concurrent Operations")
    print("=" * 50)

    server_code = create_comprehensive_server()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(server_code)
        server_file = f.name

    try:
        server_params = StdioParameters(command="python", args=[server_file])

        async with stdio_client(server_params) as (read_stream, write_stream):
            print("📡 Connecting to test server...")
            await send_initialize(read_stream, write_stream)

            # Test concurrent tool calls
            print("\\n1️⃣  Testing concurrent tool calls...")
            start_time = time.time()

            async with anyio.create_task_group() as tg:
                results = []

                async def counter_task(i):
                    response = await send_tools_call(
                        read_stream, write_stream, "counter", {"increment": 1}
                    )
                    results.append(
                        f"Counter {i+1}: {response['content'][0]['text'].split()[-1]}"
                    )

                async def random_task(i):
                    response = await send_tools_call(
                        read_stream,
                        write_stream,
                        "random_number",
                        {"min": 1, "max": 10},
                    )
                    number = response["content"][0]["text"].split()[-1]
                    results.append(f"Random {i+1}: {number}")

                # Start multiple concurrent operations
                for i in range(3):
                    tg.start_soon(counter_task, i)
                    tg.start_soon(random_task, i)

            end_time = time.time()
            print(
                f"   📊 Completed 6 concurrent operations in {end_time - start_time:.2f}s"
            )
            for result in sorted(results):
                print(f"      {result}")

            # Test mixed operations
            print("\\n2️⃣  Testing mixed concurrent operations...")
            start_time = time.time()

            async with anyio.create_task_group() as tg:
                results = []

                async def ping_op():
                    result = await send_ping(read_stream, write_stream)
                    results.append("Ping: ✅" if result else "Ping: ❌")

                async def tools_op():
                    result = await send_tools_list(read_stream, write_stream)
                    results.append(f"Tools: ✅ ({len(result['tools'])} found)")

                async def resources_op():
                    result = await send_resources_list(read_stream, write_stream)
                    results.append(f"Resources: ✅ ({len(result['resources'])} found)")

                async def calc_op():
                    _result = await send_tools_call(
                        read_stream,
                        write_stream,
                        "calculate",
                        {"operation": "add", "a": 10, "b": 5},
                    )
                    results.append("Calculate: ✅")

                tg.start_soon(ping_op)
                tg.start_soon(tools_op)
                tg.start_soon(resources_op)
                tg.start_soon(calc_op)

            end_time = time.time()
            print(f"   📊 Completed mixed operations in {end_time - start_time:.2f}s")
            for result in results:
                print(f"      {result}")

    finally:
        os.unlink(server_file)

    print("\\n🎉 Concurrent operations demo completed successfully!")


async def run_smoke_tests():
    """Run comprehensive smoke tests."""
    print("🔥 chuk-mcp Smoke Tests")
    print("=" * 50)

    tests_passed = 0
    tests_failed = 0

    async def run_test(test_func, test_name):
        nonlocal tests_passed, tests_failed
        try:
            print(f"\\n🧪 Running: {test_name}")
            await test_func()
            print(f"   ✅ {test_name} PASSED")
            tests_passed += 1
        except Exception as e:
            print(f"   ❌ {test_name} FAILED: {str(e)}")
            tests_failed += 1

    # Connection and initialization test
    async def test_connection():
        server_code = create_comprehensive_server()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_code)
            server_file = f.name

        try:
            server_params = StdioParameters(command="python", args=[server_file])
            async with stdio_client(server_params) as (read_stream, write_stream):
                init_result = await send_initialize(read_stream, write_stream)
                assert init_result is not None
                assert init_result.serverInfo.name == "comprehensive-test-server"
        finally:
            os.unlink(server_file)

    # Tools functionality test
    async def test_tools():
        server_code = create_comprehensive_server()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_code)
            server_file = f.name

        try:
            server_params = StdioParameters(command="python", args=[server_file])
            async with stdio_client(server_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)

                # Test tools list
                tools_response = await send_tools_list(read_stream, write_stream)
                assert "tools" in tools_response
                assert len(tools_response["tools"]) >= 3

                # Test tool calls
                counter_response = await send_tools_call(
                    read_stream, write_stream, "counter", {"increment": 5}
                )
                assert "content" in counter_response
                assert "5" in counter_response["content"][0]["text"]

                calc_response = await send_tools_call(
                    read_stream,
                    write_stream,
                    "calculate",
                    {"operation": "add", "a": 10, "b": 5},
                )
                assert "15" in calc_response["content"][0]["text"]
        finally:
            os.unlink(server_file)

    # Resources functionality test
    async def test_resources():
        server_code = create_comprehensive_server()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_code)
            server_file = f.name

        try:
            server_params = StdioParameters(command="python", args=[server_file])
            async with stdio_client(server_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)

                # Test resources list
                resources_response = await send_resources_list(
                    read_stream, write_stream
                )
                assert "resources" in resources_response
                assert len(resources_response["resources"]) >= 2

                # Test resource read
                status_response = await send_resources_read(
                    read_stream, write_stream, "test://status"
                )
                assert "contents" in status_response
                content = status_response["contents"][0]["text"]
                assert "comprehensive-test-server" in content
        finally:
            os.unlink(server_file)

    # Concurrent operations test
    async def test_concurrent():
        server_code = create_comprehensive_server()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_code)
            server_file = f.name

        try:
            server_params = StdioParameters(command="python", args=[server_file])
            async with stdio_client(server_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)

                # Run multiple operations concurrently
                async with anyio.create_task_group() as tg:
                    results = []

                    async def ping_op():
                        result = await send_ping(read_stream, write_stream)
                        results.append(result)

                    async def tools_op():
                        result = await send_tools_list(read_stream, write_stream)
                        results.append(len(result["tools"]) > 0)

                    async def counter_op():
                        result = await send_tools_call(
                            read_stream, write_stream, "counter", {"increment": 1}
                        )
                        results.append(
                            "counter" in result["content"][0]["text"].lower()
                        )

                    tg.start_soon(ping_op)
                    tg.start_soon(tools_op)
                    tg.start_soon(counter_op)

                assert all(results), f"Some concurrent operations failed: {results}"
        finally:
            os.unlink(server_file)

    # Run all tests
    await run_test(test_connection, "Connection & Initialization")
    await run_test(test_tools, "Tools Functionality")
    await run_test(test_resources, "Resources Functionality")
    await run_test(test_concurrent, "Concurrent Operations")

    # Summary
    print("\\n" + "=" * 50)
    print("🏁 Smoke Test Results:")
    print(f"   ✅ Passed: {tests_passed}")
    print(f"   ❌ Failed: {tests_failed}")
    print(f"   📊 Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")

    if tests_failed == 0:
        print("\\n🎉 All smoke tests passed! chuk-mcp is working correctly.")
    else:
        print("\\n⚠️  Some tests failed. Check the output above for details.")

    return tests_failed == 0


async def run_performance_tests():
    """Run basic performance benchmarks."""
    print("🚀 chuk-mcp Performance Tests")
    print("=" * 50)

    server_code = create_comprehensive_server()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(server_code)
        server_file = f.name

    try:
        server_params = StdioParameters(command="python", args=[server_file])

        # Test 1: Connection time
        print("\\n⏱️  Test 1: Connection Performance")
        connection_times = []
        for i in range(3):
            start = time.perf_counter()
            async with stdio_client(server_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)
            end = time.perf_counter()
            connection_times.append(end - start)

        avg_connection = sum(connection_times) / len(connection_times)
        print(f"   📊 Average connection time: {avg_connection:.3f}s")

        # Test 2: Throughput
        print("\\n⚡ Test 2: Request Throughput")
        async with stdio_client(server_params) as (read_stream, write_stream):
            await send_initialize(read_stream, write_stream)

            num_requests = 50
            start = time.perf_counter()

            # Concurrent requests
            async with anyio.create_task_group() as tg:
                for i in range(num_requests):
                    tg.start_soon(send_ping, read_stream, write_stream)

            concurrent_time = time.perf_counter() - start
            concurrent_throughput = num_requests / concurrent_time

            print(f"   📊 Concurrent: {concurrent_throughput:.1f} requests/sec")

        print("\\n🎯 Performance Summary:")
        print(
            f"   • Connection setup: {'Fast' if avg_connection < 1.0 else 'Slow'} ({avg_connection:.3f}s)"
        )
        print(
            f"   • Request throughput: {'Good' if concurrent_throughput > 50 else 'Needs improvement'} ({concurrent_throughput:.1f} req/s)"
        )

    finally:
        os.unlink(server_file)

    print("\\n🏁 Performance tests completed!")


# ============================================================================
# Main CLI
# ============================================================================


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="chuk-mcp Working E2E Tests (New Transport APIs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python working_smoke_test.py --demo basic
  python working_smoke_test.py --demo concurrent
  python working_smoke_test.py --demo all
  python working_smoke_test.py --smoke
  python working_smoke_test.py --performance
  python working_smoke_test.py --all
        """,
    )

    parser.add_argument(
        "--demo",
        choices=["basic", "concurrent", "all"],
        help="Run interactive demonstrations",
    )

    parser.add_argument("--smoke", action="store_true", help="Run smoke tests")

    parser.add_argument(
        "--performance", action="store_true", help="Run performance benchmarks"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run everything (demos, smoke tests, and performance)",
    )

    args = parser.parse_args()

    if not any([args.demo, args.smoke, args.performance, args.all]):
        parser.print_help()
        return

    print("🚀 chuk-mcp Working E2E Test Suite")
    print("=" * 60)
    print("🎯 Using NEW transport APIs: chuk_mcp.transports.stdio")
    print("📋 Testing protocol messages from: chuk_mcp.protocol.messages")
    print("=" * 60)

    try:
        if args.all or args.demo == "all":
            await demo_basic_functionality()
            print("\\n" + "=" * 60 + "\\n")
            await demo_concurrent_operations()
        elif args.demo == "basic":
            await demo_basic_functionality()
        elif args.demo == "concurrent":
            await demo_concurrent_operations()

        if args.all or args.smoke:
            if args.demo or args.all:
                print("\\n" + "=" * 60 + "\\n")
            success = await run_smoke_tests()
            if not success:
                sys.exit(1)

        if args.all or args.performance:
            if args.demo or args.smoke or args.all:
                print("\\n" + "=" * 60 + "\\n")
            await run_performance_tests()

        print("\\n" + "=" * 60)
        print("🎉 All requested tests completed successfully!")
        print("🔧 Your chuk-mcp implementation is working correctly.")
        print("🚀 New transport APIs are functional!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\\n\\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\n💥 Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    anyio.run(main)
