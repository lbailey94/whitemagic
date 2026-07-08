#!/usr/bin/env python3
"""WhiteMagic Benchmark Gauntlet
=================================

Comprehensive performance benchmarks across all subsystems.

Tests:
1. Memory Pipeline (store, search, recall)
2. Resonance Models (decay, patterns, constellations, harmony)
3. REST API Endpoints (latency, throughput)
4. Julia Ports (KD-tree, neighbors, stats)
5. Association Graph (query, traversal)
6. Embedding Pipeline (lookup, similarity)
7. Database Queries (complex joins, aggregations)
8. Dream Cycle (generation, consolidation)

Usage:
    python scripts/benchmark_gauntlet.py
    python scripts/benchmark_gauntlet.py --output reports/benchmark.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

from whitemagic.config.paths import DB_PATH
from whitemagic.core.memory.db_manager import safe_connect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("benchmark")


def get_conn() -> sqlite3.Connection:
    conn = safe_connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# Benchmark Runner


class BenchmarkSuite:
    def __init__(self):
        self.results = {}
        self.start_time = time.perf_counter()
        self._bench_index = 0
        self._bench_total = 0
        self._phase_bar = None

    def set_phase_progress(self, total: int, label: str = "Gauntlet"):
        """Initialize the overall gauntlet progress bar."""
        from whitemagic.utils.progress_bar import ProgressBar

        if self._phase_bar is not None:
            self._phase_bar.finish()
        self._phase_bar = ProgressBar(total=total, label=label)
        self._phase_bar.start()

    def advance_phase(self, label: str = ""):
        """Advance the gauntlet progress bar by one benchmark."""
        if self._phase_bar is not None:
            self._phase_bar.advance()
            if label:
                self._phase_bar.set_label(label)

    def finish_phase(self):
        """Finish the gauntlet progress bar."""
        if self._phase_bar is not None:
            self._phase_bar.finish()
            self._phase_bar = None

    def run(self, name: str, fn, iterations: int = 10, warmup: int = 2):
        """Run a benchmark function and collect stats."""
        log.info("  Running %s (%s iterations)...", name, iterations)

        from whitemagic.utils.progress_bar import ProgressBar

        bar = ProgressBar(
            total=iterations + warmup,
            label=name,
            counters={"warm": warmup},
        )
        bar.start()

        # Warmup
        for _ in range(warmup):
            fn()
            bar.advance(**{"warm": 0})  # just tick completed, don't change counter

        # Timed runs
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            fn()
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
            bar.advance()

        bar.finish()

        stats = {
            "mean_ms": round(statistics.mean(times), 3),
            "median_ms": round(statistics.median(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
            "stdev_ms": round(statistics.stdev(times), 3) if len(times) > 1 else 0,
            "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 3),
            "iterations": iterations,
        }

        self.results[name] = stats
        log.info(
            "    Mean: %sms, Median: %sms, P95: %sms",
            stats["mean_ms"],
            stats["median_ms"],
            stats["p95_ms"],
        )

        return stats

    def summary(self):
        total_time = time.perf_counter() - self.start_time
        return {
            "timestamp": datetime.now().isoformat(),
            "total_time_seconds": round(total_time, 2),
            "benchmarks": self.results,
        }


# Benchmarks


def bench_memory_pipeline(suite: BenchmarkSuite):
    log.info("\n═══ 1. Memory Pipeline ═══")
    conn = get_conn()

    def store_memory():
        with conn:  # Single transaction — reduces WAL checkpoint variance
            conn.execute(
                """
                INSERT INTO memories (content, title, memory_type, importance, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    "benchmark content",
                    "benchmark title",
                    "long_term",
                    0.5,
                    datetime.now().isoformat(),
                ),
            )
            conn.execute("DELETE FROM memories WHERE title = 'benchmark title'")

    suite.run("memory_store", store_memory, iterations=20)

    # Search benchmark
    def search_memories():
        conn.execute("SELECT * FROM memories WHERE content LIKE ? LIMIT 50", ("%the%",))
        conn.execute(
            "SELECT * FROM memories WHERE title LIKE ? LIMIT 50", ("%memory%",)
        )

    suite.run("memory_search", search_memories, iterations=20)

    # Recall benchmark
    def recall_memory():
        conn.execute("SELECT * FROM memories ORDER BY importance DESC LIMIT 1")

    suite.run("memory_recall", recall_memory, iterations=50)

    # Count benchmark
    def count_memories():
        conn.execute("SELECT COUNT(*) FROM memories").fetchone()

    suite.run("memory_count", count_memories, iterations=50)

    conn.close()


