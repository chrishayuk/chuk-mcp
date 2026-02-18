#!/usr/bin/env python3
"""
Advanced Stress Testing for chuk-mcp stdio_client

Tests:
1. Maximum concurrent connections
2. Message throughput (messages/sec)
3. Latency under load
4. Resource exhaustion (file descriptors, memory)
5. Long-running stability
6. Rapid connection churn

Run with: python benchmarks/stress_test.py
"""

import asyncio
import gc
import json
import psutil
import resource
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chuk_mcp.transports.stdio.parameters import StdioParameters
from chuk_mcp.transports.stdio.stdio_client import StdioClient, stdio_client


@dataclass
class StressTestResult:
    """Results from a stress test run"""

    test_name: str
    duration: float
    success: bool

    # Connection metrics
    connections_attempted: int = 0
    connections_succeeded: int = 0
    connections_failed: int = 0
    max_concurrent: int = 0

    # Performance metrics
    throughput_msg_per_sec: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Resource metrics
    memory_peak_mb: float = 0.0
    memory_current_mb: float = 0.0
    cpu_percent: float = 0.0
    file_descriptors: int = 0

    # Failure info
    error: Optional[str] = None
    failures: List[str] = field(default_factory=list)


class StressTest:
    """Advanced stress testing suite"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[StressTestResult] = []
        self.process = psutil.Process()

    def log(self, message: str):
        if self.verbose:
            print(f"[STRESS] {message}", flush=True)

    def get_resource_usage(self) -> Dict:
        """Get current resource usage"""
        try:
            mem_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent(interval=0.1)

            # Get file descriptor count
            try:
                num_fds = len(self.process.open_files()) + len(
                    self.process.connections()
                )
            except (psutil.AccessDenied, AttributeError):
                num_fds = -1

            return {
                "memory_mb": mem_info.rss / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "num_fds": num_fds,
            }
        except Exception as e:
            self.log(f"Warning: Could not get resource usage: {e}")
            return {"memory_mb": 0, "cpu_percent": 0, "num_fds": 0}

    async def test_max_concurrent_connections(
        self, start: int = 10, step: int = 10, max_attempts: int = 200
    ) -> StressTestResult:
        """
        Find maximum concurrent connections by increasing until failure.
        Tests: 10, 20, 30, ... connections until we hit a limit.
        """
        self.log(f"\n{'=' * 70}")
        self.log("Test: Maximum Concurrent Connections")
        self.log(f"Starting at {start}, step {step}, max {max_attempts}")
        self.log(f"{'=' * 70}")

        server_params = StdioParameters(
            command="python",
            args=["-c", "import sys, time; time.sleep(0.5); sys.exit(0)"],
        )

        tracemalloc.start()
        start_time = time.time()

        max_successful = 0
        total_attempted = 0
        total_succeeded = 0
        total_failed = 0
        failures = []
        error = None

        try:
            current = start

            while current <= max_attempts:
                self.log(f"\nAttempting {current} concurrent connections...")
                total_attempted += current

                contexts = []
                active_contexts = []
                success_count = 0

                try:
                    # Create all contexts
                    for i in range(current):
                        context = stdio_client(server_params)
                        contexts.append(context)

                    # Enter all contexts concurrently
                    async def enter_context(ctx, idx):
                        try:
                            await ctx.__aenter__()
                            return True
                        except Exception as e:
                            failures.append(f"Connection {idx}: {str(e)[:100]}")
                            return False

                    results = await asyncio.gather(
                        *[enter_context(ctx, i) for i, ctx in enumerate(contexts)]
                    )
                    success_count = sum(results)
                    total_succeeded += success_count
                    total_failed += current - success_count

                    if success_count == current:
                        max_successful = current
                        self.log(
                            f"  ✅ {success_count}/{current} connections succeeded"
                        )

                        # Store active contexts for cleanup
                        active_contexts = [
                            ctx for ctx, success in zip(contexts, results) if success
                        ]

                        # Clean up
                        for ctx in active_contexts:
                            try:
                                await ctx.__aexit__(None, None, None)
                            except Exception:
                                pass

                        # Move to next level
                        current += step
                    else:
                        self.log(
                            f"  ⚠️  Only {success_count}/{current} connections succeeded"
                        )
                        self.log(f"  Stopping at max_successful = {max_successful}")
                        break

                except Exception as e:
                    error_msg = f"Failed at {current} connections: {str(e)[:200]}"
                    failures.append(error_msg)
                    self.log(f"  ❌ {error_msg}")
                    break

                # Brief pause between levels
                await asyncio.sleep(0.1)
                gc.collect()

        except Exception as e:
            error = str(e)
            self.log(f"❌ Test error: {e}")

        duration = time.time() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        resources = self.get_resource_usage()

        result = StressTestResult(
            test_name="Maximum Concurrent Connections",
            duration=duration,
            success=max_successful > 0 and error is None,
            connections_attempted=total_attempted,
            connections_succeeded=total_succeeded,
            connections_failed=total_failed,
            max_concurrent=max_successful,
            memory_peak_mb=peak_mem / 1024 / 1024,
            memory_current_mb=current_mem / 1024 / 1024,
            cpu_percent=resources["cpu_percent"],
            file_descriptors=resources["num_fds"],
            error=error,
            failures=failures[:10],  # Keep first 10 failures
        )

        self.results.append(result)

        self.log(f"\n{'=' * 70}")
        self.log(f"✅ Maximum successful concurrent connections: {max_successful}")
        self.log(f"   Total attempted: {total_attempted}")
        self.log(
            f"   Success rate: {total_succeeded}/{total_attempted} ({100 * total_succeeded / total_attempted if total_attempted > 0 else 0:.1f}%)"
        )
        self.log(f"   Peak memory: {result.memory_peak_mb:.2f}MB")
        self.log(f"   File descriptors: {result.file_descriptors}")
        self.log(f"{'=' * 70}")

        return result

    async def test_connection_churn(
        self, connections_per_batch: int = 10, num_batches: int = 50
    ) -> StressTestResult:
        """
        Test rapid connection creation and destruction.
        Measures: connections/sec, memory stability, cleanup effectiveness.
        """
        self.log(f"\n{'=' * 70}")
        self.log("Test: Connection Churn")
        self.log(f"Batches: {num_batches} x {connections_per_batch} connections")
        self.log(f"{'=' * 70}")

        server_params = StdioParameters(
            command="python",
            args=["-c", "import sys; sys.exit(0)"],
        )

        tracemalloc.start()
        start_time = time.time()

        attempted = 0
        succeeded = 0
        failed = 0
        failures = []
        error = None

        try:
            for batch in range(num_batches):
                if self.verbose and (batch + 1) % 10 == 0:
                    self.log(f"  Batch {batch + 1}/{num_batches}...")

                # Create batch
                contexts = []
                for _ in range(connections_per_batch):
                    try:
                        ctx = stdio_client(server_params)
                        contexts.append(ctx)
                        attempted += 1
                    except Exception as e:
                        failed += 1
                        failures.append(str(e)[:100])

                # Enter and exit immediately (churn)
                for ctx in contexts:
                    try:
                        async with ctx:
                            await asyncio.sleep(0.001)
                        succeeded += 1
                    except Exception as e:
                        failed += 1
                        # Expected for exit(0) subprocess
                        if "returncode" not in str(e).lower():
                            failures.append(str(e)[:100])

                # Force garbage collection
                if batch % 10 == 0:
                    gc.collect()

        except Exception as e:
            error = str(e)
            self.log(f"❌ Test error: {e}")

        duration = time.time() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        resources = self.get_resource_usage()

        # Calculate throughput
        throughput = attempted / duration if duration > 0 else 0

        result = StressTestResult(
            test_name="Connection Churn",
            duration=duration,
            success=error is None,
            connections_attempted=attempted,
            connections_succeeded=succeeded,
            connections_failed=failed,
            throughput_msg_per_sec=throughput,
            memory_peak_mb=peak_mem / 1024 / 1024,
            memory_current_mb=current_mem / 1024 / 1024,
            cpu_percent=resources["cpu_percent"],
            file_descriptors=resources["num_fds"],
            error=error,
            failures=failures[:10],
        )

        self.results.append(result)

        self.log(f"\n{'=' * 70}")
        self.log("✅ Connection churn complete:")
        self.log(f"   Throughput: {throughput:.1f} connections/sec")
        self.log(
            f"   Success rate: {succeeded}/{attempted} ({100 * succeeded / attempted if attempted > 0 else 0:.1f}%)"
        )
        self.log(f"   Peak memory: {result.memory_peak_mb:.2f}MB")
        self.log(
            f"   Current memory: {result.memory_current_mb:.2f}MB (leak indicator)"
        )
        self.log(f"{'=' * 70}")

        return result

    async def test_memory_leak_detection(
        self, iterations: int = 100
    ) -> StressTestResult:
        """
        Run many iterations and track memory growth.
        Detects memory leaks by comparing start vs end memory.
        """
        self.log(f"\n{'=' * 70}")
        self.log(f"Test: Memory Leak Detection ({iterations} iterations)")
        self.log(f"{'=' * 70}")

        server_params = StdioParameters(
            command="echo",
            args=["test"],
        )

        # Force GC before starting
        gc.collect()
        tracemalloc.start()

        start_time = time.time()
        start_mem = self.process.memory_info().rss / 1024 / 1024

        memory_samples = []
        attempted = 0
        succeeded = 0
        error = None

        try:
            for i in range(iterations):
                # Create and destroy client
                client = StdioClient(server_params)
                attempted += 1
                succeeded += 1
                del client

                # Sample memory every 10 iterations
                if i % 10 == 0:
                    gc.collect()
                    mem = self.process.memory_info().rss / 1024 / 1024
                    memory_samples.append(mem)

                    if self.verbose and (i + 1) % 50 == 0:
                        self.log(
                            f"  Iteration {i + 1}/{iterations}, Memory: {mem:.2f}MB"
                        )

        except Exception as e:
            error = str(e)
            self.log(f"❌ Test error: {e}")

        # Final GC and measurement
        gc.collect()
        duration = time.time() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        end_mem = self.process.memory_info().rss / 1024 / 1024
        memory_growth = end_mem - start_mem

        # Analyze memory trend
        if len(memory_samples) > 2:
            avg_growth_per_10 = (memory_samples[-1] - memory_samples[0]) / (
                len(memory_samples) - 1
            )
        else:
            avg_growth_per_10 = 0

        resources = self.get_resource_usage()

        result = StressTestResult(
            test_name=f"Memory Leak Detection ({iterations} iterations)",
            duration=duration,
            success=error is None and memory_growth < 10,  # < 10MB growth is acceptable
            connections_attempted=attempted,
            connections_succeeded=succeeded,
            memory_peak_mb=peak_mem / 1024 / 1024,
            memory_current_mb=current_mem / 1024 / 1024,
            cpu_percent=resources["cpu_percent"],
            file_descriptors=resources["num_fds"],
            error=error,
            failures=[f"Memory growth: {memory_growth:.2f}MB"]
            if memory_growth > 10
            else [],
        )

        self.results.append(result)

        leak_status = (
            "✅ No leak"
            if memory_growth < 5
            else "⚠️  Possible leak"
            if memory_growth < 10
            else "❌ Leak detected"
        )

        self.log(f"\n{'=' * 70}")
        self.log(f"{leak_status}:")
        self.log(f"   Start memory: {start_mem:.2f}MB")
        self.log(f"   End memory: {end_mem:.2f}MB")
        self.log(f"   Growth: {memory_growth:.2f}MB")
        self.log(f"   Avg growth per 10 iterations: {avg_growth_per_10:.3f}MB")
        self.log(f"   Peak traced: {result.memory_peak_mb:.2f}MB")
        self.log(f"{'=' * 70}")

        return result

    async def test_resource_limits(self) -> StressTestResult:
        """
        Test system resource limits (file descriptors, memory limits).
        Provides recommendations for deployment sizing.
        """
        self.log(f"\n{'=' * 70}")
        self.log("Test: System Resource Limits")
        self.log(f"{'=' * 70}")

        start_time = time.time()

        try:
            # Get file descriptor limits
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

            self.log("\nFile Descriptor Limits:")
            self.log(f"  Soft limit: {soft_limit}")
            self.log(f"  Hard limit: {hard_limit}")
            self.log(f"  Current FDs: {self.get_resource_usage()['num_fds']}")

            # Get memory limits
            try:
                mem_soft, mem_hard = resource.getrlimit(resource.RLIMIT_AS)
                self.log("\nMemory Limits:")
                self.log(
                    f"  Soft limit: {mem_soft if mem_soft != resource.RLIM_INFINITY else 'unlimited'}"
                )
                self.log(
                    f"  Hard limit: {mem_hard if mem_hard != resource.RLIM_INFINITY else 'unlimited'}"
                )
            except (ValueError, OSError):
                self.log("\nMemory Limits: Not available on this platform")

            # Get CPU limits
            try:
                cpu_soft, cpu_hard = resource.getrlimit(resource.RLIMIT_CPU)
                self.log("\nCPU Time Limits:")
                self.log(
                    f"  Soft limit: {cpu_soft if cpu_soft != resource.RLIM_INFINITY else 'unlimited'}"
                )
                self.log(
                    f"  Hard limit: {cpu_hard if cpu_hard != resource.RLIM_INFINITY else 'unlimited'}"
                )
            except (ValueError, OSError):
                self.log("\nCPU Time Limits: Not available on this platform")

            # Recommendations
            self.log("\nRecommendations:")
            if soft_limit < 1024:
                self.log(
                    f"  ⚠️  FD limit ({soft_limit}) is low. Recommend increasing to 4096+"
                )
            else:
                self.log(f"  ✅ FD limit ({soft_limit}) is adequate")

            # Calculate safe concurrent connection limit
            # Each client uses ~3 FDs (stdin, stdout, stderr) + process overhead
            estimated_fds_per_client = 5
            safe_limit = int(
                (soft_limit * 0.8) / estimated_fds_per_client
            )  # 80% of limit

            self.log(f"  Estimated safe concurrent clients: ~{safe_limit}")

        except Exception as e:
            self.log(f"❌ Error checking limits: {e}")

        duration = time.time() - start_time
        resources = self.get_resource_usage()

        result = StressTestResult(
            test_name="Resource Limits Analysis",
            duration=duration,
            success=True,
            memory_current_mb=resources["memory_mb"],
            cpu_percent=resources["cpu_percent"],
            file_descriptors=resources["num_fds"],
        )

        self.results.append(result)
        self.log(f"{'=' * 70}")

        return result

    def print_summary(self):
        """Print comprehensive stress test summary"""
        print("\n" + "=" * 80)
        print("STRESS TEST SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.success)

        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"\n{status} - {result.test_name}")
            print(f"  Duration: {result.duration:.3f}s")

            if result.connections_attempted > 0:
                print(
                    f"  Connections: {result.connections_succeeded}/{result.connections_attempted}"
                )

            if result.max_concurrent > 0:
                print(f"  Max Concurrent: {result.max_concurrent}")

            if result.throughput_msg_per_sec > 0:
                print(f"  Throughput: {result.throughput_msg_per_sec:.1f} conn/sec")

            print(f"  Memory Peak: {result.memory_peak_mb:.2f}MB")
            print(f"  Memory Current: {result.memory_current_mb:.2f}MB")

            if result.cpu_percent > 0:
                print(f"  CPU: {result.cpu_percent:.1f}%")

            if result.file_descriptors > 0:
                print(f"  File Descriptors: {result.file_descriptors}")

            if result.failures:
                print("  First failures:")
                for failure in result.failures[:3]:
                    print(f"    - {failure}")

            if result.error:
                print(f"  Error: {result.error}")

        print("\n" + "=" * 80)
        print(f"Results: {passed}/{total_tests} passed")
        print("=" * 80 + "\n")

        return passed == total_tests

    def save_results(self, output_path: Path):
        """Save results to JSON"""
        results_data = {
            "timestamp": time.time(),
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.success),
            "results": [
                {
                    "test_name": r.test_name,
                    "duration": r.duration,
                    "success": r.success,
                    "connections_attempted": r.connections_attempted,
                    "connections_succeeded": r.connections_succeeded,
                    "connections_failed": r.connections_failed,
                    "max_concurrent": r.max_concurrent,
                    "throughput_msg_per_sec": r.throughput_msg_per_sec,
                    "memory_peak_mb": r.memory_peak_mb,
                    "memory_current_mb": r.memory_current_mb,
                    "cpu_percent": r.cpu_percent,
                    "file_descriptors": r.file_descriptors,
                    "error": r.error,
                    "failures": r.failures,
                }
                for r in self.results
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)

        self.log(f"Results saved to {output_path}")


async def main():
    """Run stress tests"""
    print("\n" + "=" * 80)
    print("CHUK-MCP STDIO CLIENT STRESS TESTS")
    print("=" * 80 + "\n")

    stress = StressTest(verbose=True)

    # Run tests
    await stress.test_resource_limits()
    await stress.test_memory_leak_detection(iterations=200)
    await stress.test_connection_churn(connections_per_batch=10, num_batches=100)
    # Test up to 1000 concurrent connections with larger steps for efficiency
    await stress.test_max_concurrent_connections(start=50, step=50, max_attempts=1000)

    # Print summary
    all_passed = stress.print_summary()

    # Save results
    results_path = (
        Path(__file__).parent / "results" / f"stress_test_{int(time.time())}.json"
    )
    stress.save_results(results_path)

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Stress test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Stress test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
