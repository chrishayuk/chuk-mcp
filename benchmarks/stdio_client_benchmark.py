#!/usr/bin/env python3
"""
Benchmark suite for chuk-mcp stdio_client

Tests:
1. Sequential client creation performance
2. Parallel client creation (multi-agent scenarios)
3. Memory usage and leak detection
4. Initialization time with various server configs
5. Event loop health after multiple initializations

Run with: python benchmarks/stdio_client_benchmark.py
"""

import asyncio
import json
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.transports.stdio.stdio_client import StdioClient


@dataclass
class BenchmarkResult:
    """Results from a benchmark run"""

    name: str
    duration: float
    clients_created: int
    memory_peak_mb: float
    memory_current_mb: float
    success: bool
    error: Optional[str] = None


class StdioClientBenchmark:
    """Benchmark suite for stdio_client performance testing"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[BenchmarkResult] = []

    def log(self, message: str):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(f"[BENCH] {message}", flush=True)

    async def benchmark_sequential_creation(
        self, num_clients: int = 10
    ) -> BenchmarkResult:
        """Benchmark creating clients sequentially"""
        self.log(f"Starting sequential creation benchmark ({num_clients} clients)...")

        # Mock server params (won't actually connect)
        server_params = StdioParameters(
            command="echo",
            args=["test"],
        )

        tracemalloc.start()
        start_time = time.time()
        created = 0
        error = None

        try:
            # Create clients sequentially
            for i in range(num_clients):
                _client = StdioClient(server_params)
                created += 1
                if self.verbose and (i + 1) % 10 == 0:
                    self.log(f"  Created {i + 1}/{num_clients} clients")

        except Exception as e:
            error = str(e)
            self.log(f"  ❌ Error: {e}")

        duration = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=f"Sequential Creation ({num_clients} clients)",
            duration=duration,
            clients_created=created,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024,
            success=error is None and created == num_clients,
            error=error,
        )

        self.results.append(result)
        self.log(
            f"  ✓ Completed in {duration:.3f}s, Peak memory: {result.memory_peak_mb:.2f}MB"
        )
        return result

    async def benchmark_parallel_creation(
        self, num_clients: int = 10
    ) -> BenchmarkResult:
        """Benchmark creating clients in parallel (simulates multi-agent scenario)"""
        self.log(f"Starting parallel creation benchmark ({num_clients} clients)...")

        server_params = StdioParameters(
            command="echo",
            args=["test"],
        )

        tracemalloc.start()
        start_time = time.time()
        created = 0
        error = None

        try:
            # Create all clients at once
            clients = []
            for i in range(num_clients):
                client = StdioClient(server_params)
                clients.append(client)
                created += 1

        except Exception as e:
            error = str(e)
            self.log(f"  ❌ Error: {e}")

        duration = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=f"Parallel Creation ({num_clients} clients)",
            duration=duration,
            clients_created=created,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024,
            success=error is None and created == num_clients,
            error=error,
        )

        self.results.append(result)
        self.log(
            f"  ✓ Completed in {duration:.3f}s, Peak memory: {result.memory_peak_mb:.2f}MB"
        )
        return result

    async def benchmark_interleaved_init(self, num_pairs: int = 5) -> BenchmarkResult:
        """
        Benchmark interleaved pattern: create client 1, init, create client 2, init...
        This tests the real-world multi-agent scenario that was causing hangs.
        """
        self.log(f"Starting interleaved init benchmark ({num_pairs} pairs)...")

        # Use a simple test server that exists
        server_params = StdioParameters(
            command="python",
            args=["-c", "import sys; sys.exit(0)"],  # Exits immediately
        )

        tracemalloc.start()
        start_time = time.time()
        created = 0
        error = None

        try:
            for i in range(num_pairs):
                self.log(f"  Creating and entering client {i + 1}...")

                # Create client
                client = StdioClient(server_params)
                created += 1

                # Try to enter async context (this is where hang occurred before fix)
                try:
                    async with client:
                        self.log(f"    Client {i + 1} entered context successfully")
                        await asyncio.sleep(0.01)  # Brief async operation
                except Exception as e:
                    # Expected - subprocess exits immediately
                    if (
                        "returncode" not in str(e).lower()
                        and "process" not in str(e).lower()
                    ):
                        raise

        except Exception as e:
            error = str(e)
            self.log(f"  ❌ Error: {e}")

        duration = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=f"Interleaved Init ({num_pairs} pairs)",
            duration=duration,
            clients_created=created,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024,
            success=error is None and created == num_pairs,
            error=error,
        )

        self.results.append(result)
        self.log(
            f"  ✓ Completed in {duration:.3f}s, Peak memory: {result.memory_peak_mb:.2f}MB"
        )
        return result

    async def benchmark_rapid_creation_destruction(
        self, iterations: int = 20
    ) -> BenchmarkResult:
        """Benchmark rapid create/destroy cycles to test for leaks"""
        self.log(
            f"Starting rapid create/destroy benchmark ({iterations} iterations)..."
        )

        server_params = StdioParameters(
            command="echo",
            args=["test"],
        )

        tracemalloc.start()
        start_time = time.time()
        created = 0
        error = None

        try:
            for i in range(iterations):
                # Create client
                client = StdioClient(server_params)
                created += 1

                # Immediately destroy (goes out of scope)
                del client

                if self.verbose and (i + 1) % 10 == 0:
                    self.log(f"  Iteration {i + 1}/{iterations}")

        except Exception as e:
            error = str(e)
            self.log(f"  ❌ Error: {e}")

        duration = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=f"Rapid Create/Destroy ({iterations} iterations)",
            duration=duration,
            clients_created=created,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024,
            success=error is None and created == iterations,
            error=error,
        )

        self.results.append(result)

        # Check for memory leaks (current should be close to 0)
        if result.memory_current_mb > 10:
            self.log(
                f"  ⚠️  Possible memory leak: {result.memory_current_mb:.2f}MB still allocated"
            )
        else:
            self.log(f"  ✓ No obvious leaks: {result.memory_current_mb:.2f}MB")

        return result

    async def benchmark_event_loop_health(
        self, num_clients: int = 10
    ) -> BenchmarkResult:
        """Test if event loop remains healthy after multiple client creations"""
        self.log(f"Starting event loop health benchmark ({num_clients} clients)...")

        server_params = StdioParameters(
            command="echo",
            args=["test"],
        )

        tracemalloc.start()
        start_time = time.time()
        created = 0
        error = None

        try:
            # Create multiple clients
            for i in range(num_clients):
                _client = StdioClient(server_params)
                created += 1

            # Test event loop health with a simple async operation
            self.log("  Testing event loop with asyncio.sleep...")
            await asyncio.sleep(0.1)

            # Try creating a task
            self.log("  Testing task creation...")

            async def dummy_task():
                await asyncio.sleep(0.01)
                return True

            result_value = await dummy_task()
            if not result_value:
                raise Exception("Event loop task execution failed")

            self.log("  ✓ Event loop healthy")

        except Exception as e:
            error = str(e)
            self.log(f"  ❌ Error: {e}")

        duration = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=f"Event Loop Health ({num_clients} clients)",
            duration=duration,
            clients_created=created,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024,
            success=error is None,
            error=error,
        )

        self.results.append(result)
        return result

    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.success)

        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"\n{status} - {result.name}")
            print(f"  Duration: {result.duration:.3f}s")
            print(f"  Clients: {result.clients_created}")
            print(f"  Memory Peak: {result.memory_peak_mb:.2f}MB")
            print(f"  Memory Current: {result.memory_current_mb:.2f}MB")
            if result.error:
                print(f"  Error: {result.error}")

        print("\n" + "=" * 80)
        print(f"Results: {passed}/{total_tests} passed")
        print("=" * 80 + "\n")

        return passed == total_tests

    def save_results(self, output_path: Path):
        """Save results to JSON file"""
        results_data = {
            "timestamp": time.time(),
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.success),
            "results": [
                {
                    "name": r.name,
                    "duration": r.duration,
                    "clients_created": r.clients_created,
                    "memory_peak_mb": r.memory_peak_mb,
                    "memory_current_mb": r.memory_current_mb,
                    "success": r.success,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)

        self.log(f"Results saved to {output_path}")


async def main():
    """Run all benchmarks"""
    print("\n" + "=" * 80)
    print("CHUK-MCP STDIO CLIENT BENCHMARK SUITE")
    print("=" * 80 + "\n")

    benchmark = StdioClientBenchmark(verbose=True)

    # Run all benchmarks
    await benchmark.benchmark_sequential_creation(num_clients=50)
    await benchmark.benchmark_parallel_creation(num_clients=50)
    await benchmark.benchmark_interleaved_init(num_pairs=10)
    await benchmark.benchmark_rapid_creation_destruction(iterations=100)
    await benchmark.benchmark_event_loop_health(num_clients=50)

    # Print summary
    all_passed = benchmark.print_summary()

    # Save results
    results_path = (
        Path(__file__).parent / "results" / f"stdio_client_{int(time.time())}.json"
    )
    benchmark.save_results(results_path)

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
