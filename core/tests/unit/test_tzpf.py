"""Unit tests for the Transition-Zone Prescience Framework (TZPF)."""

from whitemagic.forecasting.tzpf import (
    behavioral_calibration_index,
    brier_score,
    compute_tzpf,
    directional_foresight_index,
    hyperstition_coefficient,
    narrative_resonance_score,
    partial_validation_spectrum,
    positioning_index,
    temporal_acceleration_ratio,
)


SAMPLE_CLAIMS = [
    {
        "claim": "AI governance framework — cryptographic audit trail",
        "source_date": "2025-06-01",
        "confidence": 0.75,
        "behavioral_confidence": 0.85,
        "category": "ai_governance",
        "status": "validated",
        "validation_date": "2026-05-01",
        "validation_ref": "Anthropic model-welfare audit trail",
        "lead_weeks": 52.0,
        "points": 52.0,
        "notes": "Validated; multiple independent sources confirmed",
    },
    {
        "claim": "Agent consensus mesh — P2P agreement protocol",
        "source_date": "2025-09-01",
        "confidence": 0.60,
        "behavioral_confidence": 0.70,
        "category": "agent_architecture",
        "status": "validated",
        "validation_date": "2026-03-01",
        "validation_ref": "Agent Mesh Protocol (AMP); AgentMesh MESH; MeshRescue",
        "lead_weeks": 26.0,
        "points": 26.0,
        "notes": "Core concept presciently identified; multiple production systems",
    },
    {
        "claim": "Neurophotonic data center",
        "source_date": "2025-09-01",
        "confidence": 0.60,
        "behavioral_confidence": 0.70,
        "category": "ai_hardware",
        "status": "validated",
        "validation_date": "2026-01-01",
        "validation_ref": "Lightmatter; Ayar Labs",
        "lead_weeks": 17.0,
        "points": 17.0,
        "notes": "Partial validation — photonic layer confirmed; superconducting spine speculative",
    },
    {
        "claim": "SMR microreactor leasing",
        "source_date": "2025-09-01",
        "confidence": 0.60,
        "category": "energy",
        "status": "pending",
        "notes": "Early signs but no commercial deployment yet",
    },
    {
        "claim": "Disaster prevention lattice",
        "source_date": "2025-09-01",
        "confidence": 0.70,
        "category": "ai_governance",
        "status": "pending",
        "notes": "Systems exist but not yet unified product",
    },
]


def test_directional_foresight_index() -> None:
    validated = [c for c in SAMPLE_CLAIMS if c["status"] == "validated"]
    result = directional_foresight_index(validated)
    assert result["raw_points"] == 95.0
    assert result["dfi"] > result["raw_points"]  # weighted > raw
    assert "ai_governance" in result["by_category"]


def test_temporal_acceleration_ratio() -> None:
    validated = [c for c in SAMPLE_CLAIMS if c["status"] == "validated"]
    result = temporal_acceleration_ratio(validated)
    # Should find at least one TAR where predicted_year is extracted
    assert result["claims_scored"] >= 0


def test_hyperstition_coefficient() -> None:
    validated = [c for c in SAMPLE_CLAIMS if c["status"] == "validated"]
    result = hyperstition_coefficient(validated)
    assert 0.0 <= result["mean_hc"] <= 1.0
    assert result["distribution"]["high (>0.5)"] >= 0


def test_behavioral_calibration_index() -> None:
    closed = [c for c in SAMPLE_CLAIMS if c["status"] in ("validated", "falsified")]
    result = behavioral_calibration_index(closed)
    assert result["mean_stated_confidence"] == 0.65  # (0.75 + 0.60 + 0.60) / 3
    assert result["mean_behavioral_confidence"] == 0.75  # (0.85 + 0.70 + 0.70) / 3
    assert result["mean_outcome"] == 1.0
    assert result["stated_gap"] < 0  # underconfident
    assert result["behavioral_gap"] < 0
    assert result["shyness_gap"] <= 0  # stated < behavioral


def test_partial_validation_spectrum() -> None:
    result = partial_validation_spectrum(SAMPLE_CLAIMS)
    assert 0.0 <= result["mean_pvs"] <= 1.0
    assert result["claims_scored"] == 5
    # Neurophotonic claim should score lower due to partial validation
    neuro = [r for r in result["breakdown"] if "Neurophotonic" in r["claim"]][0]
    assert neuro["pvs"] < 0.75


def test_narrative_resonance_score() -> None:
    validated = [c for c in SAMPLE_CLAIMS if c["status"] == "validated"]
    result = narrative_resonance_score(validated)
    # Consensus mesh has 3 orgs in validation_ref
    mesh = [r for r in result["breakdown"] if "consensus" in r["claim"]][0]
    assert mesh["nrs"] >= 2


def test_positioning_index() -> None:
    validated = [c for c in SAMPLE_CLAIMS if c["status"] == "validated"]
    # With 0 actions taken
    result = positioning_index(validated, actions_taken=0)
    assert result["pi"] == 0.0
    assert result["status"] == "critical"

    # With some actions taken
    result2 = positioning_index(validated, actions_taken=5)
    assert result2["pi"] > 0.0
    assert result2["actions_implied"] > 0


def test_brier_score() -> None:
    closed = [
        c for c in SAMPLE_CLAIMS if c["status"] in ("validated", "falsified", "expired")
    ]
    result = brier_score(closed)
    assert result["brier"] is not None
    assert 0.0 <= result["brier"] <= 1.0
    assert result["claims_scored"] == 3  # 3 validated in SAMPLE_CLAIMS
    assert "decomposition" in result
    assert "breakdown" in result


def test_compute_tzpf() -> None:
    result = compute_tzpf(SAMPLE_CLAIMS, actions_taken=0)
    assert result["tzpf_version"] == "1.1.0"
    assert result["claims_total"] == 5
    assert result["claims_validated"] == 3
    assert "metrics" in result
    assert "composite" in result
    assert result["composite"]["directional_prescience"] > 0
    assert result["metrics"]["pi"]["status"] == "critical"
    assert "brier" in result["metrics"]
    assert "calibration_brier" in result["composite"]
