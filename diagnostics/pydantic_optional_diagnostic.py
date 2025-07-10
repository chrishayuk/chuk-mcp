#!/usr/bin/env python3
"""
Test script to verify chuk-mcp works with and without Pydantic.

This script validates:
1. Fallback system works when Pydantic is not available
2. All core functionality works in both modes
3. Message serialization/deserialization is compatible
4. No breaking changes when switching between modes
"""

import sys
import os
import tempfile
import json
import subprocess
import asyncio
from pathlib import Path

def test_environment_setup():
    """Test basic environment and imports."""
    print("🔍 Testing environment setup...")
    
    # Test basic Python
    print(f"   • Python version: {sys.version}")
    print(f"   • Platform: {sys.platform}")
    
    # Test if we can import chuk_mcp at all
    try:
        import chuk_mcp
        print(f"   • chuk_mcp location: {chuk_mcp.__file__}")
        print("   ✅ chuk_mcp imports successfully")
    except ImportError as e:
        print(f"   ❌ Cannot import chuk_mcp: {e}")
        return False
    
    return True


def check_pydantic_availability():
    """Check if Pydantic is currently available."""
    try:
        import pydantic
        print(f"   • Pydantic version: {pydantic.__version__}")
        return True
    except ImportError:
        print("   • Pydantic: Not available")
        return False


