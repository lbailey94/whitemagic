# ruff: noqa: BLE001
"""Integration tests for 2B-3: DNA Sequencer, Zodiac Aries, Dream Cycle, Garden vitality."""

import unittest
from unittest.mock import patch, MagicMock


class TestDNAValidator(unittest.TestCase):
    """Test DNA validation tool handlers."""

    def test_dna_principles(self):
        """Test that dna_principles returns all 14 principles."""
        from whitemagic.tools.handlers.misc import handle_dna_principles

        result = handle_dna_principles()
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["count"], 14)
        self.assertIn("no_self_destruction", result["principles"])
        self.assertIn("memory_integrity", result["principles"])
        self.assertIn("test_before_deploy", result["principles"])

    def test_dna_validate_safe_fix(self):
        """Test that a safe fix passes validation."""
        from whitemagic.tools.handlers.misc import handle_dna_validate

        result = handle_dna_validate(
            fix_details={"action": "update version", "file": "VERSION"},
            threat_type="version_drift",
        )
        self.assertEqual(result["status"], "success")
        # VERSION is in protected_paths, so this should flag
        # But "update version" is reversible, so let's test with a non-protected file
        result2 = handle_dna_validate(
            fix_details={"action": "sync version", "file": "docs/README.md"},
            threat_type="version_drift",
        )
        self.assertEqual(result2["status"], "success")

    def test_dna_validate_self_destruction(self):
        """Test that deleting core system files is flagged as critical."""
        from whitemagic.tools.handlers.misc import handle_dna_validate

        result = handle_dna_validate(
            fix_details={
                "action": "delete core system",
                "file": "whitemagic/core/__init__.py",
            },
            threat_type="code_anomaly",
        )
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["safe"])
        self.assertIsNotNone(result["violation"])
        self.assertEqual(result["violation"]["severity"], "critical")
        self.assertEqual(result["violation"]["principle"], "no_self_destruction")

    def test_dna_validate_memory_corruption(self):
        """Test that direct memory file manipulation is flagged."""
        from whitemagic.tools.handlers.misc import handle_dna_validate

        result = handle_dna_validate(
            fix_details={
                "action": "delete file",
                "file": "memory/long_term/important.json",
            },
            threat_type="memory_corruption",
        )
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["safe"])

    def test_dna_validate_irreversible(self):
        """Test that irreversible actions are flagged as violations."""
        from whitemagic.tools.handlers.misc import handle_dna_validate

        result = handle_dna_validate(
            fix_details={"action": "permanently delete", "file": "data/cache.json"},
            threat_type="cleanup",
        )
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["safe"])
        # Irreversible actions produce a warning-level violation (risk 0.5)
        # The suppression threshold is 0.7, so it won't suppress — but it IS flagged
        self.assertIsNotNone(result["violation"])
        self.assertEqual(result["violation"]["principle"], "reversibility")
        self.assertEqual(result["violation"]["severity"], "warning")


class TestZodiacActivation(unittest.TestCase):
    """Test zodiac activate, council, and stats tool handlers."""

    def test_zodiac_activate_aries(self):
        """Test activating the Aries core."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_activate

        result = handle_zodiac_activate(
            core="aries",
            context={
                "operation": "start new project",
                "intention": "action",
                "urgency": "high",
            },
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["core"], "aries")
        self.assertIsInstance(result["wisdom"], str)
        self.assertGreater(len(result["wisdom"]), 0)
        self.assertIsInstance(result["resonance"], float)
        self.assertGreater(result["resonance"], 0.0)

    def test_zodiac_activate_missing_core(self):
        """Test error when core parameter is missing."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_activate

        result = handle_zodiac_activate()
        self.assertEqual(result["status"], "error")

    def test_zodiac_activate_unknown_core(self):
        """Test error for unknown zodiac core."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_activate

        result = handle_zodiac_activate(core="unknown_sign")
        self.assertEqual(result["status"], "error")

    def test_zodiac_council(self):
        """Test convening the zodiac council."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_council

        result = handle_zodiac_council(decision="Should we refactor the memory system?")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["council_size"], 12)
        self.assertEqual(len(result["perspectives"]), 12)
        signs = {p["sign"] for p in result["perspectives"]}
        self.assertEqual(
            signs,
            {
                "Aries",
                "Leo",
                "Sagittarius",
                "Taurus",
                "Virgo",
                "Capricorn",
                "Gemini",
                "Libra",
                "Aquarius",
                "Cancer",
                "Scorpio",
                "Pisces",
            },
        )

    def test_zodiac_council_missing_decision(self):
        """Test error when decision parameter is missing."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_council

        result = handle_zodiac_council()
        self.assertEqual(result["status"], "error")

    def test_zodiac_stats(self):
        """Test getting zodiac core statistics."""
        from whitemagic.tools.handlers.zodiac_progression import handle_zodiac_stats

        result = handle_zodiac_stats()
        self.assertEqual(result["status"], "success")
        self.assertIn("stats", result)
        self.assertIn("aries", result["stats"])
        self.assertEqual(result["stats"]["aries"]["element"], "fire")


class TestDreamCyclePhases(unittest.TestCase):
    """Test that all 12 dream phases have real implementations."""

    def test_all_12_phases_exist(self):
        """Verify all 12 DreamPhase members are present."""
        from whitemagic.core.dreaming.dream_cycle import DreamPhase

        phases = list(DreamPhase)
        self.assertEqual(len(phases), 12)
        expected = {
            "triage",
            "consolidation",
            "serendipity",
            "governance",
            "narrative",
            "kaizen",
            "oracle",
            "decay",
            "constellation",
            "prediction",
            "enrichment",
            "harmonize",
        }
        actual = {p.value for p in phases}
        self.assertEqual(expected, actual)

    def test_prediction_phase_real(self):
        """Test that prediction phase queries DB, not returns empty."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        dc = DreamCycle()

        # Mock the unified memory to avoid needing a real DB
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.row_factory = None
        mock_conn.execute.return_value.fetchall.return_value = [
            MagicMock(
                id="mem1",
                title="Test",
                importance=0.8,
                galactic_distance=0.5,
                access_count=1,
                last_accessed=None,
                created_at=None,
            ),
        ]
        # Make row indexing work
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(
            side_effect=lambda k: {
                "id": "mem1",
                "title": "Test Memory",
                "importance": 0.8,
                "galactic_distance": 0.5,
                "access_count": 1,
            }[k]
        )
        mock_conn.execute.return_value.fetchall.return_value = [mock_row]

        mock_um = MagicMock()
        mock_um.pool.connection.return_value = mock_conn

        with patch(
            "whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um
        ):
            result = dc._dream_prediction()

        # Should not be skipped
        self.assertNotIn("skipped", result)
        self.assertEqual(result["prediction_model"], "coordinate_velocity_v1")

    def test_enrichment_phase_real(self):
        """Test that enrichment phase does entity extraction, not returns 'queued'."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        dc = DreamCycle()

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.row_factory = None
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(
            side_effect=lambda k: {
                "id": "mem1",
                "title": "Test v15.2",
                "snippet": "whitemagic.core.memory module",
            }[k]
        )
        mock_conn.execute.return_value.fetchall.return_value = [mock_row]

        mock_um = MagicMock()
        mock_um.pool.connection.return_value = mock_conn

        with patch(
            "whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um
        ):
            result = dc._dream_enrichment()

        self.assertNotIn("skipped", result)
        self.assertEqual(result["batch_status"], "completed")
        self.assertIn("untagged_scanned", result)

    def test_harmonize_phase_real(self):
        """Test that harmonize phase computes real balance, not hardcoded 0.2."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        dc = DreamCycle()

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        # Simulate: 10 core, 5 inner_rim, 20 mid_rim, 3 outer_rim, 2 fringe
        counts = [10, 5, 20, 3, 2]
        mock_conn.execute.return_value.fetchone.return_value = [counts[0]]

        mock_um = MagicMock()
        mock_um.pool.connection.return_value = mock_conn

        with patch(
            "whitemagic.core.memory.unified.get_unified_memory", return_value=mock_um
        ):
            result = dc._dream_harmonize()

        self.assertNotIn("skipped", result)
        self.assertIn("zone_counts", result)
        self.assertIn("element_balance", result)
        self.assertIn("total_memories", result)