def bench_resonance_models(suite: BenchmarkSuite):
    log.info("\n═══ 2. Resonance Models ═══")

    from whitemagic.core.resonance.resonance_models import (
        MemoryDecayModel,
        PatternResonanceDetector,
        ConstellationMerger,
        Constellation,
        GardenResonanceMatrix,
    )

    # Decay prediction
    decay = MemoryDecayModel()

    def predict_decay():
        decay.predict_retention(importance=0.7, age_days=30, access_count=5)

    suite.run("decay_prediction", predict_decay, iterations=100)

    # Decay curve
    def decay_curve():
        decay.predict_decay_curve(importance=0.5, days=90, step=7)

    suite.run("decay_curve", decay_curve, iterations=50)

    # Pattern detection (small dataset)
    detector = PatternResonanceDetector()
    memories = [
        {
            "id": i,
            "importance": 0.5 + i * 0.01,
            "resonance": {
                "frequency": 2.0 + i * 0.05,
                "damping": 0.1,
                "garden": "knowledge",
            },
        }
        for i in range(100)
    ]

    def find_patterns():
        detector.find_resonant_patterns(memories, min_cluster_size=2)

    suite.run("pattern_detection_100", find_patterns, iterations=20)

    # Constellation merge
    merger = ConstellationMerger(overlap_threshold=0.3)
    constellations = [
        Constellation(
            i,
            [i * 10, i * 10 + 1],
            (0.1 * i, 0.2 * i, 0.3 * i, 0.8, 0.5),
            0.3,
            0.7,
            "knowledge",
        )
        for i in range(20)
    ]

    def merge_constellations():
        merger.merge_overlapping(constellations)

    suite.run("constellation_merge_20", merge_constellations, iterations=20)

    # Garden harmony
    matrix = GardenResonanceMatrix()
    gardens = {
        f"garden_{i}": {
            "memory_count": 100,
            "avg_frequency": 1.0 + i * 0.3,
            "avg_damping": 0.1 + i * 0.02,
        }
        for i in range(10)
    }

    def calculate_harmony():
        matrix.calculate_inter_garden_harmony(gardens)

    suite.run("garden_harmony_10", calculate_harmony, iterations=50)


def bench_julia_ports(suite: BenchmarkSuite):
    log.info("\n═══ 3. Julia Ports ═══")

    from whitemagic.core.resonance.julia_resonance import get_resonance_engine

    engine = get_resonance_engine()

    def get_stats():
        engine.get_stats()

    suite.run("resonance_stats", get_stats, iterations=20)

    # Skip find_neighbors benchmarks (requires real memory IDs)
    suite.run("find_neighbors_100", lambda: None, iterations=1)
    suite.results["find_neighbors_100"]["note"] = "skipped (requires real memory IDs)"
    suite.run("find_neighbors_500", lambda: None, iterations=1)
    suite.results["find_neighbors_500"]["note"] = "skipped (requires real memory IDs)"


def bench_memory_stats(suite: BenchmarkSuite):
    log.info("\n═══ 4. Memory Stats ═══")

    from whitemagic.core.resonance.memory_stats import MemoryStatsAnalyzer

    analyzer = MemoryStatsAnalyzer()

    # Importance distribution
    scores = [0.5 + i * 0.001 for i in range(1000)]

    def analyze_importance():
        analyzer.analyze_importance_distribution(scores)

    suite.run("importance_distribution_1000", analyze_importance, iterations=50)

    # Zone transitions
    before = [0.1 + i * 0.001 for i in range(1000)]
    after = [0.15 + i * 0.001 for i in range(1000)]

    def zone_transitions():
        analyzer.zone_transition_matrix(before, after)

    suite.run("zone_transitions_1000", zone_transitions, iterations=50)

    # Outlier detection
    values = [0.5 + i * 0.001 for i in range(1000)] + [5.0, 6.0, 7.0]

    def detect_outliers():
        analyzer.detect_outliers(values)

    suite.run("outlier_detection_1003", detect_outliers, iterations=50)


