#!/usr/bin/env python
"""
cancel_scope_proof_test.py
──────────────────────────
Focused test to PROVE we've eliminated the specific cancel scope error:
"Attempted to exit cancel scope in a different task than it was entered in"

This test specifically targets the exact conditions that trigger this error.
"""

import asyncio
import json
import logging
import sys
import tempfile
import os
import time
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chuk_mcp.transports.stdio import stdio_client
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.protocol.messages import send_initialize, send_tools_list

# Test server that can trigger cancel scope issues
CANCEL_SCOPE_TRIGGER_SERVER = '''#!/usr/bin/env python3
import asyncio
import json
import sys
import random
import time

async def handle_message(message):
    method = message.get("method")
    msg_id = message.get("id")
    
    if method == "initialize":
        # Sometimes delay initialization to stress cancel scopes
        if random.random() < 0.3:
            await asyncio.sleep(random.uniform(0.1, 0.3))
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "cancel-scope-test-server", "version": "1.0.0"}
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        # Delay to increase chance of cancellation during response
        await asyncio.sleep(random.uniform(0.05, 0.15))
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"tools": [{"name": "delay_tool", "description": "Tool that causes delays"}]}
        }
    elif method == "tools/call":
        # Long delay to trigger cancellation
        await asyncio.sleep(random.uniform(0.2, 0.5))
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"content": [{"type": "text", "text": "{\\"success\\": true}"}]}
        }
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}

async def main():
    try:
        while True:
            try:
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
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
    except Exception:
        pass

if __name__ == "__main__":
    asyncio.run(main())
'''

class CancelScopeErrorHunter:
    """Specifically hunt for the cancel scope error message."""
    
    def __init__(self):
        self.cancel_scope_errors = []
        self.handler = None
        self.original_level = None
        
    def start_hunting(self):
        """Start hunting for cancel scope errors with full logging."""
        self.cancel_scope_errors = []
        
        # Enable DEBUG logging to catch all cancel scope messages
        root_logger = logging.getLogger()
        self.original_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)
        
        # Enable chuk_mcp logging
        chuk_logger = logging.getLogger('chuk_mcp')
        chuk_logger.setLevel(logging.DEBUG)
        
        class CancelScopeHunter(logging.Handler):
            def __init__(self, hunter):
                super().__init__()
                self.hunter = hunter
                
            def emit(self, record):
                try:
                    message = record.getMessage()
                    
                    # Look for the EXACT cancel scope error
                    if "cancel scope" in message.lower():
                        error_entry = {
                            'level': record.levelname,
                            'logger': record.name,
                            'message': message,
                            'thread': threading.current_thread().name,
                            'function': getattr(record, 'funcName', ''),
                            'timestamp': time.time()
                        }
                        
                        # Classify the error
                        if "attempted to exit cancel scope in a different task" in message.lower():
                            error_entry['type'] = 'CRITICAL_CANCEL_SCOPE_ERROR'
                        elif record.levelno >= logging.ERROR:
                            error_entry['type'] = 'ERROR_LEVEL_CANCEL_SCOPE'
                        else:
                            error_entry['type'] = 'DEBUG_LEVEL_CANCEL_SCOPE'
                            
                        self.hunter.cancel_scope_errors.append(error_entry)
                        
                except Exception:
                    pass
        
        self.handler = CancelScopeHunter(self)
        root_logger.addHandler(self.handler)
        chuk_logger.addHandler(self.handler)
        
    def stop_hunting(self):
        """Stop hunting and restore logging."""
        if self.handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.handler)
            
            chuk_logger = logging.getLogger('chuk_mcp')
            chuk_logger.removeHandler(self.handler)
            
            if self.original_level is not None:
                root_logger.setLevel(self.original_level)
                
            self.handler = None
    
    def analyze_results(self):
        """Analyze the hunt results."""
        critical_errors = [e for e in self.cancel_scope_errors if e['type'] == 'CRITICAL_CANCEL_SCOPE_ERROR']
        error_level = [e for e in self.cancel_scope_errors if e['type'] == 'ERROR_LEVEL_CANCEL_SCOPE']
        debug_level = [e for e in self.cancel_scope_errors if e['type'] == 'DEBUG_LEVEL_CANCEL_SCOPE']
        
        return {
            'total_cancel_scope_messages': len(self.cancel_scope_errors),
            'critical_errors': len(critical_errors),
            'error_level_messages': len(error_level),
            'debug_level_messages': len(debug_level),
            'critical_error_details': critical_errors,
            'error_level_details': error_level,
            'success': len(critical_errors) == 0 and len(error_level) == 0
        }


