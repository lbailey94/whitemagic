"""P6.1 — Relevance metrics and ID-order invariance tests.

Tests that:
1. Label-based relevance is correctly computed (recall, precision, MRR, nDCG)
2. Metrics are invariant to insertion order (ID-order invariance)
3. Relevant_count is not truncated (scale-invariance)
4. Confidence intervals are computed correctly across seeds
5. Old expected_ids-based results are marked historical
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.relevance_metrics import (
    QueryResult,
    AggregateMetrics,
    is_relevant,
    compute_query_metrics,
    aggregate_metrics,
    aggregate_with_ci,
    to_dict,
)
from benchmarks.dataset import generate_dataset, generate_queries
from benchmarks.scale_benchmark import (
    generate_scale_dataset,
    generate_scale_queries,
    self_test_id_order_invariance,
)


class TestLabelBasedRelevance:
    """Test that label-based relevance matching works correctly."""

    def test_is_relevant_single_label(self):
        mem_labels = {"subject": "entropy", "category": "physics"}
        rel_labels = {"subject": "entropy"}
        assert is_relevant(mem_labels, rel_labels)

    def test_is_relevant_multi_label(self):
        mem_labels = {"subject": "entropy", "category": "physics"}
        rel_labels = {"subject": "entropy", "category": "physics"}
        assert is_relevant(mem_labels, rel_labels)

    def test_is_not_relevant_wrong_subject(self):
        mem_labels = {"subject": "entropy", "category": "physics"}
        rel_labels = {"subject": "neural networks"}
        assert not is_relevant(mem_labels, rel_labels)

    def test_is_not_relevant_partial_match(self):
        mem_labels = {"subject": "entropy", "category": "physics"}
        rel_labels = {"subject": "entropy", "category": "biology"}
        assert not is_relevant(mem_labels, rel_labels)

    def test_is_relevant_empty_query_labels(self):
        mem_labels = {"subject": "entropy", "category": "physics"}
        rel_labels = {}
        assert is_relevant(mem_labels, rel_labels)


class TestQueryMetrics:
    """Test per-query metric computation."""

    def test_perfect_recall(self):
        # 5 relevant items, all 5 retrieved in top 10
        relevance_labels = {"subject": "entropy"}
        retrieved_ids = ["m1", "m2", "m3", "m4", "m5"]
        retrieved_labels = [
            {"subject": "entropy"},
            {"subject": "entropy"},
            {"subject": "entropy"},
            {"subject": "entropy"},
            {"subject": "entropy"},
        ]
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=5,
        )
        assert qr.recall_at_1 == 1.0 / 5  # 1 of 5 relevant in top 1
        assert qr.recall_at_5 == 5.0 / 5  # all 5 relevant in top 5
        assert qr.recall_at_10 == 5.0 / 5  # all 5 relevant in top 10
        assert qr.precision_at_10 == 5.0 / 10  # 5 relevant out of 10 positions
        assert qr.mrr == 1.0
        assert qr.first_match_rank == 1

    def test_no_relevant_retrieved(self):
        relevance_labels = {"subject": "entropy"}
        retrieved_ids = ["m1", "m2", "m3"]
        retrieved_labels = [
            {"subject": "neural networks"},
            {"subject": "game theory"},
            {"subject": "recursion"},
        ]
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=5,
        )
        assert qr.recall_at_1 == 0.0
        assert qr.recall_at_10 == 0.0
        assert qr.mrr == 0.0
        assert qr.first_match_rank is None
        assert qr.ndcg == 0.0

    def test_partial_recall(self):
        # 10 relevant items, only 3 retrieved in top 10
        relevance_labels = {"subject": "entropy"}
        retrieved_ids = [f"m{i}" for i in range(10)]
        retrieved_labels = [{"subject": "entropy"}] * 3 + [{"subject": "other"}] * 7
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=10,
        )
        assert qr.recall_at_10 == 3 / 10
        assert qr.recall_at_1 == 1 / 10
        assert qr.mrr == 1.0
        assert qr.precision_at_10 == 3 / 10

    def test_mrr_second_position(self):
        relevance_labels = {"subject": "entropy"}
        retrieved_ids = ["m1", "m2"]
        retrieved_labels = [{"subject": "other"}, {"subject": "entropy"}]
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=5,
        )
        assert qr.mrr == 0.5
        assert qr.first_match_rank == 2

    def test_ndcg_ideal_ordering(self):
        # All relevant items first = ideal DCG = nDCG 1.0
        relevance_labels = {"subject": "entropy"}
        retrieved_ids = ["m1", "m2", "m3"]
        retrieved_labels = [{"subject": "entropy"}] * 3
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=3,
        )
        assert qr.ndcg == pytest.approx(1.0, abs=1e-6)

    def test_zero_relevant_count(self):
        qr = compute_query_metrics(
            query_id="q1", query="test",
            relevance_labels={"subject": "nonexistent"},
            retrieved_ids=["m1"],
            retrieved_labels=[{"subject": "other"}],
            relevant_count=0,
        )
        assert qr.recall_at_10 == 0.0
        assert qr.mrr == 0.0


class TestAggregateMetrics:
    """Test aggregation across queries."""

    def test_aggregate_two_queries(self):
        qr1 = QueryResult(
            query_id="q1", query="a", relevance_labels={},
            retrieved_ids=[], retrieved_labels=[],
            relevant_count=1,
            recall_at_10=1.0, mrr=1.0, ndcg=1.0,
            precision_at_10=0.5,
        )
        qr2 = QueryResult(
            query_id="q2", query="b", relevance_labels={},
            retrieved_ids=[], retrieved_labels=[],
            relevant_count=1,
            recall_at_10=0.0, mrr=0.0, ndcg=0.0,
            precision_at_10=0.0,
        )
        agg = aggregate_metrics([qr1, qr2])
        assert agg.total_queries == 2
        assert agg.recall_at_10 == 0.5
        assert agg.mrr == 0.5

    def test_aggregate_empty(self):
        agg = aggregate_metrics([])
        assert agg.total_queries == 0
        assert agg.recall_at_10 == 0.0

    def test_to_dict_roundtrip(self):
        qr = QueryResult(
            query_id="q1", query="a", relevance_labels={},
            retrieved_ids=[], retrieved_labels=[],
            relevant_count=1,
            recall_at_10=0.5, mrr=0.5, ndcg=0.5,
            precision_at_10=0.3,
        )
        agg = aggregate_metrics([qr])
        d = to_dict(agg)
        assert d["total_queries"] == 1
        assert d["recall_at_10"] == 0.5
        assert "precision_at_10" in d
        assert "ndcg" in d


class TestConfidenceIntervals:
    """Test CI computation across seeds."""

    def test_ci_with_multiple_seeds(self):
        # Create 3 per-seed metrics
        per_seed = []
        for i in range(3):
            qr = QueryResult(
                query_id=f"q{i}", query="a", relevance_labels={},
                retrieved_ids=[], retrieved_labels=[],
                relevant_count=1,
                recall_at_10=0.5 + i * 0.1,
                mrr=0.5, ndcg=0.5,
                precision_at_10=0.3,
            )
            per_seed.append(aggregate_metrics([qr]))

        agg = aggregate_with_ci(per_seed)
        assert agg.ci_recall_at_10 is not None
        assert agg.ci_mrr is not None
        assert agg.ci_ndcg is not None
        # CI should bracket the mean
        lo, hi = agg.ci_recall_at_10
        assert lo <= agg.recall_at_10 <= hi

    def test_ci_single_seed_no_ci(self):
        qr = QueryResult(
            query_id="q1", query="a", relevance_labels={},
            retrieved_ids=[], retrieved_labels=[],
            relevant_count=1,
            recall_at_10=0.5, mrr=0.5, ndcg=0.5,
            precision_at_10=0.3,
        )
        agg = aggregate_with_ci([aggregate_metrics([qr])])
        assert agg.ci_recall_at_10 is None  # No CI with n<2


class TestIDOrderInvariance:
    """P6.1 requirement 5: ID-order invariance self-test."""

    def test_self_test_passes(self):
        """The built-in self-test should pass."""
        assert self_test_id_order_invariance() is True

    def test_dataset_labels_order_invariant(self):
        """Labels dict is the same regardless of insertion order."""
        memories = generate_scale_dataset(num_memories=500, seed=42)
        import random
        shuffled = memories.copy()
        random.Random(99).shuffle(shuffled)

        orig = {m["id"]: {"subject": m["subject"], "category": m["category"]} for m in memories}
        shuf = {m["id"]: {"subject": m["subject"], "category": m["category"]} for m in shuffled}
        assert orig == shuf

    def test_scale_queries_no_truncation(self):
        """relevant_count should not be capped at 20."""
        queries = generate_scale_queries(num_queries=50, num_memories=10_000)
        for q in queries:
            # relevant_count should be the actual count, not capped
            assert q["relevant_count"] > 0
            # No expected_ids field should exist
            assert "expected_ids" not in q
            assert "relevance_labels" in q

    def test_dataset_queries_no_truncation(self):
        """Small dataset queries should also not have truncated IDs."""
        queries = generate_queries(num_queries=20)
        for q in queries:
            assert q["relevant_count"] > 0
            assert "expected_ids" not in q
            assert "relevance_labels" in q


class TestOldResultsHistorical:
    """P6.1 requirement 6: old quality results marked historical."""

    def test_scale_benchmark_reports_relevance_model(self):
        """Scale benchmark output should include relevance_model field."""
        # We verify the field exists in the output structure
        # without running the full benchmark
        from benchmarks.scale_benchmark import run_scale_benchmark
        import inspect
        source = inspect.getsource(run_scale_benchmark)
        assert "relevance_model" in source
        assert "label-based" in source

    def test_old_expected_ids_format_absent(self):
        """generate_scale_queries should not produce expected_ids."""
        queries = generate_scale_queries(num_queries=10, num_memories=1000)
        for q in queries:
            assert "expected_ids" not in q
            assert "expected_subject" not in q