def bench_self_model_forecast(suite: BenchmarkSuite):
    log.info("\n═══ 5. Self-Model Forecast ═══")

    from whitemagic.core.resonance.self_model_forecast import SelfModelForecaster

    forecaster = SelfModelForecaster()

    # Forecast
    values = [0.5 + i * 0.01 for i in range(100)]

    def forecast():
        forecaster.forecast_metric(values, steps=5)

    suite.run("forecast_100", forecast, iterations=50)

    # Anomaly detection
    def detect_anomalies():
        forecaster.detect_anomalies(values)

    suite.run("anomaly_detection_100", detect_anomalies, iterations=50)

    # Correlation matrix
    metrics = {
        f"metric_{i}": [0.5 + j * 0.01 + i * 0.1 for j in range(50)] for i in range(5)
    }

    def correlation_matrix():
        forecaster.correlation_matrix(metrics)

    suite.run("correlation_5x50", correlation_matrix, iterations=30)

    # Batch forecast
    def batch_forecast():
        forecaster.batch_forecast(metrics, steps=3)

    suite.run("batch_forecast_5", batch_forecast, iterations=30)


def bench_db_queries(suite: BenchmarkSuite):
    log.info("\n═══ 6. Database Queries ═══")
    conn = get_conn()

    # Simple select
    def simple_select():
        conn.execute("SELECT * FROM memories LIMIT 100").fetchall()

    suite.run("simple_select_100", simple_select, iterations=50)

    # Complex join
    def complex_join():
        conn.execute("""
            SELECT m.id, m.title, m.importance, hc.x, hc.y, hc.z, hc.w, hc.v
            FROM memories m
            JOIN holographic_coords hc ON m.id = hc.memory_id
            ORDER BY m.importance DESC
            LIMIT 100
        """).fetchall()

    suite.run("complex_join_100", complex_join, iterations=30)

    # Aggregation
    def aggregation():
        conn.execute("""
            SELECT json_extract(metadata, '$.garden') as garden,
                   COUNT(*) as count,
                   AVG(importance) as avg_importance
            FROM memories
            GROUP BY garden
        """).fetchall()

    suite.run("aggregation_gardens", aggregation, iterations=50)

    # Cached aggregation (materialized cache)
    def cached_aggregation():
        conn.execute("SELECT * FROM cache_garden_stats").fetchall()

    suite.run("cached_aggregation_gardens", cached_aggregation, iterations=50)

    # Association query
    def association_query():
        conn.execute("""
            SELECT a.source_id, a.target_id, a.association_type, a.strength
            FROM associations a
            WHERE a.strength > 0.5
            LIMIT 100
        """).fetchall()

    suite.run("association_query", association_query, iterations=30)

    conn.close()


def bench_dream_cycle(suite: BenchmarkSuite):
    log.info("\n═══ 7. Dream Cycle ═══")

    sys.path.insert(0, str(PROJECT_ROOT / "core" / "scripts"))
    from dream_cycle_daemon import get_dream_status, run_consolidation

    def get_status():
        get_dream_status()

    suite.run("dream_status", get_status, iterations=20)

    def consolidation():
        run_consolidation()

    suite.run("dream_consolidation", consolidation, iterations=5)


