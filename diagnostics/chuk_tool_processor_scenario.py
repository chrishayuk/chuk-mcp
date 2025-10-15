#!/usr/bin/env python
"""
quiet_chuk_tool_processor_test.py
─────────────────────────────────
Focused test for chuk-tool-processor cancel scope errors with minimal noise.
"""

import asyncio
import logging
import sys
import tempfile
import os
from pathlib import Path

# QUIET logging - only capture actual errors
logging.basicConfig(
    level=logging.WARNING,  # Only WARNING and ERROR
    format="%(levelname)s: %(message)s",
)

# Silence DEBUG noise from chuk_mcp
logging.getLogger("chuk_mcp").setLevel(logging.ERROR)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chuk_mcp.transports.stdio import stdio_client  # noqa: E402
from chuk_mcp.transports.stdio.parameters import StdioParameters  # noqa: E402
from chuk_mcp.protocol.messages import send_initialize, send_tools_list  # noqa: E402

# Minimal MCP server for testing
MINIMAL_SERVER = """#!/usr/bin/env python3
import asyncio
import json
import sys
from datetime import datetime

async def handle_message(message):
    method = message.get("method")
    msg_id = message.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"tools": [{"name": "test_tool", "description": "Test tool"}]}
        }
    elif method == "tools/call":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"content": [{"type": "text", "text": "{\\"result\\": \\"success\\"}"}]}
        }
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}

async def main():
    try:
        while True:
            line = await asyncio.wait_for(asyncio.to_thread(sys.stdin.readline), timeout=0.1)
            if not line:
                break
            line = line.strip()
            if line:
                try:
                    message = json.loads(line)
                    response = await handle_message(message)
                    if response:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    pass
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())
"""


class QuietErrorTracker:
    """Track only cancel scope and JSON errors."""

    def __init__(self):
        self.errors = []
        self.handler = None

    def start(self):
        self.errors = []

        class QuietHandler(logging.Handler):
            def __init__(self, tracker):
                super().__init__()
                self.tracker = tracker

            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    msg = record.getMessage()
                    if (
                        "cancel scope" in msg.lower()
                        or "json object must be str" in msg.lower()
                    ):
                        self.tracker.errors.append(
                            {
                                "type": "cancel_scope"
                                if "cancel scope" in msg.lower()
                                else "json_error",
                                "message": msg,
                                "logger": record.name,
                            }
                        )

        self.handler = QuietHandler(self)
        logging.getLogger().addHandler(self.handler)

    def stop(self):
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
            self.handler = None

    def has_critical_errors(self):
        return len(self.errors) > 0

    def get_error_summary(self):
        if not self.errors:
            return "No critical errors"

        cancel_scope = sum(1 for e in self.errors if e["type"] == "cancel_scope")
        json_errors = sum(1 for e in self.errors if e["type"] == "json_error")

        summary = []
        if cancel_scope:
            summary.append(f"{cancel_scope} cancel scope error(s)")
        if json_errors:
            summary.append(f"{json_errors} JSON serialization error(s)")

        return ", ".join(summary)


async def create_test_server():
    """Create minimal test server."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(MINIMAL_SERVER)
        return f.name


async def test_single_workflow(server_file: str) -> bool:
    """Test single workflow execution."""
    tracker = QuietErrorTracker()
    tracker.start()

    try:
        server_params = StdioParameters(command="python", args=[server_file])

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            if not init_result:
                raise Exception("Initialization failed")

            # Get tools
            tools_response = await send_tools_list(read_stream, write_stream)
            if not tools_response or "tools" not in tools_response:
                raise Exception("Tools list failed")

            # Execute tool
            tool_call = {
                "jsonrpc": "2.0",
                "id": "test-call",
                "method": "tools/call",
                "params": {"name": "test_tool", "arguments": {}},
            }

            # CRITICAL FIX: Send dict, not JSON string
            await write_stream.send(tool_call)

            response_data = await read_stream.receive()
            if hasattr(response_data, "result"):
                # Success
                pass
            else:
                raise Exception("Tool call failed")

        await asyncio.sleep(0.05)  # Allow cleanup

    except Exception:
        tracker.stop()
        return False

    tracker.stop()
    return not tracker.has_critical_errors()


async def test_multiple_iterations(
    server_file: str, count: int = 10
) -> tuple[int, int]:
    """Test multiple iterations."""
    success_count = 0

    for i in range(count):
        if await test_single_workflow(server_file):
            success_count += 1
        await asyncio.sleep(0.01)

    return success_count, count


async def test_concurrent_executions(
    server_file: str, count: int = 5
) -> tuple[int, int]:
    """Test concurrent executions."""
    tasks = [test_single_workflow(server_file) for _ in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r is True)
    return success_count, count


async def run_focused_tests():
    """Run focused tests with minimal output."""
    print("🔧 CHUK Tool Processor Cancel Scope Fix Test")
    print("=" * 50)

    server_file = await create_test_server()

    try:
        results = {}

        # Test 1: Single execution
        print("Testing single execution...", end=" ")
        success = await test_single_workflow(server_file)
        results["single"] = success
        print("✅ PASS" if success else "❌ FAIL")

        # Test 2: Multiple iterations
        print("Testing 10 iterations...", end=" ")
        success_count, total = await test_multiple_iterations(server_file, 10)
        success = success_count == total
        results["multiple"] = success
        print(
            f"✅ {success_count}/{total} PASS"
            if success
            else f"❌ {success_count}/{total} FAIL"
        )

        # Test 3: Concurrent executions
        print("Testing 5 concurrent...", end=" ")
        success_count, total = await test_concurrent_executions(server_file, 5)
        success = success_count == total
        results["concurrent"] = success
        print(
            f"✅ {success_count}/{total} PASS"
            if success
            else f"❌ {success_count}/{total} FAIL"
        )

        # Overall result
        all_passed = all(results.values())

        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 ALL TESTS PASSED - No cancel scope errors!")
            return True
        else:
            failed_tests = [name for name, passed in results.items() if not passed]
            print(f"❌ TESTS FAILED: {', '.join(failed_tests)}")
            return False

    finally:
        os.unlink(server_file)


async def main():
    """Main test entry point."""
    try:
        success = await run_focused_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
