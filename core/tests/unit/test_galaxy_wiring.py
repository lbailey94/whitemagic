# ruff: noqa: BLE001
"""Tests for Phase 2: Cognitive Galaxy Wiring.

Verifies that cognitive subsystems route their memory writes
to the correct galaxies via the galaxy= parameter on store().
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_galaxy_wire_"))

# Source root for whitemagic core
_SRC = Path(__file__).resolve().parent.parent.parent / "whitemagic"


def _extract_galaxy_args(filepath: Path) -> list[tuple[int, str | None]]:
    """Parse a Python file and find all .store() calls, returning (line, galaxy_value) pairs."""
    source = filepath.read_text()
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "store":
                galaxy_val = None
                for kw in node.keywords:
                    if kw.arg == "galaxy":
                        if isinstance(kw.value, ast.Constant):
                            galaxy_val = kw.value.value
                        elif isinstance(kw.value, ast.Name):
                            galaxy_val = f"var:{kw.value.id}"
                        else:
                            galaxy_val = "<expr>"
                results.append((node.lineno, galaxy_val))
    return results


class TestDreamCycleGalaxyWiring(unittest.TestCase):
    """Dream cycle should route to creative_solutions galaxy."""

    def test_dream_insights_have_galaxy(self):
        filepath = _SRC / "core/dreaming/dream_cycle.py"
        calls = _extract_galaxy_args(filepath)
        # Should have at least one store call with galaxy="creative_solutions"
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "creative_solutions",
            galaxy_calls,
            "dream_cycle.py must route store() to creative_solutions galaxy",
        )


class TestInsightPipelineGalaxyWiring(unittest.TestCase):
    """Insight pipeline should route to insight galaxy."""

    def test_briefing_has_galaxy(self):
        filepath = _SRC / "core/intelligence/insight_pipeline.py"
        calls = _extract_galaxy_args(filepath)
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "insight",
            galaxy_calls,
            "insight_pipeline.py must route store() to insight galaxy",
        )


class TestNarrativeCompressorGalaxyWiring(unittest.TestCase):
    """Narrative compressor should route to creative_solutions galaxy."""

    def test_narrative_has_galaxy(self):
        filepath = _SRC / "core/dreaming/narrative_compressor.py"
        calls = _extract_galaxy_args(filepath)
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "creative_solutions",
            galaxy_calls,
            "narrative_compressor.py must route store() to creative_solutions galaxy",
        )


class TestCrossDomainDetectorGalaxyWiring(unittest.TestCase):
    """Cross-domain detector should route to creative_solutions galaxy."""

    def test_schema_has_galaxy(self):
        filepath = _SRC / "core/intelligence/synthesis/cross_domain_detector.py"
        calls = _extract_galaxy_args(filepath)
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "creative_solutions",
            galaxy_calls,
            "cross_domain_detector.py must route store() to creative_solutions galaxy",
        )


class TestDreamStateGalaxyWiring(unittest.TestCase):
    """Dream state emergence should route to creative_solutions galaxy."""

    def test_dream_state_has_galaxy(self):
        filepath = _SRC / "core/patterns/emergence/dream_state.py"
        calls = _extract_galaxy_args(filepath)
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "creative_solutions",
            galaxy_calls,
            "dream_state.py must route store() to creative_solutions galaxy",
        )


class TestAutonomousLearnerGalaxyWiring(unittest.TestCase):
    """Autonomous learner should route to knowledge galaxy."""

    def test_learner_has_galaxy(self):
        filepath = _SRC / "core/patterns/pattern_consciousness/autonomous_learner.py"
        calls = _extract_galaxy_args(filepath)
        galaxy_calls = [g for _, g in calls if g is not None]
        self.assertIn(
            "knowledge",
            galaxy_calls,
            "autonomous_learner.py must route store() to knowledge galaxy",
        )
        # All 3 store calls should have galaxy
        self.assertEqual(
            len(galaxy_calls),
            3,
            "autonomous_learner.py should have 3 store() calls with galaxy=",
        )


class TestNoUnwiredStoreCallsInWiredFiles(unittest.TestCase):
    """Ensure all store() calls in wired files have galaxy= parameter."""

    def test_dream_cycle_all_stores_wired(self):
        filepath = _SRC / "core/dreaming/dream_cycle.py"
        calls = _extract_galaxy_args(filepath)
        for lineno, galaxy in calls:
            self.assertIsNotNone(
                galaxy,
                f"dream_cycle.py store() at line {lineno} missing galaxy= parameter",
            )

    def test_insight_pipeline_all_stores_wired(self):
        filepath = _SRC / "core/intelligence/insight_pipeline.py"
        calls = _extract_galaxy_args(filepath)
        for lineno, galaxy in calls:
            self.assertIsNotNone(
                galaxy,
                f"insight_pipeline.py store() at line {lineno} missing galaxy= parameter",
            )

    def test_narrative_compressor_all_stores_wired(self):
        filepath = _SRC / "core/dreaming/narrative_compressor.py"
        calls = _extract_galaxy_args(filepath)
        for lineno, galaxy in calls:
            self.assertIsNotNone(
                galaxy,
                f"narrative_compressor.py store() at line {lineno} missing galaxy= parameter",
            )

    def test_autonomous_learner_all_stores_wired(self):
        filepath = _SRC / "core/patterns/pattern_consciousness/autonomous_learner.py"
        calls = _extract_galaxy_args(filepath)
        for lineno, galaxy in calls:
            self.assertIsNotNone(
                galaxy,
                f"autonomous_learner.py store() at line {lineno} missing galaxy= parameter",
            )


if __name__ == "__main__":
    unittest.main()