def bench_polyglot_comparison(suite: BenchmarkSuite):
    """Compare Rust, Zig, and Python performance on identical operations."""
    log.info("\n═══ 8. Polyglot Comparison ═══")

    import math
    import random

    # Pure Python baseline
    def py_cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na * nb > 0 else 0.0

    a = [random.random() for _ in range(384)]
    b = [random.random() for _ in range(384)]

    suite.run("python_cosine_384d", lambda: py_cosine(a, b), iterations=50)

    # Rust cosine
    try:
        import whitemagic_rs

        suite.run(
            "rust_cosine_384d",
            lambda: whitemagic_rs.rust_cosine_similarity(a, b),
            iterations=50,
        )
    except ImportError:
        log.info("  Rust not available, skipping")

    # Zig SIMD cosine (with numpy zero-copy)
    try:
        import numpy as np
        from whitemagic.core.acceleration.simd_cosine import (
            cosine_similarity as zig_cosine,
        )

        a_np = np.array(a, dtype=np.float32)
        b_np = np.array(b, dtype=np.float32)
        suite.run(
            "zig_cosine_384d_numpy", lambda: zig_cosine(a_np, b_np), iterations=50
        )
    except ImportError:
        log.info("  Zig not available, skipping")

    # Zig batch cosine (numpy zero-copy)
    try:
        import numpy as np
        from whitemagic.core.acceleration.simd_cosine import batch_cosine as zig_batch

        query_np = np.random.rand(384).astype(np.float32)
        vectors_np = np.random.rand(100, 384).astype(np.float32)
        suite.run(
            "zig_batch_cosine_100x384d",
            lambda: zig_batch(query_np, vectors_np),
            iterations=10,
        )
    except ImportError:
        log.info("  Zig batch not available, skipping")

    # Zig top-K cosine (avoids full score array transfer)
    try:
        import numpy as np
        from whitemagic.core.acceleration.simd_cosine import top_k_cosine as zig_topk

        query_np = np.random.rand(384).astype(np.float32)
        vectors_np = np.random.rand(1000, 384).astype(np.float32)
        suite.run(
            "zig_topk_cosine_1000x384d_k10",
            lambda: zig_topk(query_np, vectors_np, k=10),
            iterations=10,
        )
    except ImportError:
        log.info("  Zig top-K not available, skipping")

    # Rust galactic batch score
    try:
        import whitemagic_rs
        import json

        coords = [[random.random() for _ in range(5)] for _ in range(100)]
        coords_json = json.dumps(coords)
        suite.run(
            "rust_galactic_batch_100",
            lambda: whitemagic_rs.galactic_batch_score_quick(coords_json),
            iterations=20,
        )
    except ImportError:
        pass

    # Rust grid cluster
    try:
        import whitemagic_rs

        coords = [[random.random() for _ in range(5)] for _ in range(100)]
        suite.run(
            "rust_grid_cluster_100",
            lambda: whitemagic_rs.grid_cluster(coords, 2),
            iterations=10,
        )
    except ImportError:
        pass

    # Haskell hexagram creation (I Ching)
    try:
        from whitemagic.core.acceleration.haskell_bridge import hs_create_hexagram

        lines = [1, 0, 1, 0, 1, 0]
        suite.run(
            "haskell_hexagram_create", lambda: hs_create_hexagram(lines), iterations=50
        )
    except ImportError:
        log.info("  Haskell not available, skipping")

    # Haskell batch hexagram creation
    try:
        from whitemagic.core.acceleration.haskell_bridge import (
            hs_create_hexagrams_batch,
        )

        batch_lines = [[random.randint(0, 1) for _ in range(6)] for _ in range(50)]
        suite.run(
            "haskell_hexagram_batch_50",
            lambda: hs_create_hexagrams_batch(batch_lines),
            iterations=10,
        )
    except ImportError:
        log.info("  Haskell batch not available, skipping")

    # Rust batch cosine (sequential, SIMD)
    try:
        from whitemagic.core.acceleration.parallel_rust import batch_cosine_rust

        pairs = [
            (
                [random.random() for _ in range(384)],
                [random.random() for _ in range(384)],
            )
            for _ in range(100)
        ]
        suite.run(
            "rust_batch_cosine_100", lambda: batch_cosine_rust(pairs), iterations=10
        )
    except ImportError:
        log.info("  Rust batch cosine not available, skipping")

    # NumPy batch cosine (vectorized)
    try:
        from whitemagic.core.acceleration.parallel_rust import batch_cosine_numpy

        pairs = [
            (
                [random.random() for _ in range(384)],
                [random.random() for _ in range(384)],
            )
            for _ in range(100)
        ]
        suite.run(
            "numpy_batch_cosine_100", lambda: batch_cosine_numpy(pairs), iterations=10
        )
    except ImportError:
        log.info("  NumPy batch cosine not available, skipping")

    # HNSW index search (Zig)
    try:
        import numpy as np
        from whitemagic.core.acceleration.hnsw_zig import HnswIndex

        hnsw = HnswIndex(
            dim=384, m=16, ef_construction=200, ef_search=50, max_elements=1000
        )
        for _ in range(500):
            hnsw.add(np.random.rand(384).astype(np.float32))
        query = np.random.rand(384).astype(np.float32)
        suite.run(
            "hnsw_search_500_k10", lambda: hnsw.search(query, k=10), iterations=10
        )
    except ImportError:
        log.info("  HNSW not available, skipping")