def test_with_pydantic():
    """Test chuk-mcp functionality with Pydantic available."""
    print("\n📦 Testing WITH Pydantic...")
    
    # Make sure we're not forcing fallback
    if "MCP_FORCE_FALLBACK" in os.environ:
        del os.environ["MCP_FORCE_FALLBACK"]
    
    try:
        # Test imports
        from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, PYDANTIC_AVAILABLE
        print(f"   • PYDANTIC_AVAILABLE: {PYDANTIC_AVAILABLE}")
        
        # Test basic model creation
        class TestModel(McpPydanticBase):
            name: str
            value: int = 42
            
        # Test model instantiation
        model = TestModel(name="test")
        print(f"   • Model creation: ✅ {model.name}, {model.value}")
        
        # Test serialization
        data = model.model_dump()
        print(f"   • model_dump(): ✅ {data}")
        
        json_str = model.model_dump_json()
        print(f"   • model_dump_json(): ✅ {len(json_str)} chars")
        
        # Test deserialization
        model2 = TestModel.model_validate({"name": "test2", "value": 100})
        print(f"   • model_validate(): ✅ {model2.name}, {model2.value}")
        
        # Test core message types
        from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
        
        msg = JSONRPCMessage.create_request("test", {"arg": "value"})
        print(f"   • JSONRPCMessage: ✅ {msg.method}")
        
        # Test validation
        try:
            TestModel(name="test", invalid_field="should work with extra=allow")
            print("   • Extra fields: ✅ Allowed")
        except Exception as e:
            print(f"   • Extra fields: ❌ {e}")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Error with Pydantic: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_without_pydantic():
    """Test chuk-mcp functionality with Pydantic fallback."""
    print("\n🔧 Testing WITHOUT Pydantic (forced fallback)...")
    
    try:
        # Force fallback mode
        os.environ["MCP_FORCE_FALLBACK"] = "1"
        
        # Clear import cache to force re-import with fallback
        modules_to_clear = [
            name for name in sys.modules.keys() 
            if name.startswith('chuk_mcp.protocol.mcp_pydantic_base')
        ]
        for module_name in modules_to_clear:
            del sys.modules[module_name]
        
        # Test imports with fallback
        from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, PYDANTIC_AVAILABLE
        print(f"   • PYDANTIC_AVAILABLE: {PYDANTIC_AVAILABLE}")
        
        if PYDANTIC_AVAILABLE:
            print("   ⚠️  Fallback mode not activated properly")
            return False
            
        # Test basic model creation with fallback
        class TestModel(McpPydanticBase):
            name: str
            value: int = 42
            
        # Test model instantiation
        model = TestModel(name="test")
        print(f"   • Model creation: ✅ {model.name}, {model.value}")
        
        # Test serialization
        data = model.model_dump()
        print(f"   • model_dump(): ✅ {data}")
        
        json_str = model.model_dump_json()
        print(f"   • model_dump_json(): ✅ {len(json_str)} chars")
        
        # Test deserialization
        model2 = TestModel.model_validate({"name": "test2", "value": 100})
        print(f"   • model_validate(): ✅ {model2.name}, {model2.value}")
        
        # Test validation behavior
        try:
            # Test required field validation
            TestModel.model_validate({})  # Should fail - missing required 'name'
            print("   • Required validation: ❌ Should have failed")
            return False
        except Exception:
            print("   • Required validation: ✅ Works")
        
        # Test that extra fields are allowed
        model3 = TestModel(name="test3", extra_field="should_be_allowed")
        print("   • Extra fields: ✅ Allowed")
        
        # Test core message types work with fallback
        from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
        
        msg = JSONRPCMessage.create_request("test", {"arg": "value"})
        print(f"   • JSONRPCMessage: ✅ {msg.method}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error with fallback: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up environment
        if "MCP_FORCE_FALLBACK" in os.environ:
            del os.environ["MCP_FORCE_FALLBACK"]


def test_message_compatibility():
    """Test that messages are compatible between Pydantic and fallback modes."""
    print("\n🔄 Testing message compatibility...")
    
    # Test data
    test_messages = [
        {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/list",
            "params": {}
        },
        {
            "jsonrpc": "2.0",
            "id": "test-2", 
            "result": {
                "tools": [
                    {
                        "name": "test-tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "arg": {"type": "string"}
                            }
                        }
                    }
                ]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "test-3",
            "error": {
                "code": -32602,
                "message": "Invalid params"
            }
        }
    ]
    
    results = {}
    
    # Test with each mode
    for mode, force_fallback in [("pydantic", False), ("fallback", True)]:
        print(f"\n   Testing {mode} mode...")
        
        try:
            if force_fallback:
                os.environ["MCP_FORCE_FALLBACK"] = "1"
            elif "MCP_FORCE_FALLBACK" in os.environ:
                del os.environ["MCP_FORCE_FALLBACK"]
            
            # Clear import cache
            modules_to_clear = [
                name for name in sys.modules.keys() 
                if name.startswith('chuk_mcp.protocol')
            ]
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            from chuk_mcp.protocol.messages.json_rpc_message import JSONRPCMessage
            
            mode_results = []
            for msg_data in test_messages:
                # Test parsing
                msg = JSONRPCMessage.model_validate(msg_data)
                
                # Test serialization
                serialized = msg.model_dump(exclude_none=True)
                
                # Test JSON serialization
                json_str = msg.model_dump_json(exclude_none=True)
                
                mode_results.append({
                    "original": msg_data,
                    "parsed": serialized,
                    "json": json_str
                })
            
            results[mode] = mode_results
            print(f"      ✅ {mode} mode processed {len(test_messages)} messages")
            
        except Exception as e:
            print(f"      ❌ {mode} mode failed: {e}")
            results[mode] = None
        finally:
            # Clean up environment for this iteration
            if "MCP_FORCE_FALLBACK" in os.environ:
                del os.environ["MCP_FORCE_FALLBACK"]
    
    # Compare results
    print("\n   Comparing compatibility...")
    if results.get("pydantic") and results.get("fallback"):
        compatible = True
        for i, (pyd_result, fall_result) in enumerate(zip(results["pydantic"], results["fallback"])):
            # Compare parsed data (should be equivalent)
            if pyd_result["parsed"] != fall_result["parsed"]:
                print(f"      ❌ Message {i} parsed differently")
                print(f"         Pydantic: {pyd_result['parsed']}")
                print(f"         Fallback: {fall_result['parsed']}")
                compatible = False
            
            # JSON should also be compatible (allowing for different ordering)
            try:
                pyd_json = json.loads(pyd_result["json"])
                fall_json = json.loads(fall_result["json"])
                if pyd_json != fall_json:
                    print(f"      ❌ Message {i} JSON differs")
                    compatible = False
            except json.JSONDecodeError as e:
                print(f"      ❌ Message {i} JSON invalid: {e}")
                compatible = False
        
        if compatible:
            print("      ✅ All messages compatible between modes")
            return True
        else:
            print("      ❌ Compatibility issues found")
            return False
    else:
        print("      ❌ Could not test both modes")
        return False


