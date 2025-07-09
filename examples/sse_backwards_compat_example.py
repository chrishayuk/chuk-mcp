#!/usr/bin/env python3
"""
SSE Backwards Compatibility Example

This example demonstrates how the chuk-mcp SSE transport maintains backwards
compatibility with the deprecated SSE specification while providing a clear
migration path for the future.

Key Features Demonstrated:
1. Detection of SSE vs Streamable HTTP servers
2. Automatic fallback and migration guidance
3. Integration with existing protocol messages
4. Proper error handling for deprecated transport
5. Universal response handling (immediate + async)
"""

import asyncio
import os
import sys
import logging
from typing import Optional, Dict, Any

import anyio

# chuk-mcp imports
from chuk_mcp.transports.sse import sse_client, SSEParameters, try_sse_with_fallback
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_tools_call,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SSECompatibilityTester:
    """Test SSE backwards compatibility and migration scenarios."""
    
    def __init__(self, base_url: str, bearer_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token
        
    async def test_server_capabilities(self) -> Dict[str, Any]:
        """Test what transport methods a server supports."""
        import httpx
        
        results = {
            "url": self.base_url,
            "sse_supported": False,
            "streamable_http_supported": False,
            "transport_recommendation": "unknown",
            "errors": []
        }
        
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            # Test 1: Check if SSE endpoint exists
            try:
                sse_response = await client.get(f"{self.base_url}/sse")
                if sse_response.status_code == 200:
                    if "text/event-stream" in sse_response.headers.get("content-type", ""):
                        results["sse_supported"] = True
                        logger.info("✅ SSE transport detected")
                    else:
                        results["errors"].append("SSE endpoint exists but doesn't return event-stream")
                else:
                    results["errors"].append(f"SSE endpoint returned {sse_response.status_code}")
            except Exception as e:
                results["errors"].append(f"SSE test failed: {e}")
            
            # Test 2: Check if Streamable HTTP is supported
            try:
                # Try the new protocol detection method
                init_message = {
                    "jsonrpc": "2.0",
                    "id": "test-init",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "sse-compatibility-tester", "version": "1.0.0"}
                    }
                }
                
                streamable_headers = {
                    **headers,
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json"
                }
                
                streamable_response = await client.post(
                    f"{self.base_url}/mcp", 
                    json=init_message,
                    headers=streamable_headers
                )
                
                if streamable_response.status_code in [200, 202]:
                    results["streamable_http_supported"] = True
                    logger.info("✅ Streamable HTTP transport detected")
                else:
                    results["errors"].append(f"Streamable HTTP test returned {streamable_response.status_code}")
                    
            except Exception as e:
                results["errors"].append(f"Streamable HTTP test failed: {e}")
        
        # Determine recommendation
        if results["streamable_http_supported"] and results["sse_supported"]:
            results["transport_recommendation"] = "both_supported_prefer_streamable"
        elif results["streamable_http_supported"]:
            results["transport_recommendation"] = "streamable_http_only"
        elif results["sse_supported"]:
            results["transport_recommendation"] = "sse_only_deprecated"
        else:
            results["transport_recommendation"] = "none_detected"
        
        return results
    
    async def test_sse_connection(self) -> Dict[str, Any]:
        """Test actual SSE connection and protocol support."""
        results = {
            "connection_successful": False,
            "initialization_successful": False,
            "protocol_version": None,
            "server_info": None,
            "tools_available": 0,
            "response_pattern": "unknown",  # immediate_http, async_sse, or mixed
            "errors": []
        }
        
        try:
            # Create SSE parameters
            sse_params = SSEParameters(
                url=self.base_url,
                bearer_token=self.bearer_token,
                timeout=30.0,
                auto_reconnect=False  # Disable for testing
            )
            
            logger.info(f"🔄 Testing SSE connection to {self.base_url}")
            
            async with sse_client(sse_params) as (read_stream, write_stream):
                results["connection_successful"] = True
                logger.info("✅ SSE connection established")
                
                # Test initialization
                try:
                    init_result = await send_initialize(read_stream, write_stream, timeout=10.0)
                    results["initialization_successful"] = True
                    results["protocol_version"] = init_result.protocolVersion
                    results["server_info"] = {
                        "name": init_result.serverInfo.name,
                        "version": init_result.serverInfo.version
                    }
                    logger.info(f"✅ Initialization successful: {init_result.serverInfo.name}")
                    
                    # Test ping to determine response pattern
                    ping_start = asyncio.get_event_loop().time()
                    ping_success = await send_ping(read_stream, write_stream, timeout=5.0)
                    ping_duration = asyncio.get_event_loop().time() - ping_start
                    
                    if ping_success:
                        if ping_duration < 0.1:
                            results["response_pattern"] = "immediate_http"
                        elif ping_duration > 0.5:
                            results["response_pattern"] = "async_sse"
                        else:
                            results["response_pattern"] = "mixed"
                        
                        logger.info(f"✅ Ping successful ({ping_duration:.3f}s) - {results['response_pattern']}")
                    
                    # Test tools
                    try:
                        tools_response = await send_tools_list(read_stream, write_stream, timeout=10.0)
                        results["tools_available"] = len(tools_response["tools"])
                        logger.info(f"✅ Tools list: {results['tools_available']} tools available")
                    except Exception as e:
                        results["errors"].append(f"Tools list failed: {e}")
                    
                except Exception as e:
                    results["errors"].append(f"Protocol testing failed: {e}")
                    
        except Exception as e:
            results["errors"].append(f"SSE connection failed: {e}")
            logger.error(f"❌ SSE connection failed: {e}")
        
        return results
    
    async def run_migration_guidance(self) -> None:
        """Provide migration guidance based on server capabilities."""
        print("\n" + "="*60)
        print("🔄 SSE BACKWARDS COMPATIBILITY ANALYSIS")
        print("="*60)
        
        # Test server capabilities
        print("\n1️⃣ Testing server transport capabilities...")
        capabilities = await self.test_server_capabilities()
        
        print(f"   Server URL: {capabilities['url']}")
        print(f"   SSE Support: {'✅' if capabilities['sse_supported'] else '❌'}")
        print(f"   Streamable HTTP: {'✅' if capabilities['streamable_http_supported'] else '❌'}")
        
        if capabilities['errors']:
            print("   Errors encountered:")
            for error in capabilities['errors']:
                print(f"     • {error}")
        
        # Provide recommendations
        print(f"\n📋 Recommendation: {capabilities['transport_recommendation']}")
        
        if capabilities['transport_recommendation'] == "both_supported_prefer_streamable":
            print("   ✅ Server supports both transports")
            print("   💡 Recommend migrating to Streamable HTTP for future compatibility")
            print("   📌 SSE transport will continue to work for backwards compatibility")
            
        elif capabilities['transport_recommendation'] == "streamable_http_only":
            print("   ⚠️  Server only supports Streamable HTTP")
            print("   📌 This server has already migrated from SSE")
            print("   💡 Update your client to use Streamable HTTP transport")
            
        elif capabilities['transport_recommendation'] == "sse_only_deprecated":
            print("   ⚠️  Server only supports deprecated SSE transport")
            print("   📌 This server needs to be updated")
            print("   💡 Contact server maintainer about Streamable HTTP migration")
            
        else:
            print("   ❌ No supported transport detected")
            print("   💡 Check server configuration and network connectivity")
        
        # If SSE is supported, test the actual connection
        if capabilities['sse_supported']:
            print("\n2️⃣ Testing SSE connection and protocol...")
            sse_results = await self.test_sse_connection()
            
            if sse_results['connection_successful']:
                print("   ✅ SSE connection successful")
                
                if sse_results['initialization_successful']:
                    print(f"   📋 Protocol: {sse_results['protocol_version']}")
                    print(f"   🏷️  Server: {sse_results['server_info']['name']} v{sse_results['server_info']['version']}")
                    print(f"   🔧 Tools: {sse_results['tools_available']} available")
                    print(f"   ⚡ Response Pattern: {sse_results['response_pattern']}")
                    
                    # Provide pattern-specific guidance
                    if sse_results['response_pattern'] == 'immediate_http':
                        print("   💡 Server uses immediate HTTP responses (like your example)")
                    elif sse_results['response_pattern'] == 'async_sse':
                        print("   💡 Server uses async SSE responses (queue-based)")
                    else:
                        print("   💡 Server uses mixed response patterns")
                else:
                    print("   ❌ SSE connection failed during initialization")
                    
            else:
                print("   ❌ SSE connection failed")
            
            if sse_results['errors']:
                print("   Errors:")
                for error in sse_results['errors']:
                    print(f"     • {error}")
        
        # Migration timeline guidance
        print(f"\n📅 MIGRATION TIMELINE:")
        print(f"   • SSE transport deprecated: March 26, 2025 (MCP spec 2025-03-26)")
        print(f"   • SSE backwards compatibility: Maintained in chuk-mcp")
        print(f"   • Recommended action: Plan migration to Streamable HTTP")
        print(f"   • Support timeline: SSE will work but is not future-proof")