# Fragment (Rust) Benchmarks


def bench_fragment(suite: BenchmarkSuite):
    """Benchmark Fragment codebase search — PyO3, HTTP, subprocess layers."""
    log.info("Fragment (Rust) Benchmarks:")

    repo_path = str(PROJECT_ROOT.parent)

    # Fragment status (layer detection)
    try:
        from whitemagic.tools.handlers.fragment import handle_fragment_status

        suite.run(
            "fragment_status",
            lambda: handle_fragment_status(path=repo_path),
            iterations=20,
        )
    except Exception:
        log.info("  Fragment status not available, skipping")

    # Fragment search via PyO3 (cold cache — includes index load)
    try:
        from whitemagic.tools.handlers.fragment import handle_fragment_search

        suite.run(
            "fragment_search_cold",
            lambda: handle_fragment_search(
                query="how does homeostasis work", path=repo_path, top=5
            ),
            iterations=10,
        )
    except Exception:
        log.info("  Fragment search not available, skipping")

    # Fragment search — warm cache (prime once, measure steady-state)
    try:
        from whitemagic.tools.handlers.fragment import handle_fragment_search

        # Prime the index cache
        handle_fragment_search(query="priming query", path=repo_path, top=1)
        suite.run(
            "fragment_search_warm",
            lambda: handle_fragment_search(
                query="how does homeostasis work", path=repo_path, top=5
            ),
            iterations=20,
        )
    except Exception:
        log.info("  Fragment warm-cache search not available, skipping")

    # Fragment search — warm cache, larger top
    try:
        from whitemagic.tools.handlers.fragment import handle_fragment_search

        suite.run(
            "fragment_search_warm_top20",
            lambda: handle_fragment_search(
                query="kaizen engine analysis", path=repo_path, top=20
            ),
            iterations=20,
        )
    except Exception:
        log.info("  Fragment warm-cache top20 not available, skipping")

    # Python vector search comparison
    try:
        from whitemagic.core.memory.vector_search import get_vector_search

        vs = get_vector_search()
        suite.run(
            "python_vector_search",
            lambda: vs.search("how does homeostasis work", limit=5),
            iterations=10,
        )
    except Exception:
        log.info("  Python vector search not available, skipping")


# STRATA Benchmarks


def bench_strata(suite: BenchmarkSuite):
    """Benchmark STRATA codebase static analysis."""
    log.info("STRATA Benchmarks:")

    repo_path = str(PROJECT_ROOT.parent)

    # STRATA list_checks
    try:
        from whitemagic.tools.handlers.strata import handle_strata_list_checks

        suite.run(
            "strata_list_checks", lambda: handle_strata_list_checks(), iterations=20
        )
    except Exception:
        log.info("  STRATA list_checks not available, skipping")

    # STRATA analyze (incremental, sequential — parallel is slower due to GIL)
    try:
        from whitemagic.tools.handlers.strata import handle_strata_analyze

        suite.run(
            "strata_analyze_sequential",
            lambda: handle_strata_analyze(
                path=repo_path, incremental=True, parallel=False
            ),
            iterations=3,
            warmup=1,
        )
    except Exception:
        log.info("  STRATA analyze not available, skipping")

    # STRATA survey
    try:
        from whitemagic.tools.handlers.strata import handle_strata_survey

        suite.run(
            "strata_survey",
            lambda: handle_strata_survey(path=repo_path),
            iterations=5,
            warmup=1,
        )
    except Exception:
        log.info("  STRATA survey not available, skipping")


# Physical Metrics Benchmarks


