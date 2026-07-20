"""Phase 6 — Relevance metrics for benchmark quality evaluation.

Provides label-based relevance (not truncated ID lists), computing
recall@K, precision@K, MRR, nDCG, and confidence intervals across seeds.

Key design: relevance is determined by matching semantic labels
(subject, category) between query and retrieved memories, not by
membership in a pre-truncated ID set.  This makes metrics scale-invariant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryResult:
    """Metrics for a single query."""

    query_id: str
    query: str
    relevance_labels: dict[str, str]
    retrieved_ids: list[str]
    retrieved_labels: list[dict[str, str]]
    relevant_count: int
    recall_at_1: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    latency_ms: float = 0.0
    first_match_rank: int | None = None


@dataclass
class AggregateMetrics:
    """Aggregated metrics across all queries."""

    total_queries: int = 0
    recall_at_1: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    per_query: list[QueryResult] = field(default_factory=list)

    # Confidence intervals (populated by aggregate_with_ci)
    ci_recall_at_10: tuple[float, float] | None = None
    ci_mrr: tuple[float, float] | None = None
    ci_ndcg: tuple[float, float] | None = None


def is_relevant(
    memory_labels: dict[str, str],
    relevance_labels: dict[str, str],
) -> bool:
    """Check if a memory is relevant given query relevance labels.

    A memory is relevant if it matches ALL specified label dimensions.
    e.g. {"subject": "entropy"} matches any memory with subject="entropy".
    {"subject": "entropy", "category": "physics"} requires both.
    """
    for key, value in relevance_labels.items():
        if memory_labels.get(key) != value:
            return False
    return True


def compute_query_metrics(
    query_id: str,
    query: str,
    relevance_labels: dict[str, str],
    retrieved_ids: list[str],
    retrieved_labels: list[dict[str, str]],
    relevant_count: int,
    latency_ms: float = 0.0,
) -> QueryResult:
    """Compute per-query metrics.

    Args:
        query_id: Query identifier.
        query: Query text.
        relevance_labels: Labels that define relevance (e.g. {"subject": "entropy"}).
        retrieved_ids: Ordered list of retrieved memory IDs.
        retrieved_labels: Parallel list of label dicts for each retrieved memory.
        relevant_count: Total number of relevant memories in the dataset.
        latency_ms: Query latency in milliseconds.

    Returns:
        QueryResult with all metrics computed.
    """
    if relevant_count == 0:
        return QueryResult(
            query_id=query_id,
            query=query,
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=0,
            latency_ms=latency_ms,
        )

    # Build relevance vector: 1.0 if relevant, 0.0 if not
    rel_vector = [
        1.0 if is_relevant(labels, relevance_labels) else 0.0
        for labels in retrieved_labels
    ]

    # Recall@K: fraction of relevant items found in top K
    def recall_at(k: int) -> float:
        top_k = rel_vector[:k]
        hits = sum(top_k)
        return hits / relevant_count

    # Precision@K: fraction of top K that are relevant
    def precision_at(k: int) -> float:
        top_k = rel_vector[:k]
        return sum(top_k) / k if k > 0 else 0.0

    # MRR: 1/rank of first relevant result
    mrr = 0.0
    first_match_rank = None
    for rank, rel in enumerate(rel_vector, 1):
        if rel > 0:
            mrr = 1.0 / rank
            first_match_rank = rank
            break

    # nDCG: normalized discounted cumulative gain
    dcg = 0.0
    for rank, rel in enumerate(rel_vector, 1):
        if rel > 0:
            dcg += 1.0 / math.log2(rank + 1)
    # IDCG: ideal DCG (all relevant items at top)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(rel_vector), relevant_count) + 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return QueryResult(
        query_id=query_id,
        query=query,
        relevance_labels=relevance_labels,
        retrieved_ids=retrieved_ids,
        retrieved_labels=retrieved_labels,
        relevant_count=relevant_count,
        recall_at_1=recall_at(1),
        recall_at_5=recall_at(5),
        recall_at_10=recall_at(10),
        precision_at_1=precision_at(1),
        precision_at_5=precision_at(5),
        precision_at_10=precision_at(10),
        mrr=mrr,
        ndcg=ndcg,
        latency_ms=latency_ms,
        first_match_rank=first_match_rank,
    )


def aggregate_metrics(results: list[QueryResult]) -> AggregateMetrics:
    """Aggregate per-query metrics into summary statistics."""
    n = len(results)
    if n == 0:
        return AggregateMetrics()

    return AggregateMetrics(
        total_queries=n,
        recall_at_1=sum(r.recall_at_1 for r in results) / n,
        recall_at_5=sum(r.recall_at_5 for r in results) / n,
        recall_at_10=sum(r.recall_at_10 for r in results) / n,
        precision_at_1=sum(r.precision_at_1 for r in results) / n,
        precision_at_5=sum(r.precision_at_5 for r in results) / n,
        precision_at_10=sum(r.precision_at_10 for r in results) / n,
        mrr=sum(r.mrr for r in results) / n,
        ndcg=sum(r.ndcg for r in results) / n,
        per_query=results,
    )


def aggregate_with_ci(
    per_seed_metrics: list[AggregateMetrics],
) -> AggregateMetrics:
    """Aggregate across seeds with confidence intervals.

    Args:
        per_seed_metrics: One AggregateMetrics per seed.

    Returns:
        AggregateMetrics with mean values and confidence intervals
        (mean ± 1.96 * std / sqrt(n) for 95% CI).
    """
    if not per_seed_metrics:
        return AggregateMetrics()

    n = len(per_seed_metrics)
    agg = aggregate_metrics(
        [qr for am in per_seed_metrics for qr in am.per_query]
    )

    if n < 2:
        return agg

    def ci(values: list[float]) -> tuple[float, float]:
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = math.sqrt(variance)
        margin = 1.96 * std / math.sqrt(n)
        return (mean - margin, mean + margin)

    r10_values = [am.recall_at_10 for am in per_seed_metrics]
    mrr_values = [am.mrr for am in per_seed_metrics]
    ndcg_values = [am.ndcg for am in per_seed_metrics]

    agg.ci_recall_at_10 = ci(r10_values)
    agg.ci_mrr = ci(mrr_values)
    agg.ci_ndcg = ci(ndcg_values)

    return agg


def to_dict(agg: AggregateMetrics) -> dict[str, Any]:
    """Serialize AggregateMetrics to a JSON-friendly dict."""
    d: dict[str, Any] = {
        "total_queries": agg.total_queries,
        "recall_at_1": round(agg.recall_at_1, 6),
        "recall_at_5": round(agg.recall_at_5, 6),
        "recall_at_10": round(agg.recall_at_10, 6),
        "precision_at_1": round(agg.precision_at_1, 6),
        "precision_at_5": round(agg.precision_at_5, 6),
        "precision_at_10": round(agg.precision_at_10, 6),
        "mrr": round(agg.mrr, 6),
        "ndcg": round(agg.ndcg, 6),
    }
    if agg.ci_recall_at_10 is not None:
        d["ci_recall_at_10"] = [round(agg.ci_recall_at_10[0], 6), round(agg.ci_recall_at_10[1], 6)]
    if agg.ci_mrr is not None:
        d["ci_mrr"] = [round(agg.ci_mrr[0], 6), round(agg.ci_mrr[1], 6)]
    if agg.ci_ndcg is not None:
        d["ci_ndcg"] = [round(agg.ci_ndcg[0], 6), round(agg.ci_ndcg[1], 6)]
    return d
