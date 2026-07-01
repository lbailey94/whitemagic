"""Transition-Zone Prescience Framework (TZPF)

A multidimensional scoring system designed for forecasting in domains where:
- Base rates are unknown (no historical precedent)
- Outcomes are partially validated on a spectrum
- The forecaster may influence outcomes (hyperstition)
- Traditional binary calibration metrics break down

Metrics
-------
DFI  — Directional Foresight Index (civilizational impact weighted)
TAR  — Temporal Acceleration Ratio (predicted vs actual timeline)
HC   — Hyperstition Coefficient (self-fulfilling dynamics)
BCI  — Behavioral Calibration Index (stated vs behavioral confidence)
PVS  — Partial Validation Spectrum (0-1 continuum, not binary)
NRS  — Narrative Resonance Score (independent source convergence)
PI   — Positioning Index (actions taken / actions implied)

References
----------
- Brier (1950), Gneiting & Raftery (2007) — proper scoring rules
- Murphy (1973) — forecast decomposition
- Land (1995), CCRU — hyperstition theory
- Waghmare & Ziegel (2026) — CRPS and logarithmic score review
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# Default category impact weights for DFI
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_IMPACT_WEIGHTS: dict[str, float] = {
    "ai_governance": 4.5,  # Civilization-scale governance architecture
    "agent_architecture": 4.0,  # Foundational agent design patterns
    "ai_trends": 4.5,  # Macro civilizational direction
    "ai_hardware": 3.5,  # Infrastructure & compute
    "energy": 4.0,  # Energy is civilization substrate
    "geopolitics": 2.5,  # Political events (narrower scope)
    "general": 2.0,  # Default
}

# ═══════════════════════════════════════════════════════════════════════════
# Core TZPF Metric Functions
# ═══════════════════════════════════════════════════════════════════════════


def directional_foresight_index(
    claims: Sequence[dict[str, Any]],
    impact_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute DFI: points weighted by civilizational impact.

    DFI = sum(points_i * impact_weight_i)

    Args:
        claims: List of claim dicts with 'points' and 'category' keys.
        impact_weights: Override category weights. Defaults above.

    Returns:
        Dict with raw_points, weighted_dfi, and per-category breakdown.
    """
    weights = impact_weights or DEFAULT_IMPACT_WEIGHTS
    raw_total = 0.0
    weighted_total = 0.0
    by_category: dict[str, dict[str, float]] = {}

    for claim in claims:
        pts = float(claim.get("points") or 0)
        cat = claim.get("category", "general")
        w = weights.get(cat, weights.get("general", 2.0))

        raw_total += pts
        weighted_total += pts * w

        if cat not in by_category:
            by_category[cat] = {"claims": 0, "raw_points": 0.0, "weighted": 0.0}
        by_category[cat]["claims"] += 1
        by_category[cat]["raw_points"] += pts
        by_category[cat]["weighted"] += pts * w

    return {
        "raw_points": round(raw_total, 1),
        "dfi": round(weighted_total, 1),
        "dfi_per_claim": round(weighted_total / len(claims), 1) if claims else 0.0,
        "by_category": {
            k: {
                "claims": v["claims"],
                "raw_points": round(v["raw_points"], 1),
                "weighted": round(v["weighted"], 1),
            }
            for k, v in sorted(by_category.items(), key=lambda x: -x[1]["weighted"])
        },
    }