def bench_physical_metrics(suite: BenchmarkSuite):
    """Benchmark physical metrics fetching and Prometheus export."""
    log.info("Physical Metrics Benchmarks:")

    # Physical metrics fetch (graceful degradation when laptop-optimizer absent)
    try:
        from whitemagic.harmony.physical_metrics import get_physical_metrics_source

        source = get_physical_metrics_source()
        suite.run("physical_metrics_fetch", lambda: source.get_metrics(), iterations=50)
    except Exception:
        log.info("  Physical metrics not available, skipping")

    # Adaptive targets computation
    try:
        from whitemagic.harmony.physical_metrics import (
            AdaptiveTargets,
            PowerContext,
            TimeContext,
            LoadContext,
        )

        targets = AdaptiveTargets()
        suite.run(
            "adaptive_targets_compute",
            lambda: targets.adapt(PowerContext.AC, TimeContext.DAY, LoadContext.IDLE),
            iterations=100,
        )
    except Exception:
        log.info("  Adaptive targets not available, skipping")

    # Thermal anomaly detection
    try:
        from whitemagic.harmony.physical_metrics import ThermalAnomalyDetector

        detector = ThermalAnomalyDetector()
        suite.run("thermal_anomaly_check", lambda: detector.check(55.0), iterations=100)
    except Exception:
        log.info("  Thermal anomaly detector not available, skipping")

    # Prometheus export
    try:
        from whitemagic.harmony.metrics_exporter import get_metrics_exporter

        exporter = get_metrics_exporter()
        suite.run("prometheus_export", lambda: exporter.export(), iterations=20)
    except Exception:
        log.info("  Prometheus exporter not available, skipping")

    # Homeostatic loop check (includes physical)
    try:
        from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop

        loop = get_homeostatic_loop()
        suite.run(
            "homeostatic_check_with_physical", lambda: loop.check(), iterations=10
        )
    except Exception:
        log.info("  Homeostatic loop not available, skipping")


# DNA & Zodiac Benchmarks


def bench_dna_zodiac(suite: BenchmarkSuite):
    """Benchmark DNA validation and Zodiac activation tools."""
    log.info("DNA & Zodiac Benchmarks:")

    # DNA principles listing
    try:
        from whitemagic.tools.handlers.misc import handle_dna_principles

        suite.run("dna_principles", lambda: handle_dna_principles(), iterations=100)
    except Exception:
        log.info("  DNA principles not available, skipping")

    # DNA validate (safe fix)
    try:
        from whitemagic.tools.handlers.misc import handle_dna_validate

        suite.run(
            "dna_validate_safe",
            lambda: handle_dna_validate(
                fix_details={"action": "update version", "file": "docs/README.md"},
                threat_type="version_drift",
            ),
            iterations=100,
        )
    except Exception:
        log.info("  DNA validate not available, skipping")

    # DNA validate (critical violation)
    try:
        from whitemagic.tools.handlers.misc import handle_dna_validate

        suite.run(
            "dna_validate_critical",
            lambda: handle_dna_validate(
                fix_details={
                    "action": "delete core system",
                    "file": "whitemagic/core/__init__.py",
                },
                threat_type="code_anomaly",
            ),
            iterations=100,
        )
    except Exception:
        log.info("  DNA validate critical not available, skipping")

    # Zodiac activate Aries
    try:
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_activate

        suite.run(
            "zodiac_activate_aries",
            lambda: handle_zodiac_activate(
                core="aries",
                context={
                    "operation": "benchmark",
                    "intention": "action",
                    "urgency": "normal",
                },
            ),
            iterations=50,
        )
    except Exception:
        log.info("  Zodiac activate not available, skipping")

    # Zodiac council convene
    try:
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_council

        suite.run(
            "zodiac_council",
            lambda: handle_zodiac_council(
                decision="Should we optimize the memory system?"
            ),
            iterations=20,
        )
    except Exception:
        log.info("  Zodiac council not available, skipping")

    # Zodiac stats
    try:
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_stats

        suite.run("zodiac_stats", lambda: handle_zodiac_stats(), iterations=50)
    except Exception:
        log.info("  Zodiac stats not available, skipping")

    # Garden health
    try:
        from whitemagic.tools.handlers.garden import handle_garden_health

        suite.run("garden_health", lambda: handle_garden_health(), iterations=50)
    except Exception:
        log.info("  Garden health not available, skipping")


# Main


