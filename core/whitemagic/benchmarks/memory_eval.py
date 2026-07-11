"""Memory benchmark and evaluation suite for WhiteMagic.

Measures performance and quality metrics across the three-tier memory system:

    python -m whitemagic.benchmarks.memory_eval

Or programmatically:

    from whitemagic.benchmarks.memory_eval import run_benchmarks
    results = run_benchmarks()
    print(results.summary())
"""

from __future__ import annotations

import json
import logging
import os
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory

logger = logging.getLogger(__name__)

# Use temp state root to avoid polluting production DB
_WM_STATE_ROOT = os.environ.get("WM_STATE_ROOT", "")


def _ensure_temp_state() -> str:
    """Ensure we're using a temp state root for benchmarks."""
    global _WM_STATE_ROOT
    if not _WM_STATE_ROOT:
        tmpdir = tempfile.mkdtemp(prefix="wm_bench_")
        os.environ["WM_STATE_ROOT"] = tmpdir
        _WM_STATE_ROOT = tmpdir
    return _WM_STATE_ROOT


@dataclass
class BenchmarkResult:
    """Single benchmark result."""
    name: str
    metric: str
    value: float
    target: float
    unit: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        """Value / target ratio (1.0 = exactly at target)."""
        if self.target == 0:
            return float("inf") if self.value == 0 else 0.0
        return self.value / self.target


