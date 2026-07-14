"""Tests for P3 gap closure — DreamCycle oracle claim auto-resolution.

Tests verify:
- _dream_prediction() includes oracle_claims_resolved field
- Stale oracle claims (>30 days) are auto-resolved
- _check_oracle_action_evidence searches memory for guidance keywords
- Recent claims (<30 days) are not auto-resolved
- Graceful degradation when TemporalForecastDB unavailable
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.core.dreaming.dream_cycle import DreamCycle


@pytest.fixture
def mock_dream_cycle():
    """Create a DreamCycle with mocked dependencies."""
    cycle = DreamCycle()
    yield cycle


class TestOracleClaimAutoResolution:
    """Test that DreamCycle auto-resolves stale oracle claims."""

    def test_dream_prediction_includes_oracle_claims_resolved(self, mock_dream_cycle):
        """_dream_prediction should include oracle_claims_resolved field."""
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.row_factory = None
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        mock_db = MagicMock()
        mock_db.get_oracle_claims.return_value = []

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um), \
             patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db):
            result = mock_dream_cycle._dream_prediction()
            assert "oracle_claims_resolved" in result
            assert result["oracle_claims_resolved"] == 0

    def test_stale_claim_resolved_as_falsified(self, mock_dream_cycle):
        """Oracle claims older than 30 days with no action evidence should be falsified."""
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.row_factory = None
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        old_date = (datetime.utcnow() - timedelta(days=45)).date().isoformat()
        mock_db = MagicMock()
        mock_db.get_oracle_claims.return_value = [
            {"id": "claim-1", "source_date": old_date, "guidance_action": "Persevere in your path", "oracle_hexagram": 32},
        ]

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um), \
             patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db), \
             patch.object(mock_dream_cycle, "_check_oracle_action_evidence", return_value=False):
            result = mock_dream_cycle._dream_prediction()
            assert result["oracle_claims_resolved"] == 1
            mock_db.resolve_oracle_claim.assert_called_once_with(
                "claim-1", "falsified",
                notes="Auto-resolved: no action evidence found after 30 days"
            )

    def test_stale_claim_resolved_as_validated(self, mock_dream_cycle):
        """Oracle claims older than 30 days with action evidence should be validated."""
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.row_factory = None
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        old_date = (datetime.utcnow() - timedelta(days=45)).date().isoformat()
        mock_db = MagicMock()
        mock_db.get_oracle_claims.return_value = [
            {"id": "claim-2", "source_date": old_date, "guidance_action": "Take bold action now", "oracle_hexagram": 1},
        ]

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um), \
             patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db), \
             patch.object(mock_dream_cycle, "_check_oracle_action_evidence", return_value=True):
            result = mock_dream_cycle._dream_prediction()
            assert result["oracle_claims_resolved"] == 1
            mock_db.resolve_oracle_claim.assert_called_once_with(
                "claim-2", "validated",
                notes="Auto-resolved: action evidence found in dream cycle"
            )

    def test_recent_claims_not_resolved(self, mock_dream_cycle):
        """Oracle claims younger than 30 days should not be auto-resolved."""
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.row_factory = None
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        recent_date = (datetime.utcnow() - timedelta(days=10)).date().isoformat()
        mock_db = MagicMock()
        mock_db.get_oracle_claims.return_value = [
            {"id": "claim-3", "source_date": recent_date, "guidance_action": "Wait patiently", "oracle_hexagram": 2},
        ]

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um), \
             patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db):
            result = mock_dream_cycle._dream_prediction()
            assert result["oracle_claims_resolved"] == 0
            mock_db.resolve_oracle_claim.assert_not_called()

    def test_graceful_degradation_no_db(self, mock_dream_cycle):
        """Should handle TemporalForecastDB failure gracefully."""
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.row_factory = None
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um), \
             patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", side_effect=Exception("DB fail")):
            result = mock_dream_cycle._dream_prediction()
            assert result.get("oracle_claims_resolved", 0) == 0


class TestCheckOracleActionEvidence:
    """Test the _check_oracle_action_evidence helper."""

    def test_empty_guidance_returns_false(self, mock_dream_cycle):
        assert mock_dream_cycle._check_oracle_action_evidence("") is False

    def test_short_guidance_returns_false(self, mock_dream_cycle):
        assert mock_dream_cycle._check_oracle_action_evidence("ab") is False

    def test_finds_evidence_in_memory(self, mock_dream_cycle):
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=1)
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um):
            result = mock_dream_cycle._check_oracle_action_evidence("Persevere diligently through challenges")
            assert result is True

    def test_no_evidence_returns_false(self, mock_dream_cycle):
        mock_um = MagicMock()
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=0)
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_um.pool.connection.return_value.__enter__.return_value = mock_conn

        with patch("whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um):
            result = mock_dream_cycle._check_oracle_action_evidence("Retreat from this situation entirely")
            assert result is False

    def test_memory_failure_returns_false(self, mock_dream_cycle):
        with patch("whitemagic.core.memory.unified.get_unified_memory", side_effect=Exception("Memory fail")):
            result = mock_dream_cycle._check_oracle_action_evidence("Take bold creative action")
            assert result is False
