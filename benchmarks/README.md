# CHUK-MCP Benchmarks

Performance and stress testing suite for chuk-mcp components.

## Benchmark Scripts

### `stdio_client_benchmark.py`
Core stdio_client performance testing.

**Tests:**
- Sequential client creation (50 clients)
- Parallel client creation (50 clients)
- Interleaved init pattern (10 pairs) - tests multi-agent scenario
- Rapid create/destroy cycles (100 iterations) - leak detection
- Event loop health after multiple clients

**Run:**
```bash
python benchmarks/stdio_client_benchmark.py
```

**Output:**
- Console summary with pass/fail status
- JSON results saved to `benchmarks/results/stdio_client_<timestamp>.json`

### `multi_agent_scenario.py`
Real-world multi-agent MCP initialization patterns.

**Tests:**
- Sequential pattern (create all → initialize all)
- Interleaved pattern (create → init → create → init)
- Concurrent initialization
- Mixed MCP server configurations

**Run:**
```bash
python benchmarks/scenarios/multi_agent_scenario.py
```

### `stress_test.py`
Advanced stress testing for maximum capacity and resource limits.

**Tests:**
- **Maximum Concurrent Connections:** Tests up to 1000 concurrent connections
- **Connection Churn:** 1000 rapid create/destroy cycles measuring throughput
- **Memory Leak Detection:** 200 iterations tracking memory growth
- **Resource Limits:** System FD limits, memory limits, CPU limits

**Run:**
```bash
python benchmarks/stress_test.py
```

**Latest Results:**
- ✅ **700+ concurrent connections** (test stopped at timeout, not capacity limit)
- ✅ **252+ connections/sec** throughput
- ✅ **0MB memory leak** over 200 iterations
- ✅ **~167,000 estimated max capacity** based on FD limits

**Output:**
- Console summary with detailed metrics
- JSON results saved to `benchmarks/results/stress_test_<timestamp>.json`

## Results Directory

Benchmark results are saved to `benchmarks/results/` with timestamps.

Example result format:
```json
{
  "timestamp": 1700000000.0,
  "total_tests": 5,
  "passed": 5,
  "results": [
    {
      "name": "Sequential Creation (50 clients)",
      "duration": 0.123,
      "clients_created": 50,
      "memory_peak_mb": 12.45,
      "memory_current_mb": 2.10,
      "success": true,
      "error": null
    }
  ]
}
```

## Analyzing Results

### Memory Leaks
Check `memory_current_mb` in rapid create/destroy tests:
- < 5MB: No obvious leaks ✅
- 5-20MB: Possible leak ⚠️
- > 20MB: Likely leak ❌

### Performance Regression
Compare duration across runs:
```bash
# Run benchmark twice
python benchmarks/stdio_client_benchmark.py > run1.txt
python benchmarks/stdio_client_benchmark.py > run2.txt

# Compare durations
diff run1.txt run2.txt
```

### Event Loop Health
If "Event Loop Health" test fails, indicates anyio/asyncio mixing issues.

## CI Integration

Add to CI pipeline:
```yaml
- name: Run benchmarks
  run: python benchmarks/stdio_client_benchmark.py
  timeout-minutes: 5
```

## Interpreting Failures

### Sequential Creation Fails
- Check `__init__` doesn't block
- Verify no synchronous I/O operations

### Interleaved Init Fails
- Indicates lazy initialization not working
- Check streams created in `__aenter__` not `__init__`

### Event Loop Health Fails
- anyio/asyncio mixing detected
- Check for `asyncio.wait_for()` wrapping anyio operations
- Verify no global event loop contamination

## Development

To add new benchmarks:

```python
async def benchmark_new_test(self, param: int) -> BenchmarkResult:
    self.log(f"Starting new test...")

    tracemalloc.start()
    start_time = time.time()

    try:
        # Test code here
        pass
    except Exception as e:
        error = str(e)

    duration = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result = BenchmarkResult(
        name="New Test",
        duration=duration,
        clients_created=count,
        memory_peak_mb=peak / 1024 / 1024,
        memory_current_mb=current / 1024 / 1024,
        success=error is None,
        error=error,
    )

    self.results.append(result)
    return result
```

## Historical Context

These benchmarks were created to verify the fix for the multi-agent MCP initialization issue where creating a 3rd agent would hang after initializing 2 MCP agents.

**Root cause:** anyio memory streams created synchronously in `__init__` while other anyio task groups were active.

**Fix:** Lazy stream initialization - streams created in `__aenter__` (async context) instead of `__init__`.

The benchmarks verify this fix and prevent regression.