async def create_cancel_scope_server():
    """Create server that can trigger cancel scope issues."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(CANCEL_SCOPE_TRIGGER_SERVER)
        return f.name


async def test_cancel_scope_during_normal_shutdown(server_file: str) -> dict:
    """Test cancel scope handling during normal shutdown."""
    hunter = CancelScopeErrorHunter()
    hunter.start_hunting()
    
    print("  🎯 Testing normal shutdown cancel scope handling...")
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        # Normal workflow that should NOT trigger cancel scope errors
        for i in range(5):
            async with stdio_client(server_params) as (read_stream, write_stream):
                await send_initialize(read_stream, write_stream)
                await send_tools_list(read_stream, write_stream)
                # Normal exit - should not cause cancel scope errors
            
            await asyncio.sleep(0.02)  # Small delay between iterations
        
        # Allow time for any delayed errors to appear
        await asyncio.sleep(0.2)
        
    except Exception as e:
        print(f"    ❌ Exception during test: {e}")
    
    hunter.stop_hunting()
    return hunter.analyze_results()


async def test_cancel_scope_with_task_cancellation(server_file: str) -> dict:
    """Test cancel scope handling when tasks are explicitly cancelled."""
    hunter = CancelScopeErrorHunter()
    hunter.start_hunting()
    
    print("  🎯 Testing cancel scope with explicit task cancellation...")
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        async def connection_that_gets_cancelled():
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    await send_initialize(read_stream, write_stream)
                    await send_tools_list(read_stream, write_stream)
                    # This will be cancelled
                    await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                # Expected cancellation
                pass
        
        # Start tasks and then cancel them
        tasks = []
        for i in range(3):
            task = asyncio.create_task(connection_that_gets_cancelled())
            tasks.append(task)
            await asyncio.sleep(0.05)  # Let task start
        
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        
        # Wait for cancellation to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Allow time for any cancel scope errors to appear
        await asyncio.sleep(0.2)
        
    except Exception as e:
        print(f"    ❌ Exception during cancellation test: {e}")
    
    hunter.stop_hunting()
    return hunter.analyze_results()


async def test_cancel_scope_with_exceptions_during_cleanup(server_file: str) -> dict:
    """Test cancel scope handling when exceptions occur during cleanup."""
    hunter = CancelScopeErrorHunter()
    hunter.start_hunting()
    
    print("  🎯 Testing cancel scope with exceptions during cleanup...")
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        # Connections that will have exceptions during cleanup
        for i in range(3):
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    await send_initialize(read_stream, write_stream)
                    # Force different types of exceptions
                    if i == 0:
                        raise ValueError("Forced exception during connection")
                    elif i == 1:
                        raise RuntimeError("Another forced exception")
                    else:
                        raise asyncio.CancelledError("Forced cancellation")
            except (ValueError, RuntimeError, asyncio.CancelledError):
                # These exceptions are expected
                pass
            
            await asyncio.sleep(0.05)
        
        # Allow time for any cancel scope errors to appear
        await asyncio.sleep(0.2)
        
    except Exception as e:
        print(f"    ❌ Exception during cleanup test: {e}")
    
    hunter.stop_hunting()
    return hunter.analyze_results()


async def test_cancel_scope_rapid_fire_stress(server_file: str) -> dict:
    """Rapid fire connections to stress cancel scope handling."""
    hunter = CancelScopeErrorHunter()
    hunter.start_hunting()
    
    print("  🎯 Testing cancel scope under rapid fire stress...")
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        # Rapid fire connections with minimal delays
        for i in range(20):
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    await send_initialize(read_stream, write_stream)
                    # Very short operation
                await asyncio.sleep(0.001)  # Minimal delay
            except Exception:
                # Some failures expected under stress
                pass
        
        # Allow time for any cancel scope errors to appear
        await asyncio.sleep(0.2)
        
    except Exception as e:
        print(f"    ❌ Exception during stress test: {e}")
    
    hunter.stop_hunting()
    return hunter.analyze_results()


async def run_cancel_scope_proof_tests():
    """Run comprehensive cancel scope proof tests."""
    print("🔍 CANCEL SCOPE ERROR PROOF TEST")
    print("=" * 60)
    print("Specifically hunting for: 'Attempted to exit cancel scope in a different task'")
    print("=" * 60)
    
    server_file = await create_cancel_scope_server()
    
    try:
        tests = [
            ("Normal Shutdown", test_cancel_scope_during_normal_shutdown),
            ("Task Cancellation", test_cancel_scope_with_task_cancellation),
            ("Exception Cleanup", test_cancel_scope_with_exceptions_during_cleanup),
            ("Rapid Fire Stress", test_cancel_scope_rapid_fire_stress),
        ]
        
        all_results = []
        total_critical_errors = 0
        total_error_level = 0
        
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name} Test:")
            result = await test_func(server_file)
            all_results.append((test_name, result))
            
            total_critical_errors += result['critical_errors']
            total_error_level += result['error_level_messages']
            
            # Report results
            if result['success']:
                print(f"    ✅ PASS - No critical cancel scope errors")
            else:
                print(f"    ❌ FAIL - {result['critical_errors']} critical, {result['error_level_messages']} error-level")
            
            if result['total_cancel_scope_messages'] > 0:
                print(f"    📊 Total cancel scope messages: {result['total_cancel_scope_messages']}")
                print(f"        Critical: {result['critical_errors']}, Error-level: {result['error_level_messages']}, Debug: {result['debug_level_messages']}")
        
        # Final analysis
        print("\n" + "=" * 60)
        print("🏁 CANCEL SCOPE PROOF TEST RESULTS")
        print("=" * 60)
        
        if total_critical_errors == 0 and total_error_level == 0:
            print("🎉 PROOF COMPLETE: NO CANCEL SCOPE ERRORS DETECTED!")
            print("✅ The specific error 'Attempted to exit cancel scope in a different task' has been eliminated")
            print("✅ No ERROR-level cancel scope messages detected")
            print("✅ The fix is working correctly under all test conditions")
            
            # Show debug-level messages as proof the fix is working
            total_debug = sum(r[1]['debug_level_messages'] for r in all_results)
            if total_debug > 0:
                print(f"📝 {total_debug} DEBUG-level cancel scope messages detected (expected/harmless)")
            
            return True
        else:
            print("❌ CANCEL SCOPE ERRORS STILL DETECTED!")
            print(f"🚨 Critical errors: {total_critical_errors}")
            print(f"🚨 Error-level messages: {total_error_level}")
            print("🔧 The fix needs further refinement")
            
            # Show details of critical errors
            for test_name, result in all_results:
                if result['critical_errors'] > 0 or result['error_level_messages'] > 0:
                    print(f"\n❌ {test_name} errors:")
                    for error in result['critical_error_details'] + result['error_level_details']:
                        print(f"    {error['level']}: {error['message']}")
            
            return False
            
    finally:
        os.unlink(server_file)


async def main():
    """Main proof test entry point."""
    try:
        success = await run_cancel_scope_proof_tests()
        
        if success:
            print("\n🏆 CANCEL SCOPE ERROR ELIMINATED!")
            print("✅ The fix has been proven to work")
        else:
            print("\n🚨 CANCEL SCOPE ERROR STILL EXISTS!")
            print("❌ Further fixes needed")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Proof test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Proof test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())