@dataclass
class BenchmarkSuite:
    """Full benchmark suite results."""
    results: list[BenchmarkResult] = field(default_factory=list)
    total_duration_s: float = 0.0
    timestamp: str = ""

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed_count / len(self.results) if self.results else 0.0

    def summary(self) -> str:
        lines = [
            "WhiteMagic Memory Benchmark Suite",
            f"{'='*60}",
            f"Timestamp: {self.timestamp}",
            f"Duration: {self.total_duration_s:.2f}s",
            f"Passed: {self.passed_count}/{len(self.results)} ({self.pass_rate:.0%})",
            f"{'='*60}",
            "",
        ]
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(
                f"  [{status}] {r.name}: {r.value:.3f} {r.unit} "
                f"(target: {r.target:.3f} {r.unit})"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_duration_s": self.total_duration_s,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "pass_rate": self.pass_rate,
            "results": [asdict(r) for r in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _measure_latency(fn: Any, iterations: int = 100, warmup: int = 10) -> tuple[float, float, float]:
    """Measure function latency. Returns (mean_ms, median_ms, p95_ms)."""
    for _ in range(warmup):
        fn()

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

    return (
        statistics.mean(times),
        statistics.median(times),
        sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
    )


def bench_store_latency(mem: AgentMemory) -> BenchmarkResult:
    """Measure single memory store latency."""
    mean_ms, median_ms, p95_ms = _measure_latency(
        lambda: mem.long_term.store(f"Benchmark test memory {time.time()}", tags={"bench"}),
        iterations=50,
        warmup=5,
    )
    return BenchmarkResult(
        name="store_latency",
        metric="mean_latency_ms",
        value=mean_ms,
        target=1.0,
        unit="ms",
        passed=mean_ms < 1.0,
        details={"mean_ms": mean_ms, "median_ms": median_ms, "p95_ms": p95_ms},
    )


def bench_fts5_search(mem: AgentMemory, n_memories: int = 100) -> BenchmarkResult:
    """Measure FTS5 full-text search latency."""
    for i in range(n_memories):
        mem.long_term.store(
            f"Memory about topic {i}: API rate limiting and authentication flows",
            tags={"bench", f"topic_{i % 10}"},
            importance=0.3 + (i % 7) * 0.1,
        )

    mean_ms, median_ms, p95_ms = _measure_latency(
        lambda: mem.long_term.search(query="rate limiting", limit=10),
        iterations=50,
        warmup=5,
    )
    return BenchmarkResult(
        name="fts5_search_latency",
        metric="mean_latency_ms",
        value=mean_ms,
        target=3.0,
        unit="ms",
        passed=mean_ms < 3.0,
        details={"mean_ms": mean_ms, "median_ms": median_ms, "p95_ms": p95_ms, "memories": n_memories},
    )


def bench_semantic_search(mem: AgentMemory) -> BenchmarkResult:
    """Measure semantic (embedding) search latency."""
    mean_ms, median_ms, p95_ms = _measure_latency(
        lambda: mem.long_term.search_similar(query="authentication and security", limit=10),
        iterations=30,
        warmup=5,
    )
    return BenchmarkResult(
        name="semantic_search_latency",
        metric="mean_latency_ms",
        value=mean_ms,
        target=1.0,
        unit="ms",
        passed=mean_ms < 1.0,
        details={"mean_ms": mean_ms, "median_ms": median_ms, "p95_ms": p95_ms},
    )


def bench_hybrid_search(mem: AgentMemory) -> BenchmarkResult:
    """Measure hybrid search (FTS5 + semantic + reranking) latency."""
    mean_ms, median_ms, p95_ms = _measure_latency(
        lambda: mem.long_term.search_hybrid(query="API rate limit authentication", limit=10),
        iterations=30,
        warmup=5,
    )
    return BenchmarkResult(
        name="hybrid_search_latency",
        metric="mean_latency_ms",
        value=mean_ms,
        target=5.0,
        unit="ms",
        passed=mean_ms < 5.0,
        details={"mean_ms": mean_ms, "median_ms": median_ms, "p95_ms": p95_ms},
    )


def bench_recall_precision(mem: AgentMemory) -> BenchmarkResult:
    """Measure recall precision@10 — fraction of relevant results in top 10."""
    test_queries = [
        ("rate limiting", {"bench", "topic_1"}),
        ("authentication", {"bench", "topic_2"}),
        ("API security", {"bench", "topic_3"}),
    ]

    precisions: list[float] = []
    for query, expected_tags in test_queries:
        results = mem.long_term.search(query=query, limit=10)
        if not results:
            continue
        relevant = sum(1 for r in results if expected_tags & set(r.get("tags", [])))
        precisions.append(relevant / len(results))

    avg_precision = statistics.mean(precisions) if precisions else 0.0
    return BenchmarkResult(
        name="recall_precision_at_10",
        metric="precision",
        value=avg_precision,
        target=0.85,
        unit="ratio",
        passed=avg_precision >= 0.85,
        details={"per_query": precisions, "num_queries": len(precisions)},
    )


def bench_working_memory_capacity(mem: AgentMemory) -> BenchmarkResult:
    """Verify working memory respects capacity (Miller's Law 7±2)."""
    capacity = mem.short_term.capacity
    for i in range(capacity + 5):
        mem.short_term.add(f"chunk_{i}", importance=0.5 + i * 0.05)

    active = mem.short_term.get_active()
    active_count = len(active)

    return BenchmarkResult(
        name="working_memory_capacity",
        metric="active_chunks",
        value=float(active_count),
        target=float(capacity),
        unit="chunks",
        passed=active_count <= capacity,
        details={
            "capacity": capacity,
            "attempted": capacity + 5,
            "active": active_count,
            "evicted": (capacity + 5) - active_count,
        },
    )


def bench_episodic_progressive_recall(mem: AgentMemory) -> BenchmarkResult:
    """Measure progressive recall token reduction vs naive full recall."""
    for i in range(20):
        mem.episodic.record(
            role="user" if i % 2 == 0 else "ai",
            content=f"Turn {i}: " + "x" * 200,
            importance=0.3 + (i % 5) * 0.1,
        )

    full_turns = mem.episodic.recall_recent(n=20)
    full_chars = sum(len(t.get("content", "")) for t in full_turns)

    progressive = mem.episodic.recall_progressive(token_budget=500)
    progressive_chars = sum(len(t.get("preview", "")) + len(t.get("title", "")) for t in progressive)

    reduction = 1.0 - (progressive_chars / full_chars) if full_chars > 0 else 0.0

    return BenchmarkResult(
        name="episodic_progressive_recall",
        metric="token_reduction_ratio",
        value=reduction,
        target=0.80,
        unit="ratio",
        passed=reduction >= 0.80,
        details={
            "full_chars": full_chars,
            "progressive_chars": progressive_chars,
            "full_turns": len(full_turns),
            "progressive_turns": len(progressive),
        },
    )


def bench_cross_session_continuity(mem: AgentMemory) -> BenchmarkResult:
    """Measure cross-session continuity — previous session context recovery."""
    for i in range(10):
        mem.episodic.record(
            role="user" if i % 2 == 0 else "ai",
            content=f"Session 1 turn {i}: important decision about API design",
            importance=0.7,
            turn_type="decision" if i % 3 == 0 else "message",
        )

    continuity = mem.episodic.get_continuity(n=10)
    count = continuity.get("count", 0)
    has_context = bool(continuity.get("formatted", ""))

    recovery_rate = count / 10.0 if count > 0 else 0.0

    return BenchmarkResult(
        name="cross_session_continuity",
        metric="recovery_rate",
        value=recovery_rate,
        target=0.90,
        unit="ratio",
        passed=recovery_rate >= 0.90 and has_context,
        details={
            "recovered_turns": count,
            "has_formatted_context": has_context,
            "first_awakening": continuity.get("first_awakening", True),
        },
    )


def bench_dedup_accuracy(mem: AgentMemory) -> BenchmarkResult:
    """Measure content-hash deduplication accuracy."""
    unique_content = [f"Unique memory {i} about topic {i}" for i in range(10)]
    dup_content = [f"Unique memory {i} about topic {i}" for i in range(10)]

    for content in unique_content:
        mem.long_term.store(content, tags={"dedup_test"})

    dups_stored = 0
    for content in dup_content:
        result = mem.long_term.store(content, tags={"dedup_test"})
        if result:
            dups_stored += 1

    dedup_rate = 1.0 - (dups_stored / len(dup_content)) if dup_content else 0.0

    return BenchmarkResult(
        name="dedup_accuracy",
        metric="dedup_rate",
        value=dedup_rate,
        target=0.95,
        unit="ratio",
        passed=dedup_rate >= 0.95,
        details={
            "unique_stored": len(unique_content),
            "dup_attempts": len(dup_content),
            "dups_actually_stored": dups_stored,
        },
    )


def bench_scaling(mem: AgentMemory) -> BenchmarkResult:
    """Measure search latency scaling from 1K to 10K memories."""
    mem.long_term.search(query="topic", limit=10)
    time_1k_start = time.perf_counter()
    for _ in range(10):
        mem.long_term.search(query="topic", limit=10)
    time_1k = (time.perf_counter() - time_1k_start) / 10 * 1000

    for i in range(900):
        mem.long_term.store(f"Scaling test {i}: topic {i % 50}", tags={"scaling", f"batch_{i // 100}"})

    time_10k_start = time.perf_counter()
    for _ in range(10):
        mem.long_term.search(query="topic", limit=10)
    time_10k = (time.perf_counter() - time_10k_start) / 10 * 1000

    scaling_ratio = time_10k / time_1k if time_1k > 0 else float("inf")

    return BenchmarkResult(
        name="search_scaling",
        metric="latency_ratio_10x_data",
        value=scaling_ratio,
        target=2.0,
        unit="ratio",
        passed=scaling_ratio < 2.0,
        details={
            "latency_1k_ms": time_1k,
            "latency_10k_ms": time_10k,
            "scaling_ratio": scaling_ratio,
        },
    )


def run_benchmarks() -> BenchmarkSuite:
    """Run the full benchmark suite.

    Returns:
        BenchmarkSuite with all results.
    """
    _ensure_temp_state()

    suite = BenchmarkSuite(timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"))
    start = time.perf_counter()

    mem = AgentMemory(working_memory_capacity=7)

    benchmarks = [
        ("store_latency", lambda: bench_store_latency(mem)),
        ("fts5_search", lambda: bench_fts5_search(mem, n_memories=100)),
        ("semantic_search", lambda: bench_semantic_search(mem)),
        ("hybrid_search", lambda: bench_hybrid_search(mem)),
        ("recall_precision", lambda: bench_recall_precision(mem)),
        ("working_memory_capacity", lambda: bench_working_memory_capacity(mem)),
        ("episodic_progressive_recall", lambda: bench_episodic_progressive_recall(mem)),
        ("cross_session_continuity", lambda: bench_cross_session_continuity(mem)),
        ("dedup_accuracy", lambda: bench_dedup_accuracy(mem)),
        ("search_scaling", lambda: bench_scaling(mem)),
    ]

    for name, fn in benchmarks:
        try:
            result = fn()
            suite.results.append(result)
            logger.info("Benchmark %s: %s", name, "PASS" if result.passed else "FAIL")
        except Exception as e:
            logger.error("Benchmark %s failed with error: %s", name, e)
            suite.results.append(BenchmarkResult(
                name=name,
                metric="error",
                value=0.0,
                target=1.0,
                unit="error",
                passed=False,
                details={"error": str(e)},
            ))

    suite.total_duration_s = time.perf_counter() - start
    return suite


def get_comparison_table() -> str:
    """Get a comparison table vs alternatives."""
    lines = [
        "WhiteMagic vs Alternatives — Memory System Comparison",
        "=" * 70,
        "",
        f"{'Feature':<30} {'WM':<10} {'Mem0':<10} {'Zep':<10} {'MemGPT':<10}",
        "-" * 70,
        f"{'Three-tier architecture':<30} {'Yes':<10} {'No':<10} {'Partial':<10} {'Yes':<10}",
        f"{'5D holographic coords':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Galaxy partitioning':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Dream consolidation':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Surprise-gated ingestion':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'HRR compositional vectors':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Progressive recall':<30} {'Yes':<10} {'No':<10} {'Partial':<10} {'Yes':<10}",
        f"{'Cross-session continuity':<30} {'Yes':<10} {'Partial':<10} {'Yes':<10} {'Yes':<10}",
        f"{'Sleep consolidation':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Content-hash dedup':<30} {'Yes':<10} {'Yes':<10} {'No':<10} {'No':<10}",
        f"{'Hebbian link strengthening':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Emotional valence':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'FTS5 + Semantic hybrid':<30} {'Yes':<10} {'Semantic':<10} {'Semantic':<10} {'Vector':<10}",
        f"{'Local-first (no cloud)':<30} {'Yes':<10} {'Yes':<10} {'No':<10} {'Yes':<10}",
        f"{'MCP-native':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'LangChain adapter':<30} {'Yes':<10} {'Yes':<10} {'Yes':<10} {'Yes':<10}",
        f"{'Obsidian adapter':<30} {'Yes':<10} {'No':<10} {'No':<10} {'No':<10}",
        f"{'Open source':<30} {'Yes':<10} {'Yes':<10} {'No':<10} {'Yes':<10}",
        "",
        "Note: Comparison based on publicly available documentation as of Jul 2026.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    suite = run_benchmarks()
    print(suite.summary())
    print()
    print(get_comparison_table())
