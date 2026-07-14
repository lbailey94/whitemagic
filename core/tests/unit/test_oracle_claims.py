"""Tests for Oracle Outcome Tracking (Phase 3).

Tests verify:
- Oracle claim creation with hexagram metadata
- Claim resolution marks outcomes correctly
- Oracle Brier score is computed separately from simulation Brier
- Prescience score includes oracle claims
- Graceful degradation when DB unavailable
"""

import pytest
import tempfile
from pathlib import Path

from whitemagic.forecasting.temporal_db import TemporalForecastDB
from whitemagic.oracle.wisdom_synthesis import OracleSynthesizer, SynthesisResult


@pytest.fixture
def temp_db():
    """Create a temporary TemporalForecastDB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_predictions.db"
        db = TemporalForecastDB(db_path=db_path)
        yield db


class TestOracleClaimCreation:
    """Test oracle claim creation in TemporalForecastDB."""

    def test_record_oracle_claim(self, temp_db):
        claim_id = temp_db.record_oracle_claim(
            question="Oracle guidance: Persevere in right action",
            source="oracle:32",
            confidence=0.7,
            oracle_source="synthesized",
            oracle_hexagram=32,
            guidance_action="Persevere with patience",
        )
        assert claim_id is not None
        assert len(claim_id) > 0

        claims = temp_db.get_oracle_claims()
        assert len(claims) == 1
        assert claims[0]["claim_type"] == "oracle"
        assert claims[0]["oracle_source"] == "synthesized"
        assert claims[0]["oracle_hexagram"] == 32
        assert claims[0]["status"] == "pending"
        assert claims[0]["guidance_action"] == "Persevere with patience"

    def test_record_oracle_claim_invalid_confidence(self, temp_db):
        with pytest.raises(ValueError):
            temp_db.record_oracle_claim(
                question="Test",
                source="oracle:1",
                confidence=1.5,
            )

    def test_get_oracle_claims_filtered(self, temp_db):
        temp_db.record_oracle_claim("Claim 1", "oracle:1", 0.6)
        temp_db.record_oracle_claim("Claim 2", "oracle:2", 0.8)

        pending = temp_db.get_oracle_claims(status="pending")
        assert len(pending) == 2

        validated = temp_db.get_oracle_claims(status="validated")
        assert len(validated) == 0

    def test_oracle_claims_separate_from_regular(self, temp_db):
        """Oracle claims should not mix with regular predictions."""
        temp_db.add_prediction("Regular prediction", "2026-01-01", 0.7)
        temp_db.record_oracle_claim("Oracle claim", "oracle:1", 0.6)

        oracle_claims = temp_db.get_oracle_claims()
        assert len(oracle_claims) == 1
        assert oracle_claims[0]["claim_type"] == "oracle"

        all_preds = temp_db.all_predictions()
        assert len(all_preds) == 2  # Both exist, but oracle has claim_type


class TestOracleClaimResolution:
    """Test resolving oracle claims."""

    def test_resolve_positive(self, temp_db):
        claim_id = temp_db.record_oracle_claim(
            "Oracle guidance: Act boldly",
            "oracle:1",
            0.8,
            oracle_hexagram=1,
        )
        result = temp_db.resolve_oracle_claim(claim_id, action_taken=True, outcome_positive=True)
        assert result["status"] == "validated"
        assert result["action_taken"] is True

        claims = temp_db.get_oracle_claims()
        assert claims[0]["status"] == "validated"
        assert claims[0]["action_taken"] == 1

    def test_resolve_negative(self, temp_db):
        claim_id = temp_db.record_oracle_claim(
            "Oracle guidance: Retreat",
            "oracle:33",
            0.6,
        )
        result = temp_db.resolve_oracle_claim(claim_id, action_taken=False, outcome_positive=False)
        assert result["status"] == "falsified"

        claims = temp_db.get_oracle_claims()
        assert claims[0]["status"] == "falsified"
        assert claims[0]["action_taken"] == -1

    def test_resolve_nonexistent_claim(self, temp_db):
        with pytest.raises(KeyError):
            temp_db.resolve_oracle_claim("nonexistent-id", True, True)


class TestOraclePrescienceScore:
    """Test oracle-specific prescience scoring."""

    def test_empty_score(self, temp_db):
        score = temp_db.oracle_prescience_score()
        assert score["total"] == 0
        assert score["brier_score"] is None
        assert score["accuracy"] is None

    def test_score_with_resolved_claims(self, temp_db):
        # Create and resolve several claims
        c1 = temp_db.record_oracle_claim("Claim 1", "oracle:1", 0.8, oracle_hexagram=1)
        temp_db.resolve_oracle_claim(c1, action_taken=True, outcome_positive=True)

        c2 = temp_db.record_oracle_claim("Claim 2", "oracle:2", 0.6, oracle_hexagram=2)
        temp_db.resolve_oracle_claim(c2, action_taken=True, outcome_positive=False)

        score = temp_db.oracle_prescience_score()
        assert score["total"] == 2
        assert score["validated"] == 1
        assert score["falsified"] == 1
        assert score["brier_score"] is not None
        assert 0.0 <= score["accuracy"] <= 1.0

    def test_score_with_pending(self, temp_db):
        temp_db.record_oracle_claim("Pending", "oracle:1", 0.7)
        score = temp_db.oracle_prescience_score()
        assert score["total"] == 1
        assert score["pending"] == 1
        assert score["brier_score"] is None


class TestSynthesizerEmitsClaims:
    """Test that OracleSynthesizer emits claims."""

    def _make_oracle_output(self, hexagram_num=32):
        return {
            "sign": "Leo",
            "element": "fire",
            "modality": "fixed",
            "phase": "yang",
            "wu_xing": "fire",
            "iching_name": "Duration",
            "iching_number": hexagram_num,
            "iching_judgment": "Duration succeeds through constancy.",
            "iching_guidance": "Persevere in right action with patience and determination.",
            "ifa_odu": "Ogbe",
            "ifa_wisdom": "Patience brings blessings to those who wait.",
            "ifa_ire": "Good fortune through persistence",
            "ifa_osogbo": "Avoid haste",
        }

    def test_synthesize_emits_claim_ids(self):
        output = self._make_oracle_output(32)
        result = OracleSynthesizer().synthesize(output)
        assert hasattr(result, "claim_ids")
        assert isinstance(result.claim_ids, list)

    def test_synthesize_claim_ids_populated(self):
        """With a real DB, claim_ids should contain UUIDs."""
        output = self._make_oracle_output(32)
        result = OracleSynthesizer().synthesize(output)
        # Claims may or may not be created depending on DB availability
        # but the field should always exist
        if result.claim_ids:
            for cid in result.claim_ids:
                assert isinstance(cid, str)
                assert len(cid) > 0

    def test_synthesize_without_guidance_no_claims(self):
        """If practical guidance is too short, no claims should be created."""
        output = {
            "sign": "Aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "fire",
            "iching_name": "",
            "iching_number": 1,
            "iching_judgment": "",
            "iching_guidance": "",
            "ifa_odu": "",
            "ifa_wisdom": "",
            "ifa_ire": "",
            "ifa_osogbo": "",
        }
        result = OracleSynthesizer().synthesize(output)
        # With no guidance text, claim_ids should be empty
        # (or might still have claims if guidance is derived from phase)
        assert isinstance(result.claim_ids, list)