async def run_examples():
    """Run SSE backwards compatibility examples."""
    
    # Example 1: Basic SSE connection (existing server)
    print("🌊 Example 1: Basic SSE Connection")
    print("-" * 40)
    
    try:
        # These would be your actual server parameters
        sse_params = SSEParameters(
            url="http://localhost:8000",  # Your SSE server
            timeout=30.0,
            auto_reconnect=True
        )
        
        async with sse_client(sse_params) as (read_stream, write_stream):
            print("✅ Connected to SSE server")
            
            # Standard MCP protocol usage - unchanged!
            init_result = await send_initialize(read_stream, write_stream)
            print(f"📋 Server: {init_result.serverInfo.name}")
            
            # Your existing protocol code works unchanged
            tools = await send_tools_list(read_stream, write_stream)
            print(f"🔧 Tools available: {len(tools['tools'])}")
            
    except Exception as e:
        print(f"❌ Example 1 failed (expected if no server): {e}")
    
    # Example 2: Smart fallback with migration guidance
    print(f"\n🔄 Example 2: Smart Migration Detection")
    print("-" * 40)
    
    try:
        # This would attempt SSE and provide migration guidance
        async with try_sse_with_fallback(
            url="http://localhost:8000",
            timeout=10.0
        ) as (read_stream, write_stream):
            print("✅ SSE connection with fallback successful")
            
    except Exception as e:
        print(f"📋 Migration guidance: {e}")
    
    # Example 3: Server compatibility testing
    print(f"\n🔍 Example 3: Server Compatibility Analysis")
    print("-" * 40)
    
    # Test against common endpoints that might exist
    test_urls = [
        "http://localhost:8000",   # Your example server
        "http://localhost:3000",   # Common MCP dev port
        "https://api.example.com", # Remote server example
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        tester = SSECompatibilityTester(url)
        
        try:
            # Quick capability check
            capabilities = await asyncio.wait_for(
                tester.test_server_capabilities(), 
                timeout=5.0
            )
            
            status = "✅" if capabilities['sse_supported'] or capabilities['streamable_http_supported'] else "❌"
            print(f"  {status} {capabilities['transport_recommendation']}")
            
        except asyncio.TimeoutError:
            print(f"  ⏱️  Timeout (server not available)")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    """Main entry point for SSE backwards compatibility examples."""
    
    print("🌊 chuk-mcp SSE Backwards Compatibility Demo")
    print("=" * 60)
    print("This demo shows how chuk-mcp maintains SSE backwards compatibility")
    print("while providing clear migration guidance for the future.")
    print("=" * 60)
    
    try:
        anyio.run(run_examples)
        
        print("\n" + "=" * 60)
        print("📚 Key Takeaways:")
        print("  ✅ chuk-mcp SSE transport works with existing SSE servers")
        print("  ✅ Universal response handling (immediate + async SSE)")
        print("  ✅ Clear migration guidance when SSE isn't supported")
        print("  ✅ Existing protocol code unchanged")
        print("  ⚠️  SSE is deprecated - plan migration to Streamable HTTP")
        print("  📌 Backwards compatibility maintained for existing deployments")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print(f"\n👋 Demo interrupted. SSE transport ready for production use!")
    except Exception as e:
        print(f"\n💥 Demo error: {e}")
        print("Note: Errors expected when test servers are not running")


if __name__ == "__main__":
    main()