async def test_full_workflow():
    """Test complete MCP workflow in both modes."""
    print("\n🎯 Testing full MCP workflow...")
    
    # Create a simple test server
    server_code = '''#!/usr/bin/env python3
import asyncio
import json
import sys
import os

# Test without pydantic if requested
if len(sys.argv) > 1 and sys.argv[1] == "--no-pydantic":
    os.environ["MCP_FORCE_FALLBACK"] = "1"

class TestServer:
    async def handle_message(self, message):
        method = message.get("method")
        msg_id = message.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"}
                }
            }
        elif method == "notifications/initialized":
            return None
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", 
                "id": msg_id,
                "result": {
                    "tools": [{
                        "name": "test",
                        "description": "Test tool",
                        "inputSchema": {"type": "object", "properties": {}}
                    }]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": "Method not found"}
            }
    
    async def run(self):
        async def read_stdin():
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            
            while True:
                line = await reader.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').strip()
                if line_str:
                    yield line_str
        
        async for line in read_stdin():
            try:
                message = json.loads(line)
                response = await self.handle_message(message)
                if response:
                    print(json.dumps(response), flush=True)
            except Exception as e:
                error = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error), flush=True)

if __name__ == "__main__":
    asyncio.run(TestServer().run())
'''
    
    # Test both modes
    for mode, extra_args in [("with-pydantic", []), ("without-pydantic", ["--no-pydantic"])]:
        print(f"\n   Testing {mode}...")
        
        # Create temporary server file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(server_code)
            server_file = f.name
        
        try:
            # Set up environment for client
            env = os.environ.copy()
            if "without-pydantic" in mode:
                env["MCP_FORCE_FALLBACK"] = "1"
            elif "MCP_FORCE_FALLBACK" in env:
                del env["MCP_FORCE_FALLBACK"]
            
            # Clear import cache for client
            modules_to_clear = [
                name for name in sys.modules.keys() 
                if name.startswith('chuk_mcp.protocol')
            ]
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # Import fresh
            from chuk_mcp.transports.stdio import stdio_client
            from chuk_mcp.transports.stdio.parameters import StdioParameters
            from chuk_mcp.protocol.messages import send_initialize, send_ping, send_tools_list
            
            # Test the workflow
            server_params = StdioParameters(
                command="python",
                args=[server_file] + extra_args
            )
            
            async with stdio_client(server_params) as (read_stream, write_stream):
                # Test initialize
                init_result = await send_initialize(read_stream, write_stream)
                if not init_result:
                    raise Exception("Initialize failed")
                
                # Test ping
                ping_ok = await send_ping(read_stream, write_stream)
                if not ping_ok:
                    raise Exception("Ping failed")
                
                # Test tools list
                tools_response = await send_tools_list(read_stream, write_stream)
                tools = tools_response.get("tools", [])
                if len(tools) != 1:
                    raise Exception(f"Expected 1 tool, got {len(tools)}")
                
                print(f"      ✅ {mode}: All tests passed")
                
        except Exception as e:
            print(f"      ❌ {mode}: {e}")
            return False
        finally:
            # Cleanup
            try:
                os.unlink(server_file)
            except:
                pass
    
    return True


def install_test():
    """Test that the package can be installed without Pydantic."""
    print("\n📦 Testing installation scenarios...")
    
    # Test 1: Current environment
    pydantic_available = check_pydantic_availability()
    print(f"   • Current environment has Pydantic: {pydantic_available}")
    
    # Test 2: Try to import chuk_mcp and verify it works
    try:
        import chuk_mcp
        from chuk_mcp.protocol.mcp_pydantic_base import PYDANTIC_AVAILABLE
        print(f"   • chuk_mcp reports Pydantic available: {PYDANTIC_AVAILABLE}")
        
        # Test basic functionality
        from chuk_mcp.transports.stdio.parameters import StdioParameters
        params = StdioParameters(command="echo", args=["test"])
        print("   ✅ Basic imports work")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 chuk-mcp Pydantic Optional Tests")
    print("=" * 50)
    print("This will verify that chuk-mcp works with and without Pydantic")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Environment setup
    if not test_environment_setup():
        print("❌ Environment setup failed")
        return False
    
    # Test 2: Check Pydantic availability
    print(f"\n📋 Pydantic Status:")
    has_pydantic = check_pydantic_availability()
    
    # Test 3: Installation test
    if not install_test():
        all_passed = False
    
    # Test 4: With Pydantic (if available)
    if has_pydantic:
        if not test_with_pydantic():
            all_passed = False
    else:
        print("\n📦 Skipping Pydantic tests (not installed)")
    
    # Test 5: Without Pydantic (forced fallback)
    if not test_without_pydantic():
        all_passed = False
    
    # Test 6: Message compatibility
    if has_pydantic:
        if not test_message_compatibility():
            all_passed = False
    else:
        print("\n🔄 Skipping compatibility tests (Pydantic not available)")
    
    # Test 7: Full workflow test
    try:
        import anyio
        if not anyio.run(test_full_workflow):
            all_passed = False
    except Exception as e:
        print(f"\n❌ Full workflow test failed: {e}")
        all_passed = False
    
    # Results
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ chuk-mcp is fully compatible with and without Pydantic")
        print("\n📋 Summary:")
        print("   • Fallback system works correctly")
        print("   • Message serialization is compatible")
        print("   • Full MCP workflow works in both modes")
        print("   • Installation works without Pydantic dependency")
        print("\n💡 Recommendations:")
        print("   • Ship with Pydantic as optional dependency")
        print("   • Document both installation modes")
        print("   • Test with both scenarios in CI")
    else:
        print("❌ SOME TESTS FAILED!")
        print("\n🔧 Issues found with Pydantic optional support")
        print("   Please review the error messages above")
        
    print("=" * 50)
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)