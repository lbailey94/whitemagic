#!/usr/bin/env python3
"""
Comprehensive MCP Tools Performance Benchmark Suite
====================================================

Measures latency, throughput, and resource usage for WhiteMagic MCP tools.

Usage:
    python scripts/benchmark_mcp_tools.py [--output-dir DIR] [--iterations N]

Output:
    - benchmark_results.json (raw data)
    - benchmark_report.md (human-readable report)
    - benchmark_charts.png (visualizations)
"""

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import psutil
from whitemagic.tools.unified_api import call_tool


@dataclass
class BenchmarkResult:
    """Results from benchmarking a single tool."""

    tool_name: str
    iterations: int
    total_time_s: float
    min_time_ms: float
    max_time_ms: float
    mean_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    std_dev_ms: float
    memory_mb: float
    cpu_percent: float
    success_rate: float
    errors: list[str]


def benchmark_tool(
    tool_name: str,
    args: dict[str, Any],
    iterations: int = 100,
    warmup: int = 5,
) -> BenchmarkResult:
    """Benchmark a single tool with multiple iterations."""

    # Warmup phase
    print(f"  Warming up {tool_name}...")
    for _ in range(warmup):
        try:
            call_tool(tool_name, **args)
        except Exception:
            pass  # Ignore warmup errors

    # Measurement phase
    print(f"  Running {iterations} iterations...")
    times_ms = []
    errors = []

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    initial_cpu = process.cpu_percent(interval=None)

    total_start = time.perf_counter()

    for i in range(iterations):
        if i % 20 == 0:
            print(f"    Iteration {i}/{iterations}")

        start = time.perf_counter()
        try:
            result = call_tool(tool_name, **args)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed_ms)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed_ms)
            errors.append(f"{type(e).__name__}: {str(e)}")

    total_time = time.perf_counter() - total_start

    # Resource usage
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    final_cpu = process.cpu_percent(interval=None)

    # Calculate statistics
    if times_ms:
        sorted_times = sorted(times_ms)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)

        result = BenchmarkResult(
            tool_name=tool_name,
            iterations=iterations,
            total_time_s=total_time,
            min_time_ms=min(times_ms),
            max_time_ms=max(times_ms),
            mean_time_ms=statistics.mean(times_ms),
            median_time_ms=statistics.median(times_ms),
            p95_time_ms=sorted_times[p95_idx]
            if p95_idx < len(sorted_times)
            else sorted_times[-1],
            p99_time_ms=sorted_times[p99_idx]
            if p99_idx < len(sorted_times)
            else sorted_times[-1],
            std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
            memory_mb=final_memory - initial_memory,
            cpu_percent=final_cpu - initial_cpu,
            success_rate=(iterations - len(errors)) / iterations,
            errors=errors[:10],  # Keep first 10 errors
        )
    else:
        result = BenchmarkResult(
            tool_name=tool_name,
            iterations=iterations,
            total_time_s=total_time,
            min_time_ms=0,
            max_time_ms=0,
            mean_time_ms=0,
            median_time_ms=0,
            p95_time_ms=0,
            p99_time_ms=0,
            std_dev_ms=0,
            memory_mb=final_memory - initial_memory,
            cpu_percent=final_cpu - initial_cpu,
            success_rate=0,
            errors=["No successful iterations"],
        )

    return result


def benchmark_concurrent(
    tool_name: str,
    args: dict[str, Any],
    concurrency_levels: list[int] | None = None,
    requests_per_level: int = 50,
) -> dict[int, dict]:
    """Benchmark tool under concurrent load."""
    import concurrent.futures

    if concurrency_levels is None:
        concurrency_levels = [1, 5, 10, 20]

    results = {}

    for concurrency in concurrency_levels:
        print(f"  Testing concurrency level {concurrency}...")

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(call_tool, tool_name, **args)
                for _ in range(requests_per_level)
            ]

            successes = 0
            failures = 0

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                    successes += 1
                except Exception:
                    failures += 1

        total_time = time.perf_counter() - start_time
        throughput = requests_per_level / total_time

        results[concurrency] = {
            "concurrency": concurrency,
            "total_requests": requests_per_level,
            "successes": successes,
            "failures": failures,
            "total_time_s": total_time,
            "throughput_rps": throughput,
            "success_rate": successes / requests_per_level,
        }

    return results


