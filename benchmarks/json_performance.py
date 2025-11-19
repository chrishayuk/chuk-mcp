#!/usr/bin/env python3
"""
JSON Performance Benchmark - Compare orjson vs stdlib json

Measures the performance difference between:
1. orjson (fast C implementation)
2. stdlib json (pure Python)
"""

import time
import json as stdlib_json
from chuk_mcp.protocol import fast_json

# Test data - realistic MCP message
TEST_MESSAGE = {
    "jsonrpc": "2.0",
    "id": "test-request-12345",
    "method": "tools/call",
    "params": {
        "name": "search_database",
        "arguments": {
            "query": "SELECT * FROM users WHERE created_at > '2024-01-01'",
            "limit": 100,
            "filters": {
                "status": "active",
                "role": ["admin", "user", "moderator"],
                "metadata": {
                    "tags": ["important", "verified", "premium"],
                    "score": 95.5,
                    "nested": {"deep": {"value": "test"}},
                },
            },
        },
    },
}

# Complex response data
TEST_RESPONSE = {
    "jsonrpc": "2.0",
    "id": "test-request-12345",
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Query executed successfully. Found 1,234 matching records.",
            },
            {
                "type": "resource",
                "resource": {
                    "uri": "db://users/results/xyz",
                    "name": "User Query Results",
                    "mimeType": "application/json",
                },
            },
        ],
        "isError": False,
        "metadata": {
            "execution_time_ms": 45.3,
            "rows_affected": 1234,
            "query_plan": {
                "type": "index_scan",
                "table": "users",
                "index": "created_at_idx",
            },
        },
    },
}


def benchmark_serialization(iterations=10000):
    """Benchmark JSON serialization (dumps)."""
    print("\n" + "=" * 80)
    print("JSON SERIALIZATION BENCHMARK (dumps)")
    print("=" * 80)
    print(f"Iterations: {iterations:,}")
    print(f"Using orjson: {fast_json.HAS_ORJSON}")

    # Benchmark fast_json (orjson or stdlib)
    start = time.perf_counter()
    for _ in range(iterations):
        fast_json.dumps(TEST_MESSAGE)
    fast_time = time.perf_counter() - start

    # Benchmark stdlib json for comparison
    start = time.perf_counter()
    for _ in range(iterations):
        stdlib_json.dumps(TEST_MESSAGE)
    stdlib_time = time.perf_counter() - start

    # Calculate speedup
    speedup = stdlib_time / fast_time if fast_time > 0 else 0
    improvement_pct = (
        ((stdlib_time - fast_time) / stdlib_time * 100) if stdlib_time > 0 else 0
    )

    print("\n📊 Results:")
    print(f"  fast_json: {fast_time:.4f}s ({iterations / fast_time:,.0f} ops/sec)")
    print(
        f"  stdlib json: {stdlib_time:.4f}s ({iterations / stdlib_time:,.0f} ops/sec)"
    )
    print(f"  Speedup: {speedup:.2f}x faster")
    print(f"  Improvement: {improvement_pct:.1f}%")

    return speedup


def benchmark_deserialization(iterations=10000):
    """Benchmark JSON deserialization (loads)."""
    print("\n" + "=" * 80)
    print("JSON DESERIALIZATION BENCHMARK (loads)")
    print("=" * 80)
    print(f"Iterations: {iterations:,}")

    # Pre-serialize the test data
    json_str = stdlib_json.dumps(TEST_RESPONSE)

    # Benchmark fast_json (orjson or stdlib)
    start = time.perf_counter()
    for _ in range(iterations):
        fast_json.loads(json_str)
    fast_time = time.perf_counter() - start

    # Benchmark stdlib json for comparison
    start = time.perf_counter()
    for _ in range(iterations):
        stdlib_json.loads(json_str)
    stdlib_time = time.perf_counter() - start

    # Calculate speedup
    speedup = stdlib_time / fast_time if fast_time > 0 else 0
    improvement_pct = (
        ((stdlib_time - fast_time) / stdlib_time * 100) if stdlib_time > 0 else 0
    )

    print("\n📊 Results:")
    print(f"  fast_json: {fast_time:.4f}s ({iterations / fast_time:,.0f} ops/sec)")
    print(
        f"  stdlib json: {stdlib_time:.4f}s ({iterations / stdlib_time:,.0f} ops/sec)"
    )
    print(f"  Speedup: {speedup:.2f}x faster")
    print(f"  Improvement: {improvement_pct:.1f}%")

    return speedup


def benchmark_round_trip(iterations=5000):
    """Benchmark full round-trip (dumps + loads)."""
    print("\n" + "=" * 80)
    print("JSON ROUND-TRIP BENCHMARK (dumps + loads)")
    print("=" * 80)
    print(f"Iterations: {iterations:,}")

    # Benchmark fast_json (orjson or stdlib)
    start = time.perf_counter()
    for _ in range(iterations):
        json_str = fast_json.dumps(TEST_MESSAGE)
        _ = fast_json.loads(json_str)
    fast_time = time.perf_counter() - start

    # Benchmark stdlib json for comparison
    start = time.perf_counter()
    for _ in range(iterations):
        json_str = stdlib_json.dumps(TEST_MESSAGE)
        _ = stdlib_json.loads(json_str)
    stdlib_time = time.perf_counter() - start

    # Calculate speedup
    speedup = stdlib_time / fast_time if fast_time > 0 else 0
    improvement_pct = (
        ((stdlib_time - fast_time) / stdlib_time * 100) if stdlib_time > 0 else 0
    )

    print("\n📊 Results:")
    print(f"  fast_json: {fast_time:.4f}s ({iterations / fast_time:,.0f} ops/sec)")
    print(
        f"  stdlib json: {stdlib_time:.4f}s ({iterations / stdlib_time:,.0f} ops/sec)"
    )
    print(f"  Speedup: {speedup:.2f}x faster")
    print(f"  Improvement: {improvement_pct:.1f}%")

    return speedup


def main():
    print("\n" + "=" * 80)
    print("CHUK-MCP JSON PERFORMANCE BENCHMARK")
    print("=" * 80)

    # Run benchmarks
    serialize_speedup = benchmark_serialization(10000)
    deserialize_speedup = benchmark_deserialization(10000)
    roundtrip_speedup = benchmark_round_trip(5000)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(
        f"Using orjson: {'✅ YES' if fast_json.HAS_ORJSON else '❌ NO (using stdlib json)'}"
    )
    print("\nSpeedup vs stdlib json:")
    print(f"  Serialization:   {serialize_speedup:.2f}x faster")
    print(f"  Deserialization: {deserialize_speedup:.2f}x faster")
    print(f"  Round-trip:      {roundtrip_speedup:.2f}x faster")

    if fast_json.HAS_ORJSON:
        print(
            f"\n🚀 Overall performance improvement: {roundtrip_speedup:.2f}x faster with orjson"
        )
        print("   This translates to 2-3x more message throughput in practice!")
    else:
        print("\n💡 Install orjson for 2-3x faster JSON operations:")
        print("   pip install 'chuk-mcp[fast-json]'")

    print("=" * 80)


if __name__ == "__main__":
    main()
