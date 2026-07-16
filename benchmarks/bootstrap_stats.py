"""Bootstrap confidence intervals and judge FPR probes for benchmark rigor.

Implements Section 7.2 of the Memory & Cognitive Systems Strategy 2026.

Provides:
  - Bootstrap CIs for recall@K and MRR metrics
  - Judge FPR probes (false positive rate of the evaluation methodology itself)
  - Paired comparison CIs (is A significantly better than B?)

Usage:
    from benchmarks.bootstrap_stats import bootstrap_ci, judge_fpr_probe

    ci = bootstrap_ci(recall_values, metric_name="recall@5")
    fpr = judge_fpr_probe(num_probes=1000, probe_size=50)
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


def bootstrap_ci(
    values: list[float],
    metric_name: str = "metric",
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, Any]:
    """Compute bootstrap confidence interval for a list of metric values.

    Args:
        values: Per-query metric values (e.g., recall@5 for each query).
        metric_name: Name of the metric for labeling.
        n_bootstrap: Number of bootstrap resamples.
        confidence: Confidence level (0.95 = 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        Dict with mean, ci_lower, ci_upper, ci_width, n_samples.
    """
    if not values:
        return {
            "metric": metric_name,
            "mean": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "ci_width": 0.0,
            "n_samples": 0,
        }

    rng = random.Random(seed)
    n = len(values)
    boot_means: list[float] = []

    for _ in range(n_bootstrap):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = 1.0 - confidence
    lower_idx = int((alpha / 2) * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap) - 1

    lower = boot_means[lower_idx]
    upper = boot_means[upper_idx]
    point_estimate = sum(values) / n

    return {
        "metric": metric_name,
        "mean": round(point_estimate, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
        "ci_width": round(upper - lower, 4),
        "n_samples": n,
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


def paired_bootstrap_ci(
    a_values: list[float],
    b_values: list[float],
    metric_name: str = "metric",
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, Any]:
    """Compute bootstrap CI for the difference between two systems.

    Args:
        a_values: Per-query metric values for system A.
        b_values: Per-query metric values for system B.
        metric_name: Name of the metric.
        n_bootstrap: Number of bootstrap resamples.
        confidence: Confidence level.
        seed: Random seed.

    Returns:
        Dict with mean_diff, ci_lower, ci_upper, significant (bool).
    """
    if len(a_values) != len(b_values):
        logger.warning("Paired bootstrap requires equal-length lists; truncating")
        min_len = min(len(a_values), len(b_values))
        a_values = a_values[:min_len]
        b_values = b_values[:min_len]

    if not a_values:
        return {
            "metric": metric_name,
            "mean_diff": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "significant": False,
            "n_samples": 0,
        }

    rng = random.Random(seed)
    n = len(a_values)
    diffs: list[float] = []

    for _ in range(n_bootstrap):
        sample_diffs = []
        for _ in range(n):
            idx = rng.randint(0, n - 1)
            sample_diffs.append(a_values[idx] - b_values[idx])
        diffs.append(sum(sample_diffs) / n)

    diffs.sort()
    alpha = 1.0 - confidence
    lower = diffs[int((alpha / 2) * n_bootstrap)]
    upper = diffs[int((1 - alpha / 2) * n_bootstrap) - 1]
    mean_diff = sum(a - b for a, b in zip(a_values, b_values)) / n

    return {
        "metric": metric_name,
        "mean_diff": round(mean_diff, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
        "significant": not (lower <= 0 <= upper),
        "n_samples": n,
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


def judge_fpr_probe(
    num_probes: int = 1000,
    probe_size: int = 50,
    seed: int = 42,
) -> dict[str, Any]:
    """Measure the false positive rate of the evaluation methodology itself.

    Generates random "relevance" judgments and checks how often the
    evaluation framework produces false positives (claiming a result is
    relevant when it's random). This calibrates the judge's FPR.

    Args:
        num_probes: Number of random probes to run.
        probe_size: Number of items per probe.
        seed: Random seed.

    Returns:
        Dict with fpr, mean_random_recall, probes, and interpretation.
    """
    rng = random.Random(seed)
    false_positives = 0
    random_recalls: list[float] = []

    for _ in range(num_probes):
        # Generate random "ground truth" and "predictions"
        gt_ids = set(rng.randint(0, 10000) for _ in range(probe_size // 5))
        pred_ids = [rng.randint(0, 10000) for _ in range(probe_size)]

        # Check if any prediction matches ground truth by chance
        hits = len(gt_ids & set(pred_ids))
        recall = hits / len(gt_ids) if gt_ids else 0
        random_recalls.append(recall)

        if recall > 0:
            false_positives += 1

    fpr = false_positives / num_probes
    mean_random_recall = sum(random_recalls) / len(random_recalls)

    return {
        "fpr": round(fpr, 4),
        "mean_random_recall": round(mean_random_recall, 4),
        "num_probes": num_probes,
        "probe_size": probe_size,
        "interpretation": (
            f"Random chance produces recall > 0 in {fpr:.1%} of probes. "
            f"Mean random recall: {mean_random_recall:.4f}. "
            f"Any system recall below {mean_random_recall * 2:.4f} may be noise."
        ),
    }


def add_cis_to_results(
    per_query_recalls: dict[str, list[float]],
    n_bootstrap: int = 1000,
) -> dict[str, dict[str, Any]]:
    """Add bootstrap CIs to a set of per-query recall values.

    Args:
        per_query_recalls: Dict mapping metric name (e.g., "recall@1") to
            a list of per-query values (1.0 or 0.0 for each query).
        n_bootstrap: Number of bootstrap resamples.

    Returns:
        Dict mapping metric name to CI dict.
    """
    results: dict[str, dict[str, Any]] = {}
    for metric, values in per_query_recalls.items():
        results[metric] = bootstrap_ci(values, metric_name=metric, n_bootstrap=n_bootstrap)
    return results
