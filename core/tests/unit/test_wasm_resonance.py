"""Tests for resonance models ported to WASM/TypeScript."""
import json
import math
from pathlib import Path

import pytest


def _ts_src() -> Path:
    return Path(__file__).resolve().parents[3] / "sdk" / "typescript" / "src"


class TestResonanceModelsTypeScript:
    def test_module_exists(self):
        assert (_ts_src() / "resonance_models.ts").exists()

    def test_exported_from_index(self):
        content = (_ts_src() / "index.ts").read_text()
        assert "MemoryDecayModel" in content
        assert "PatternResonanceDetector" in content
        assert "ConstellationMerger" in content
        assert "GardenResonanceMatrix" in content

    def test_has_required_classes(self):
        content = (_ts_src() / "resonance_models.ts").read_text()
        assert "class MemoryDecayModel" in content
        assert "class PatternResonanceDetector" in content
        assert "class ConstellationMerger" in content
        assert "class GardenResonanceMatrix" in content

    def test_has_required_methods(self):
        content = (_ts_src() / "resonance_models.ts").read_text()
        assert "predictRetention" in content
        assert "predictDecayCurve" in content
        assert "calculateReinforcementSchedule" in content
        assert "findResonantPatterns" in content
        assert "mergeOverlapping" in content
        assert "calculateInterGardenHarmony" in content


class TestParityWithPython:
    """Verify TypeScript constants match Python defaults."""

    def test_decay_params_match(self):
        from whitemagic.core.resonance.resonance_models import DecayParams
        py_params = DecayParams()
        ts_content = (_ts_src() / "resonance_models.ts").read_text()
        # Check that the default values are present in the TS source
        assert str(py_params.base_decay_rate) in ts_content
        assert str(py_params.importance_protection) in ts_content
        assert str(py_params.reinforcement_boost) in ts_content
        assert str(py_params.reinforcement_decay) in ts_content
        assert str(py_params.minimum_retention) in ts_content

    def test_embedding_dim_matches(self):
        from whitemagic.inference.browser_embedder import EMBEDDING_DIM
        ts_content = (_ts_src() / "browser_embedder.ts").read_text()
        assert str(EMBEDDING_DIM) in ts_content


class TestPythonResonanceModels:
    """Verify Python models still work correctly (regression check)."""

    def test_memory_decay_basic(self):
        from whitemagic.core.resonance.resonance_models import MemoryDecayModel
        model = MemoryDecayModel()
        result = model.predict_retention(importance=0.8, age_days=30, access_count=5)
        assert 0 < result["retention"] <= 1.0
        assert result["status"] in ("stable", "decaying", "critical")

    def test_pattern_resonance_basic(self):
        from whitemagic.core.resonance.resonance_models import PatternResonanceDetector
        detector = PatternResonanceDetector()
        memories = [
            {"id": 1, "resonance": {"frequency": 0.5}, "importance": 0.8},
            {"id": 2, "resonance": {"frequency": 0.55}, "importance": 0.7},
            {"id": 3, "resonance": {"frequency": 2.0}, "importance": 0.5},
        ]
        result = detector.find_resonant_patterns(memories)
        assert result["total_clusters"] >= 1
        assert result["memories_analyzed"] == 3

    def test_constellation_merger_basic(self):
        from whitemagic.core.resonance.resonance_models import ConstellationMerger, Constellation
        merger = ConstellationMerger(overlap_threshold=0.3)
        constellations = [
            Constellation(constellation_id=0, member_ids=[1, 2], center=(0, 0, 0, 0, 0), radius=1.0, avg_importance=0.8, garden="codex"),
            Constellation(constellation_id=1, member_ids=[3, 4], center=(0.1, 0, 0, 0, 0), radius=1.0, avg_importance=0.7, garden="codex"),
            Constellation(constellation_id=2, member_ids=[5], center=(10, 10, 10, 10, 10), radius=0.5, avg_importance=0.9, garden="sessions"),
        ]
        result = merger.merge_overlapping(constellations)
        assert result["merges"] >= 1
        assert result["total_after"] < result["total_before"]

    def test_garden_harmony_basic(self):
        from whitemagic.core.resonance.resonance_models import GardenResonanceMatrix
        matrix = GardenResonanceMatrix()
        gardens = {
            "codex": {"memory_count": 100, "avg_frequency": 0.3, "avg_damping": 0.1, "avg_importance": 0.7, "avg_vitality": 0.5},
            "sessions": {"memory_count": 50, "avg_frequency": 0.35, "avg_damping": 0.1, "avg_importance": 0.6, "avg_vitality": 0.4},
        }
        result = matrix.calculate_inter_garden_harmony(gardens)
        assert 0 <= result["overall_harmony"] <= 1.0
