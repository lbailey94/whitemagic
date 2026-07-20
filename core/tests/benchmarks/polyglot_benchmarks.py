import pytest

pytestmark = pytest.mark.performance

"""Performance benchmarking suite for polyglot operations.

Benchmarks performance across:
- Python native implementations
- Rust-accelerated operations
- Go-accelerated operations
- Zig-accelerated operations
- FFI overhead
"""

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    iterations: int
    total_time_ms: float
    mean_time_ms: float
    median_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    ops_per_second: float


class BenchmarkSuite:
    """Performance benchmarking suite for polyglot operations."""

    def __init__(self, warmup_iterations: int = 3, benchmark_iterations: int = 10):
        self.warmup_iterations = warmup_iterations
        self.benchmark_iterations = benchmark_iterations
        self.results: list[BenchmarkResult] = []

    def benchmark(self, func: Callable, name: str, *args, **kwargs) -> BenchmarkResult:
        """Benchmark a function with warmup and measurement phases.

        Args:
            func: Function to benchmark
            name: Name of the benchmark
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            BenchmarkResult with timing statistics
        """
        from whitemagic.utils.progress_bar import ProgressBar

        total = self.warmup_iterations + self.benchmark_iterations
        bar = ProgressBar(total=total, label=name)
        bar.start()

        # Warmup phase
        for _ in range(self.warmup_iterations):
            func(*args, **kwargs)
            bar.advance()

        # Measurement phase
        timings_ms = []
        for _ in range(self.benchmark_iterations):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            timings_ms.append((end - start) * 1000)
            bar.advance()

        bar.finish()

        # Calculate statistics
        total_time = sum(timings_ms)
        mean_time = statistics.mean(timings_ms)
        median_time = statistics.median(timings_ms)
        min_time = min(timings_ms)
        max_time = max(timings_ms)
        std_dev = statistics.stdev(timings_ms) if len(timings_ms) > 1 else 0.0
        ops_per_second = 1000.0 / mean_time if mean_time > 0 else 0.0

        result = BenchmarkResult(
            name=name,
            iterations=self.benchmark_iterations,
            total_time_ms=total_time,
            mean_time_ms=mean_time,
            median_time_ms=median_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            std_dev_ms=std_dev,
            ops_per_second=ops_per_second,
        )

        self.results.append(result)
        return result

    def print_results(self) -> None:
        """Print all benchmark results in a formatted table."""
        if not self.results:
            print("No benchmark results to display.")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)
        print(f"{'Name':<40} {'Mean (ms)':<12} {'Median (ms)':<12} {'Ops/s':<12}")
        print("-" * 80)

        for result in self.results:
            print(
                f"{result.name:<40} "
                f"{result.mean_time_ms:<12.4f} "
                f"{result.median_time_ms:<12.4f} "
                f"{result.ops_per_second:<12.2f}"
            )

        print("=" * 80)

    def compare_speedup(self, baseline_name: str, comparison_name: str) -> float:
        """Calculate speedup between two benchmarks.

        Args:
            baseline_name: Name of baseline benchmark
            comparison_name: Name of comparison benchmark

        Returns:
            Speedup factor (comparison is X times faster than baseline)
        """
        baseline = next((r for r in self.results if r.name == baseline_name), None)
        comparison = next((r for r in self.results if r.name == comparison_name), None)

        if not baseline or not comparison:
            raise ValueError(
                f"Could not find benchmarks: {baseline_name}, {comparison_name}"
            )

        if baseline.mean_time_ms == 0:
            return float("inf")

        return baseline.mean_time_ms / comparison.mean_time_ms


# ---------------------------------------------------------------------------
# Benchmark Functions
# ---------------------------------------------------------------------------


def benchmark_string_processing():
    """Benchmark string processing operations."""
    suite = BenchmarkSuite(warmup_iterations=2, benchmark_iterations=5)

    # Test data
    test_text = "This is a sample text for benchmarking string operations. " * 100

    # Python native
    def python_lower():
        return test_text.lower()

    suite.benchmark(python_lower, "Python: str.lower()")

    # Python regex
    import re

    pattern = re.compile(r"\b\w+\b")

    def python_regex():
        return pattern.findall(test_text)

    suite.benchmark(python_regex, "Python: regex.findall()")

    suite.print_results()
    return suite


def benchmark_list_operations():
    """Benchmark list operations."""
    suite = BenchmarkSuite(warmup_iterations=2, benchmark_iterations=5)

    # Test data
    test_list = list(range(10000))

    # Python native
    def python_sum():
        return sum(test_list)

    suite.benchmark(python_sum, "Python: sum()")

    def python_filter():
        return [x for x in test_list if x % 2 == 0]

    suite.benchmark(python_filter, "Python: list comprehension")

    suite.print_results()
    return suite


def benchmark_dict_operations():
    """Benchmark dictionary operations."""
    suite = BenchmarkSuite(warmup_iterations=2, benchmark_iterations=5)

    # Test data
    test_dict = {f"key_{i}": f"value_{i}" for i in range(10000)}

    def python_dict_get():
        return [test_dict.get(f"key_{i}") for i in range(1000)]

    suite.benchmark(python_dict_get, "Python: dict.get()")

    def python_dict_keys():
        return list(test_dict.keys())

    suite.benchmark(python_dict_keys, "Python: dict.keys()")

    suite.print_results()
    return suite


def benchmark_memory_operations():
    """Benchmark memory-like operations (simplified)."""
    suite = BenchmarkSuite(warmup_iterations=2, benchmark_iterations=5)

    # Test data
    test_items = [{"id": i, "content": f"item_{i}"} for i in range(1000)]

    def python_filter_items():
        return [item for item in test_items if item["id"] % 2 == 0]

    suite.benchmark(python_filter_items, "Python: filter list of dicts")

    def python_sort_items():
        return sorted(test_items, key=lambda x: x["id"])

    suite.benchmark(python_sort_items, "Python: sort list of dicts")

    suite.print_results()
    return suite


def run_all_benchmarks() -> dict[str, BenchmarkSuite]:
    """Run all benchmark suites.

    Returns:
        Dictionary mapping suite names to BenchmarkSuite objects
    """
    results = {}

    print("Running string processing benchmarks...")
    results["string_processing"] = benchmark_string_processing()

    print("\nRunning list operation benchmarks...")
    results["list_operations"] = benchmark_list_operations()

    print("\nRunning dict operation benchmarks...")
    results["dict_operations"] = benchmark_dict_operations()

    print("\nRunning memory operation benchmarks...")
    results["memory_operations"] = benchmark_memory_operations()

    return results


if __name__ == "__main__":
    # Run all benchmarks
    all_results = run_all_benchmarks()

    # Print summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    for suite_name, suite in all_results.items():
        print(f"\n{suite_name}:")
        for result in suite.results:
            print(
                f"  {result.name}: {result.mean_time_ms:.4f}ms mean, {result.ops_per_second:.2f} ops/s"
            )