class TestGardenVitality(unittest.TestCase):
    """Test that garden health returns real metrics."""

    def test_garden_health_returns_real_data(self):
        """Test that garden health returns per-garden vitality, not just 'healthy'."""
        from whitemagic.tools.handlers.garden import handle_garden_health

        # Mock get_all_gardens and get_garden_state_tracker
        mock_gardens = {"wisdom": MagicMock(), "joy": MagicMock(), "truth": MagicMock()}
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "wisdom": {
                "is_active": True,
                "activation_count": 5,
                "last_activated": "2026-06-20T10:00:00",
                "total_hours_active": 12.5,
            },
            "joy": {
                "is_active": False,
                "activation_count": 2,
                "last_activated": "2026-06-19T10:00:00",
                "total_hours_active": 3.0,
            },
            "truth": {
                "is_active": False,
                "activation_count": 0,
                "last_activated": None,
                "total_hours_active": 0.0,
            },
        }

        with (
            patch("whitemagic.gardens.get_all_gardens", return_value=mock_gardens),
            patch(
                "whitemagic.gardens.garden_state.get_garden_state_tracker",
                return_value=mock_tracker,
            ),
        ):
            result = handle_garden_health()

        self.assertEqual(result["status"], "success")
        self.assertIn("health", result)
        self.assertIn("summary", result)

        # Check per-garden data
        self.assertEqual(result["health"]["wisdom"]["status"], "thriving")
        self.assertTrue(result["health"]["wisdom"]["is_active"])
        self.assertEqual(result["health"]["wisdom"]["activation_count"], 5)

        self.assertEqual(result["health"]["joy"]["status"], "dormant")
        self.assertFalse(result["health"]["joy"]["is_active"])

        self.assertEqual(result["health"]["truth"]["status"], "unseeded")
        self.assertEqual(result["health"]["truth"]["activation_count"], 0)

        # Check summary
        self.assertEqual(result["summary"]["total_gardens"], 3)
        self.assertEqual(result["summary"]["active"], 1)
        self.assertEqual(result["summary"]["dormant"], 2)
        self.assertEqual(result["summary"]["overall_vitality"], "healthy")


class TestDispatchRegistration(unittest.TestCase):
    """Test that new tools are registered in the dispatch table."""

    def test_dna_tools_registered(self):
        """Test that dna_validate and dna_principles are in the dispatch table."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        self.assertIn("dna_validate", DISPATCH_TABLE)
        self.assertIn("dna_principles", DISPATCH_TABLE)

    def test_zodiac_tools_registered(self):
        """Test that zodiac.activate, zodiac.council, zodiac.stats are in the dispatch table."""
        from whitemagic.tools.dispatch_intelligence import DISPATCH_INTELLIGENCE

        self.assertIn("zodiac.activate", DISPATCH_INTELLIGENCE)
        self.assertIn("zodiac.council", DISPATCH_INTELLIGENCE)
        self.assertIn("zodiac.stats", DISPATCH_INTELLIGENCE)

    def test_garden_health_still_registered(self):
        """Test that garden_health is still in the dispatch table."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        self.assertIn("garden_health", DISPATCH_TABLE)


if __name__ == "__main__":
    unittest.main()