def temporal_acceleration_ratio(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute TAR: predicted timeline vs actual validation timeline.

    For each validated claim with explicit predicted_year in notes:
    TAR = predicted_year / actual_year

    A TAR > 1 means reality accelerated faster than the prediction.
    A TAR < 1 means the prediction was aggressive (validated early).
    TAR = 1 means perfect timeline calibration.

    Returns:
        Dict with mean_tar, median_tar, and per-claim breakdown.
    """
    import re

    ratios: list[float] = []
    breakdown: list[dict[str, Any]] = []

    for claim in claims:
        if claim.get("status") != "validated":
            continue
        notes = claim.get("notes", "")
        source_date = claim.get("source_date", "")
        validation_date = claim.get("validation_date", "")

        # Try to extract predicted window from notes
        pred_match = re.search(
            r"(?:predicted|predict|forecast|window)\s*(?:~)?\s*(\d{4})\s*(?:–|-)\s*(\d{4})",
            notes,
            re.IGNORECASE,
        )
        single_pred = re.search(
            r"(?:predicted|predict|forecast)\s*(?:~)?\s*(\d{4})",
            notes,
            re.IGNORECASE,
        )

        pred_year: float | None = None
        if pred_match:
            pred_year = (int(pred_match.group(1)) + int(pred_match.group(2))) / 2
        elif single_pred:
            pred_year = float(single_pred.group(1))
        else:
            # Fallback: if source_date is 2025 and notes mention "2028-2029"
            # or if validation_date is known and notes mention "too conservative"
            if "2028-2029" in notes or "2028" in notes and "predicted" in notes.lower():
                pred_year = 2028.5  # mid-point

        actual_year: float | None = None
        if validation_date:
            actual_year = float(validation_date[:4])
        elif source_date:
            actual_year = float(source_date[:4]) + 0.5  # crude fallback

        if pred_year and actual_year and pred_year > 0 and actual_year > 0:
            tar = pred_year / actual_year
            ratios.append(tar)
            breakdown.append(
                {
                    "claim": claim["claim"][:50],
                    "predicted_year": pred_year,
                    "actual_year": actual_year,
                    "tar": round(tar, 2),
                }
            )

    if not ratios:
        return {
            "mean_tar": None,
            "median_tar": None,
            "claims_scored": 0,
            "breakdown": [],
        }

    return {
        "mean_tar": round(sum(ratios) / len(ratios), 2),
        "median_tar": round(sorted(ratios)[len(ratios) // 2], 2),
        "claims_scored": len(ratios),
        "breakdown": breakdown,
    }


def hyperstition_coefficient(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute HC: evidence of self-fulfilling / participatory dynamics.

    Scored 0-1 per claim based on evidence in notes:
    0.0 — purely descriptive, no evidence of influence
    0.3 — terminology/ideas appeared in industry before validation
    0.5 — claims were cited or acknowledged by validators
    0.7 — active open-source or published work preceded validation
    1.0 — validation event explicitly credited the claimant

    Returns:
        Dict with mean_hc, distribution, and per-claim scores.
    """
    scores: list[float] = []
    breakdown: list[dict[str, Any]] = []

    for claim in claims:
        notes = claim.get("notes", "").lower()
        hc = 0.0

        # Explicit credit → 1.0
        if any(
            x in notes for x in ["credited", "ahead of the curve", "ahead", "predated"]
        ):
            hc = 1.0
        # Cited / acknowledged → 0.5-0.7
        elif any(
            x in notes
            for x in ["acknowledged", "resonant", "explicitly uses", "framing"]
        ):
            hc = 0.6
        # Terminology appeared in industry → 0.3-0.5
        elif any(
            x in notes for x in ["mainstream", "multiple independent", "converged"]
        ):
            hc = 0.4
        # Core concept presciently identified → 0.2-0.3
        elif "prescient" in notes or "ahead" in notes:
            hc = 0.3
        # Pure description → 0.0-0.1
        else:
            hc = 0.1

        # Boost for claims where the predictor *built* something
        source_ref = claim.get("source_ref", "").lower()
        if any(x in source_ref for x in ["whitemagic", "core/", "grimoire/", "codex"]):
            hc = min(hc + 0.2, 1.0)

        scores.append(hc)
        breakdown.append(
            {
                "claim": claim["claim"][:50],
                "hc": round(hc, 2),
            }
        )

    return {
        "mean_hc": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "median_hc": round(sorted(scores)[len(scores) // 2], 2) if scores else 0.0,
        "distribution": {
            "high (>0.5)": sum(1 for s in scores if s > 0.5),
            "medium (0.2-0.5)": sum(1 for s in scores if 0.2 <= s <= 0.5),
            "low (<0.2)": sum(1 for s in scores if s < 0.2),
        },
        "breakdown": breakdown,
    }


def behavioral_calibration_index(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute BCI: behavioral confidence vs stated confidence vs outcomes.

    BCI_stated  = mean(stated_confidence) - mean(outcome)
    BCI_behavioral = mean(behavioral_confidence) - mean(outcome)
    Shyness gap = BCI_stated - BCI_behavioral

    Returns:
        Dict with stated_gap, behavioral_gap, shyness_gap.
    """
    stated: list[float] = []
    behavioral: list[float] = []
    outcomes: list[int] = []

    for claim in claims:
        if claim.get("status") not in ("validated", "falsified"):
            continue
        sc = claim.get("confidence")
        bc = claim.get("behavioral_confidence")
        if sc is None:
            continue

        stated.append(float(sc))
        behavioral.append(float(bc) if bc is not None else float(sc))
        outcomes.append(1 if claim["status"] == "validated" else 0)

    if not stated:
        return {
            "stated_gap": None,
            "behavioral_gap": None,
            "shyness_gap": None,
            "mean_stated_confidence": None,
            "mean_behavioral_confidence": None,
            "mean_outcome": None,
        }

    mean_stated = sum(stated) / len(stated)
    mean_behavioral = sum(behavioral) / len(behavioral)
    mean_outcome = sum(outcomes) / len(outcomes)

    return {
        "stated_gap": round(mean_stated - mean_outcome, 3),
        "behavioral_gap": round(mean_behavioral - mean_outcome, 3),
        "shyness_gap": round(
            (mean_stated - mean_outcome) - (mean_behavioral - mean_outcome), 3
        ),
        "mean_stated_confidence": round(mean_stated, 3),
        "mean_behavioral_confidence": round(mean_behavioral, 3),
        "mean_outcome": round(mean_outcome, 3),
    }


def partial_validation_spectrum(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute PVS: partial validation spectrum scores (0-1 continuum).

    Scoring rules from notes:
    - "full validation" / "product shipping" → 1.0
    - "validated" with no qualifiers → 0.75
    - "partial validation" / "some layers" / "directionally" → 0.50
    - "early signals" / "trend confirmed" → 0.25
    - "pending" / no evidence → 0.0-0.10
    - "expired" / falsified → 0.0

    Returns:
        Dict with mean_pvs, per-claim scores.
    """
    scores: list[float] = []
    breakdown: list[dict[str, Any]] = []

    for claim in claims:
        status = claim.get("status", "")
        notes = claim.get("notes", "").lower()
        pvs = 0.0

        if status == "falsified":
            pvs = 0.0
        elif status == "expired":
            pvs = 0.0
        elif status == "pending":
            if "early" in notes or "signs" in notes:
                pvs = 0.15
            else:
                pvs = 0.05
        elif status == "validated":
            if (
                "full validation" in notes
                or "product shipping" in notes
                or "standard adopted" in notes
            ):
                pvs = 1.0
            elif (
                "partial validation" in notes
                or "some layers" in notes
                or "directionally" in notes
            ):
                if "photonic" in notes and "superconducting" in notes:
                    pvs = 0.30  # e.g. neurophotonic DC
                else:
                    pvs = 0.50
            elif "mainstream" in notes or "multiple independent" in notes:
                pvs = 0.75
            else:
                pvs = 0.75
        else:
            pvs = 0.0

        scores.append(pvs)
        breakdown.append(
            {
                "claim": claim["claim"][:50],
                "status": status,
                "pvs": round(pvs, 2),
            }
        )

    return {
        "mean_pvs": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "claims_scored": len(scores),
        "breakdown": breakdown,
    }


def narrative_resonance_score(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute NRS: count of independent validation sources per claim.

    Parses validation_ref for evidence of multiple independent sources.
    Rules:
    - 1 source → 1
    - 2-3 sources → 2-3
    - 4+ sources → 4+
    - "multiple" / "independent" / list of orgs → count them

    Returns:
        Dict with mean_nrs, max_nrs, per-claim counts.
    """
    import re

    counts: list[int] = []
    breakdown: list[dict[str, Any]] = []

    for claim in claims:
        ref = claim.get("validation_ref", "")
        status = claim.get("status", "")
        if status != "validated":
            continue

        # Count distinct orgs / papers in validation_ref
        orgs = set()
        # Common org patterns
        org_patterns = [
            r"Anthropic",
            r"OpenAI",
            r"Google",
            r"Microsoft",
            r"Cloudflare",
            r"NIST",
            r"Karpathy",
            r"arXiv",
            r"Nature",
            r"Science",
            r"SemiEngineering",
            r"Business Insider",
            r"PURSUE",
            r"CIE-Scorer",
            r"CRV",
            r"CMI",
            r"AMP",
            r"AgentMesh",
            r"MeshRescue",
            r"HumanMesh",
            r"x402",
            r"OpenClaw",
            r"Moltbook",
            r"MDPI",
            r"DoD",
            r"DoEnergy",
            r"BrainChip",
            r"TetraMem",
            r"Lightmatter",
            r"Ayar",
            r"EDGEAI",
            r"Nvidia",
        ]
        for pat in org_patterns:
            if re.search(pat, ref, re.IGNORECASE):
                orgs.add(pat)

        # Count semicolon or plus-separated references
        separators = ref.count(";") + ref.count("+") + ref.count(",")
        nrs = max(len(orgs), separators + 1, 1)

        # Cap at 10 for sanity
        nrs = min(nrs, 10)

        counts.append(nrs)
        breakdown.append(
            {
                "claim": claim["claim"][:50],
                "nrs": nrs,
                "sources_found": list(orgs)[:5],
            }
        )

    return {
        "mean_nrs": round(sum(counts) / len(counts), 1) if counts else 0.0,
        "max_nrs": max(counts) if counts else 0,
        "claims_scored": len(counts),
        "breakdown": breakdown,
    }


def positioning_index(
    claims: Sequence[dict[str, Any]],
    actions_taken: int | None = None,
) -> dict[str, Any]:
    """Compute PI: actions taken vs actions implied by prescience.

    This is the most important and most manual metric. It measures whether
    the forecaster acted on their own predictions.

    Actions implied per claim (heuristic):
    - governance claims → publish, build tooling, advocate
    - architecture claims → open-source, spec, standard
    - trend claims → position, invest, speak
    - hardware claims → patent, partner, prototype

    Default: 3 implied actions per validated claim of weight >= 3

    Args:
        claims: All claims (validated carry more implied actions).
        actions_taken: Override with known count. If None, uses heuristic.

    Returns:
        Dict with pi, actions_taken, actions_implied, and status.
    """
    implied = 0
    for claim in claims:
        status = claim.get("status", "")
        cat = claim.get("category", "general")
        pts = claim.get("points") or 0

        if status == "validated" and pts >= 10:
            # High-impact validated claims imply more action
            if cat in ("ai_governance", "ai_trends"):
                implied += 4
            elif cat in ("agent_architecture", "ai_hardware"):
                implied += 3
            else:
                implied += 2
        elif status == "validated":
            implied += 1
        elif status == "pending" and pts >= 10:
            implied += 2

    taken = actions_taken if actions_taken is not None else 0
    pi = taken / implied if implied > 0 else 0.0

    return {
        "pi": round(pi, 2),
        "actions_taken": taken,
        "actions_implied": implied,
        "status": "excellent"
        if pi >= 0.8
        else "good"
        if pi >= 0.5
        else "needs_work"
        if pi >= 0.2
        else "critical",
    }


def brier_score(
    claims: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute classical Brier score for binary probabilistic forecasts.

    Brier = mean((p - o)²) where p = stated confidence, o = outcome (0 or 1).

    Also computes:
    - Brier skill score vs a naive baseline (mean outcome as predictor)
    - Reliability, Resolution, Uncertainty (Murphy decomposition)
    - Calibration curve buckets

    Returns:
        Dict with brier, skill_score, decomposition, and per-claim scores.
    """
    entries: list[tuple[float, int]] = []
    breakdown: list[dict[str, Any]] = []

    for claim in claims:
        status = claim.get("status", "")
        if status not in ("validated", "falsified", "expired"):
            continue
        p = claim.get("confidence")
        if p is None:
            continue
        p = float(p)
        o = 1 if status == "validated" else 0
        entries.append((p, o))
        breakdown.append(
            {
                "claim": claim["claim"][:50],
                "p": round(p, 3),
                "o": o,
                "brier": round((p - o) ** 2, 4),
            }
        )

    if not entries:
        return {
            "brier": None,
            "skill_score": None,
            "decomposition": {
                "reliability": None,
                "resolution": None,
                "uncertainty": None,
            },
            "claims_scored": 0,
            "breakdown": [],
        }

    # Overall Brier
    brier = sum((p - o) ** 2 for p, o in entries) / len(entries)

    # Baseline: predict mean outcome for everything
    mean_o = sum(o for _, o in entries) / len(entries)
    baseline_brier = sum((mean_o - o) ** 2 for _, o in entries) / len(entries)
    skill = 1.0 - (brier / baseline_brier) if baseline_brier > 0 else 0.0

    # Murphy decomposition (simplified: bucket by confidence rounded to 0.1)
    from collections import defaultdict

    buckets: dict[float, list[int]] = defaultdict(list)
    for p, o in entries:
        bucket_p = round(p, 1)
        buckets[bucket_p].append(o)

    reliability = 0.0
    resolution = 0.0
    n_total = len(entries)
    for bucket_p, outcomes in buckets.items():
        n_b = len(outcomes)
        o_bar_b = sum(outcomes) / n_b
        # Reliability: average of (p_bucket - o_bar_b)² weighted by n_b
        reliability += (n_b / n_total) * (bucket_p - o_bar_b) ** 2
        # Resolution: average of (o_bar_b - mean_o)² weighted by n_b
        resolution += (n_b / n_total) * (o_bar_b - mean_o) ** 2

    uncertainty = mean_o * (1 - mean_o)

    return {
        "brier": round(brier, 4),
        "skill_score": round(skill, 4),
        "decomposition": {
            "reliability": round(reliability, 4),
            "resolution": round(resolution, 4),
            "uncertainty": round(uncertainty, 4),
        },
        "claims_scored": len(entries),
        "breakdown": breakdown,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Unified TZPF Summary
# ═══════════════════════════════════════════════════════════════════════════


def compute_tzpf(
    claims: Sequence[dict[str, Any]],
    actions_taken: int | None = None,
    impact_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute the full TZPF scorecard for a set of claims.

    Args:
        claims: List of claim dicts from prescience_claims.yaml or DB.
        actions_taken: Known count of actions taken. If None, PI = 0.
        impact_weights: Override DFI category weights.

    Returns:
        Complete TZPF summary dict with all metrics.
    """
    validated = [c for c in claims if c.get("status") == "validated"]
    all_closed = [
        c for c in claims if c.get("status") in ("validated", "falsified", "expired")
    ]

    dfi = directional_foresight_index(validated, impact_weights)
    tar = temporal_acceleration_ratio(validated)
    hc = hyperstition_coefficient(validated)
    bci = behavioral_calibration_index(all_closed)
    pvs = partial_validation_spectrum(claims)
    nrs = narrative_resonance_score(validated)
    pi = positioning_index(validated, actions_taken=actions_taken)
    brier = brier_score(all_closed)

    return {
        "tzpf_version": "1.1.0",
        "claims_total": len(claims),
        "claims_validated": len(validated),
        "metrics": {
            "dfi": dfi,
            "tar": tar,
            "hc": hc,
            "bci": bci,
            "pvs": pvs,
            "nrs": nrs,
            "pi": pi,
            "brier": brier,
        },
        "composite": {
            "directional_prescience": dfi["dfi"],
            "timeline_calibration": tar.get("mean_tar"),
            "hyperstitional_potency": hc["mean_hc"],
            "confidence_shyness": bci.get("shyness_gap"),
            "validation_completeness": pvs["mean_pvs"],
            "narrative_resonance": nrs["mean_nrs"],
            "action_orientation": pi["pi"],
            "calibration_brier": brier["brier"],
            "calibration_skill": brier["skill_score"],
        },
    }
