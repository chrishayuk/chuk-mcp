#!/usr/bin/env python
"""
quiet_stress_test.py
───────────────────
Focused stress test with minimal noise to verify cancel scope fix.
"""

import asyncio
import json
import logging
import sys
import tempfile
import os
import time
from pathlib import Path

# MINIMAL logging - only actual errors
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
logging.getLogger('chuk_mcp').setLevel(logging.ERROR)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chuk_mcp.transports.stdio import stdio_client
from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.protocol.messages import send_initialize, send_ping

# Minimal server with stress conditions
STRESS_SERVER = '''#!/usr/bin/env python3
import asyncio
import json
import sys
import random

async def handle_message(message):
    method = message.get("method")
    msg_id = message.get("id")
    
    # Random delay to stress timing
    if random.random() < 0.3:
        await asyncio.sleep(random.uniform(0.01, 0.05))
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "stress-server", "version": "1.0.0"}
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Not found"}}

async def main():
    try:
        while True:
            line = await asyncio.wait_for(asyncio.to_thread(sys.stdin.readline), timeout=0.05)
            if not line:
                break
            line = line.strip()
            if line:
                try:
                    message = json.loads(line)
                    response = await handle_message(message)
                    if response:
                        print(json.dumps(response), flush=True)
                except:
                    pass
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())
'''

class CriticalErrorDetector:
    """Detect only critical errors (cancel scope, JSON serialization)."""
    
    def __init__(self):
        self.critical_errors = 0
        self.handler = None
        
    def start(self):
        self.critical_errors = 0
        
        class CriticalHandler(logging.Handler):
            def __init__(self, detector):
                super().__init__()
                self.detector = detector
                
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    msg = record.getMessage().lower()
                    if "cancel scope" in msg or "json object must be str" in msg:
                        self.detector.critical_errors += 1
        
        self.handler = CriticalHandler(self)
        logging.getLogger().addHandler(self.handler)
        
    def stop(self):
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
        return self.critical_errors == 0


async def create_stress_server():
    """Create stress test server."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(STRESS_SERVER)
        return f.name


async def stress_rapid_connections(server_file: str, count: int = 20) -> bool:
    """Rapid fire connections."""
    detector = CriticalErrorDetector()
    detector.start()
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        for _ in range(count):
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    await send_initialize(read_stream, write_stream)
                    await send_ping(read_stream, write_stream)
                await asyncio.sleep(0.001)
            except:
                pass  # Expected failures under stress
        
        await asyncio.sleep(0.05)
        
    except Exception:
        pass
    
    return detector.stop()


async def stress_concurrent_cancel(server_file: str, count: int = 15) -> bool:
    """Concurrent connections with cancellation."""
    detector = CriticalErrorDetector()
    detector.start()
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        
        async def connection_with_timeout():
            try:
                async with asyncio.timeout(0.05):  # Short timeout = cancellation
                    async with stdio_client(server_params) as (read_stream, write_stream):
                        await send_initialize(read_stream, write_stream)
                        await asyncio.sleep(0.1)  # Will be cancelled
                return True
            except:
                return False  # Expected
        
        tasks = [connection_with_timeout() for _ in range(count)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        await asyncio.sleep(0.05)
        
    except Exception:
        pass
    
    return detector.stop()


async def stress_memory_pressure(server_file: str, count: int = 30) -> bool:
    """Memory pressure + connections."""
    detector = CriticalErrorDetector()
    detector.start()
    
    try:
        server_params = StdioParameters(command="python", args=[server_file])
        memory_hog = []
        
        for i in range(count):
            # Create memory pressure
            if i % 5 == 0:
                memory_hog.append([0] * 5000)
                if len(memory_hog) > 5:
                    memory_hog.pop(0)
            
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    await send_initialize(read_stream, write_stream)
                await asyncio.sleep(0.001)
            except:
                pass
        
        memory_hog.clear()
        await asyncio.sleep(0.05)
        
    except Exception:
        pass
    
    return detector.stop()


async def run_stress_tests():
    """Run stress tests with minimal output."""
    print("⚡ Cancel Scope Stress Test")
    print("=" * 30)
    
    server_file = await create_stress_server()
    
    try:
        tests = [
            ("Rapid connections (20x)", lambda: stress_rapid_connections(server_file, 20)),
            ("Concurrent + cancel (15x)", lambda: stress_concurrent_cancel(server_file, 15)),
            ("Memory pressure (30x)", lambda: stress_memory_pressure(server_file, 30)),
        ]
        
        results = []
        
        for name, test_func in tests:
            print(f"Running {name}...", end=" ")
            start_time = time.time()
            success = await test_func()
            duration = time.time() - start_time
            results.append(success)
            print(f"{'✅' if success else '❌'} ({duration:.2f}s)")
        
        print("\n" + "=" * 30)
        
        if all(results):
            print("🎉 ALL STRESS TESTS PASSED")
            print("✅ No cancel scope errors under stress")
            return True
        else:
            failed = sum(1 for r in results if not r)
            print(f"❌ {failed}/{len(results)} STRESS TESTS FAILED")
            print("🚨 Cancel scope errors detected under stress")
            return False
            
    finally:
        os.unlink(server_file)


async def main():
    """Main stress test entry point."""
    try:
        success = await run_stress_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Stress test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Stress test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())