def generate_report(results: list[BenchmarkResult], concurrent_results: dict) -> str:
    """Generate markdown report from benchmark results."""

    report = []
    report.append("# WhiteMagic MCP Tools Performance Benchmark Report\n")
    report.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Total tools benchmarked:** {len(results)}\n")

    # Summary table
    report.append("\n## Summary\n")
    report.append(
        "| Tool | Median (ms) | P95 (ms) | P99 (ms) | Success Rate | Memory (MB) |"
    )
    report.append(
        "|------|-------------|----------|----------|--------------|-------------|"
    )

    for r in sorted(results, key=lambda x: x.median_time_ms):
        report.append(
            f"| {r.tool_name} | {r.median_time_ms:.2f} | {r.p95_time_ms:.2f} | "
            f"{r.p99_time_ms:.2f} | {r.success_rate * 100:.1f}% | {r.memory_mb:.2f} |"
        )

    # Detailed results
    report.append("\n## Detailed Results\n")

    for r in sorted(results, key=lambda x: x.median_time_ms):
        report.append(f"\n### {r.tool_name}\n")
        report.append(f"- **Iterations:** {r.iterations}")
        report.append(f"- **Total time:** {r.total_time_s:.2f}s")
        report.append(f"- **Min:** {r.min_time_ms:.2f}ms")
        report.append(f"- **Max:** {r.max_time_ms:.2f}ms")
        report.append(f"- **Mean:** {r.mean_time_ms:.2f}ms")
        report.append(f"- **Median:** {r.median_time_ms:.2f}ms")
        report.append(f"- **P95:** {r.p95_time_ms:.2f}ms")
        report.append(f"- **P99:** {r.p99_time_ms:.2f}ms")
        report.append(f"- **Std Dev:** {r.std_dev_ms:.2f}ms")
        report.append(f"- **Memory delta:** {r.memory_mb:.2f}MB")
        report.append(f"- **CPU delta:** {r.cpu_percent:.1f}%")
        report.append(f"- **Success rate:** {r.success_rate * 100:.1f}%")

        if r.errors:
            report.append(f"- **Sample errors:**")
            for error in r.errors[:5]:
                report.append(f"  - `{error}`")

    # Concurrent results
    if concurrent_results:
        report.append("\n## Concurrent Load Testing\n")
        report.append(
            "| Concurrency | Requests | Successes | Throughput (req/s) | Success Rate |"
        )
        report.append(
            "|-------------|----------|-----------|-------------------|--------------|"
        )

        for level, data in sorted(concurrent_results.items()):
            report.append(
                f"| {data['concurrency']} | {data['total_requests']} | "
                f"{data['successes']} | {data['throughput_rps']:.2f} | "
                f"{data['success_rate'] * 100:.1f}% |"
            )

    # Recommendations
    report.append("\n## Performance Recommendations\n")

    # Identify slow tools
    slow_tools = [r for r in results if r.p95_time_ms > 1000]
    if slow_tools:
        report.append("\n### Slow Tools (P95 > 1000ms)\n")
        for r in slow_tools:
            report.append(f"- **{r.tool_name}**: {r.p95_time_ms:.0f}ms P95")
        report.append(
            "\n**Recommendation:** Consider caching, optimization, or async execution for these tools.\n"
        )

    # Identify high-memory tools
    high_memory = [r for r in results if r.memory_mb > 10]
    if high_memory:
        report.append("\n### High Memory Usage (> 10MB)\n")
        for r in high_memory:
            report.append(f"- **{r.tool_name}**: {r.memory_mb:.1f}MB")
        report.append(
            "\n**Recommendation:** Investigate memory leaks or consider streaming responses.\n"
        )

    # Identify unreliable tools
    unreliable = [r for r in results if r.success_rate < 0.95]
    if unreliable:
        report.append("\n### Unreliable Tools (Success Rate < 95%)\n")
        for r in unreliable:
            report.append(f"- **{r.tool_name}**: {r.success_rate * 100:.1f}%")
        report.append(
            "\n**Recommendation:** Investigate error causes and improve error handling.\n"
        )

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Benchmark WhiteMagic MCP tools")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Directory to save benchmark results",
    )
    parser.add_argument(
        "--iterations", type=int, default=100, help="Number of iterations per tool"
    )
    parser.add_argument(
        "--concurrent", action="store_true", help="Run concurrent load tests"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("WhiteMagic MCP Tools Performance Benchmark")
    print("=" * 70)

    # Define tools to benchmark
    tools_to_benchmark = [
        ("list_ganas", {}),
        ("list_ganas", {"quadrant": "South"}),
        ("list_ganas", {"search": "memory"}),
        ("vitality", {}),
        ("vitality", {"gana": "gana_ghost"}),
        ("discover", {}),
        ("gnosis", {"compact": True}),
        ("gnosis", {"compact": False}),
        ("capability.matrix", {}),
        ("karma_report", {}),
        ("state.summary", {}),
        ("health_report", {}),
    ]

    results = []

    print(
        f"\nBenchmarking {len(tools_to_benchmark)} tools with {args.iterations} iterations each...\n"
    )

    for tool_name, tool_args in tools_to_benchmark:
        print(f"\n{'=' * 70}")
        print(f"Benchmarking: {tool_name} {tool_args}")
        print("=" * 70)

        result = benchmark_tool(tool_name, tool_args, iterations=args.iterations)
        results.append(result)

        print(f"\n  Results:")
        print(f"    Median: {result.median_time_ms:.2f}ms")
        print(f"    P95: {result.p95_time_ms:.2f}ms")
        print(f"    P99: {result.p99_time_ms:.2f}ms")
        print(f"    Success rate: {result.success_rate * 100:.1f}%")

    # Concurrent testing
    concurrent_results = {}
    if args.concurrent:
        print(f"\n{'=' * 70}")
        print("Running concurrent load tests...")
        print("=" * 70)

        concurrent_results = benchmark_concurrent(
            "list_ganas",
            {},
            concurrency_levels=[1, 5, 10, 20],
            requests_per_level=50,
        )

    raw_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "iterations": args.iterations,
        "results": [asdict(r) for r in results],
        "concurrent_results": concurrent_results,
    }

    raw_path = output_dir / "benchmark_results.json"
    with open(raw_path, "w") as f:
        json.dump(raw_data, f, indent=2)
    print(f"\n✓ Raw results saved to {raw_path}")

    # Generate report
    report = generate_report(results, concurrent_results)
    report_path = output_dir / "benchmark_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"✓ Report saved to {report_path}")

    print("\n" + "=" * 70)
    print("Benchmark complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