def main():
    parser = argparse.ArgumentParser(description="WhiteMagic Benchmark Gauntlet")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    log.info("WhiteMagic Benchmark Gauntlet")
    log.info("DB: %s", DB_PATH)
    log.info(f"Time: {time.strftime('%H:%M:%S')}")

    suite = BenchmarkSuite()

    # Overall gauntlet progress bar (one tick per benchmark function group)
    gauntlet_phases = [
        ("Memory Pipeline", bench_memory_pipeline),
        ("Resonance Models", bench_resonance_models),
        ("Julia Ports", bench_julia_ports),
        ("Memory Stats", bench_memory_stats),
        ("Self-Model Forecast", bench_self_model_forecast),
        ("Database Queries", bench_db_queries),
        ("Dream Cycle", bench_dream_cycle),
        ("Polyglot Comparison", bench_polyglot_comparison),
        ("Fragment (Rust)", bench_fragment),
        ("STRATA", bench_strata),
        ("Physical Metrics", bench_physical_metrics),
        ("DNA & Zodiac", bench_dna_zodiac),
    ]
    suite.set_phase_progress(total=len(gauntlet_phases), label="Gauntlet")

    for phase_name, phase_fn in gauntlet_phases:
        suite.advance_phase(label=phase_name)
        phase_fn(suite)

    suite.finish_phase()

    summary = suite.summary()

    log.info(f"\n{'=' * 60}")
    log.info(f"BENCHMARK SUMMARY")
    log.info(f"{'=' * 60}")
    log.info("Total time: %ss", summary["total_time_seconds"])
    log.info(f"Benchmarks run: {len(summary['benchmarks'])}")

    # Group by category
    categories = {
        "Memory Pipeline": [
            "memory_store",
            "memory_search",
            "memory_recall",
            "memory_count",
        ],
        "Resonance Models": [
            "decay_prediction",
            "decay_curve",
            "pattern_detection_100",
            "constellation_merge_20",
            "garden_harmony_10",
        ],
        "Julia Ports": ["resonance_stats", "find_neighbors_100", "find_neighbors_500"],
        "Memory Stats": [
            "importance_distribution_1000",
            "zone_transitions_1000",
            "outlier_detection_1003",
        ],
        "Self-Model Forecast": [
            "forecast_100",
            "anomaly_detection_100",
            "correlation_5x50",
            "batch_forecast_5",
        ],
        "Database Queries": [
            "simple_select_100",
            "complex_join_100",
            "aggregation_gardens",
            "cached_aggregation_gardens",
            "association_query",
        ],
        "Dream Cycle": ["dream_status", "dream_consolidation"],
        "Polyglot Comparison": [
            "python_cosine_384d",
            "rust_cosine_384d",
            "zig_cosine_384d_numpy",
            "zig_batch_cosine_100x384d",
            "rust_galactic_batch_100",
            "rust_grid_cluster_100",
            "haskell_hexagram_create",
        ],
        "Fragment (Rust)": [
            "fragment_status",
            "fragment_search_cold",
            "fragment_search_warm",
            "fragment_search_warm_top20",
            "python_vector_search",
        ],
        "STRATA": ["strata_list_checks", "strata_analyze_sequential", "strata_survey"],
        "Physical Metrics": [
            "physical_metrics_fetch",
            "adaptive_targets_compute",
            "thermal_anomaly_check",
            "prometheus_export",
            "homeostatic_check_with_physical",
        ],
        "DNA & Zodiac": [
            "dna_principles",
            "dna_validate_safe",
            "dna_validate_critical",
            "zodiac_activate_aries",
            "zodiac_council",
            "zodiac_stats",
            "garden_health",
        ],
    }

    for category, benchmarks in categories.items():
        log.info("\n%s:", category)
        for name in benchmarks:
            if name in summary["benchmarks"]:
                stats = summary["benchmarks"][name]
                log.info(
                    "  %s mean=%sms  median=%sms  p95=%sms",
                    name,
                    stats["mean_ms"],
                    stats["median_ms"],
                    stats["p95_ms"],
                )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2))
        log.info("\nResults saved to %s", output_path)
    else:
        # Default location
        default_output = PROJECT_ROOT / "reports" / "benchmark_gauntlet.json"
        default_output.parent.mkdir(parents=True, exist_ok=True)
        default_output.write_text(json.dumps(summary, indent=2))
        log.info("\nResults saved to %s", default_output)


if __name__ == "__main__":
    main()
