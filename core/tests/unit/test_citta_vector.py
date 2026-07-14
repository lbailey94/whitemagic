"""Unit tests for CittaVector — multidimensional consciousness state."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_cv_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

import math  # noqa: E402

from whitemagic.core.consciousness.citta_vector import (  # noqa: E402
    COHERENCE_DIMS,
    VECTOR_DIM,
    CittaTrajectory,
    CittaVector,
    interpolate,
)


class TestCittaVectorConstruction:
    def test_default_vector_is_zero(self):
        vec = CittaVector()
        assert len(vec) == VECTOR_DIM
        assert all(c == 0.0 for c in vec.components)

    def test_from_scalar_coherence(self):
        vec = CittaVector.from_moment(coherence=0.8)
        sub = vec.coherence_subspace()
        assert len(sub) == 8
        assert all(abs(c - 0.8) < 1e-6 for c in sub)

    def test_from_coherence_scores(self):
        scores = {d: 0.5 + i * 0.05 for i, d in enumerate(COHERENCE_DIMS)}
        vec = CittaVector.from_moment(coherence_scores=scores)
        sub = vec.coherence_subspace()
        assert sub[0] == 0.5
        assert sub[1] == 0.55
        assert abs(sub[7] - 0.85) < 1e-6

    def test_depth_one_hot(self):
        vec = CittaVector.from_moment(depth_layer="flow")
        sub = vec.depth_subspace()
        assert sub == [0.0, 0.0, 1.0, 0.0]
        assert vec.depth_layer == "flow"

    def test_unknown_depth_defaults_surface(self):
        vec = CittaVector.from_moment(depth_layer="unknown")
        assert vec.depth_layer == "surface"

    def test_emotional_mapping(self):
        vec = CittaVector.from_moment(emotional_tone="joyful")
        assert vec.valence == 0.8
        assert vec.arousal == 0.7

    def test_unknown_emotion_defaults_neutral(self):
        vec = CittaVector.from_moment(emotional_tone="bogus")
        assert vec.valence == 0.0
        assert vec.arousal == 0.3

    def test_neuro_signals(self):
        neuro = {"composite_cognitive_load": 0.6, "composite_novelty": 0.3}
        vec = CittaVector.from_moment(neuro_signals=neuro)
        assert vec.neuro_subspace() == [0.6, 0.3]

    def test_neuro_signals_none(self):
        vec = CittaVector.from_moment()
        assert vec.neuro_subspace() == [0.0, 0.0]


class TestCittaVectorGeometry:
    def test_distance_identical_vectors(self):
        a = CittaVector.from_moment(coherence=0.8, depth_layer="surface")
        b = CittaVector.from_moment(coherence=0.8, depth_layer="surface")
        assert a.distance(b) == 0.0

    def test_distance_different_coherence(self):
        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        # 8 dims each differ by 0.5 → sqrt(8 * 0.25) = sqrt(2)
        assert abs(a.distance(b) - math.sqrt(2.0)) < 1e-6

    def test_distance_different_depth(self):
        a = CittaVector.from_moment(depth_layer="surface")
        b = CittaVector.from_moment(depth_layer="flow")
        # 2 dims differ by 1.0 (one-hot swap) → sqrt(2)
        assert abs(a.distance(b) - math.sqrt(2.0)) < 1e-6

    def test_cosine_similarity_identical(self):
        a = CittaVector.from_moment(coherence=0.8, emotional_tone="curious")
        assert a.cosine_similarity(a) == 1.0

    def test_cosine_similarity_orthogonal_depth(self):
        a = CittaVector.from_moment(depth_layer="surface")
        b = CittaVector.from_moment(depth_layer="flow")
        # Only depth one-hot differs, no overlap → similarity < 1
        sim = a.cosine_similarity(b)
        assert sim < 1.0

    def test_subspace_distance(self):
        from whitemagic.core.consciousness.citta_vector import COHERENCE_RANGE

        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        d = a.subspace_distance(b, COHERENCE_RANGE)
        assert abs(d - math.sqrt(2.0)) < 1e-6

    def test_zero_vector_cosine(self):
        a = CittaVector()
        b = CittaVector.from_moment(coherence=0.8)
        assert a.cosine_similarity(b) == 0.0


class TestCittaVectorSerialization:
    def test_to_dict_and_back(self):
        vec = CittaVector.from_moment(
            coherence=0.7,
            depth_layer="terminal",
            emotional_tone="excited",
            neuro_signals={"composite_cognitive_load": 0.4, "composite_novelty": 0.2},
        )
        d = vec.to_dict()
        assert d["depth_layer"] == "terminal"
        assert d["overall_coherence"] == 0.7
        restored = CittaVector.from_dict(d)
        assert restored.components == vec.components

    def test_from_dict_invalid(self):
        restored = CittaVector.from_dict({"components": [1.0, 2.0]})
        assert restored.components == [0.0] * VECTOR_DIM

    def test_from_dict_empty(self):
        restored = CittaVector.from_dict({})
        assert restored.components == [0.0] * VECTOR_DIM


class TestCittaTrajectory:
    def test_empty_trajectory(self):
        t = CittaTrajectory()
        assert t.velocity() == []
        assert t.avg_velocity() == 0.0
        assert t.max_velocity() == 0.0
        assert t.ignition_events() == []

    def test_single_vector_trajectory(self):
        t = CittaTrajectory()
        t.append(CittaVector.from_moment(coherence=0.8))
        assert t.velocity() == []
        assert t.avg_velocity() == 0.0

    def test_velocity_chain(self):
        t = CittaTrajectory()
        t.append(CittaVector.from_moment(coherence=0.5))
        t.append(CittaVector.from_moment(coherence=0.6))
        t.append(CittaVector.from_moment(coherence=0.7))
        vels = t.velocity()
        assert len(vels) == 2
        # Each step: 8 dims change by 0.1 → sqrt(8 * 0.01) = sqrt(0.08)
        expected = math.sqrt(0.08)
        assert abs(vels[0] - expected) < 1e-6
        assert abs(vels[1] - expected) < 1e-6

    def test_ignition_detection(self):
        t = CittaTrajectory()
        # Several small steps then a big jump
        for i in range(5):
            t.append(CittaVector.from_moment(coherence=0.5 + i * 0.01, emotional_tone="neutral"))
        t.append(CittaVector.from_moment(coherence=1.0, emotional_tone="excited"))
        ignitions = t.ignition_events(threshold=2.0)
        assert len(ignitions) >= 1
        assert ignitions[0]["position"] == 5

    def test_coherence_trajectory(self):
        t = CittaTrajectory()
        t.append(CittaVector.from_moment(coherence=0.3))
        t.append(CittaVector.from_moment(coherence=0.6))
        t.append(CittaVector.from_moment(coherence=0.9))
        ct = t.coherence_trajectory()
        assert ct == [0.3, 0.6, 0.9]

    def test_emotional_trajectory(self):
        t = CittaTrajectory()
        t.append(CittaVector.from_moment(emotional_tone="calm"))
        t.append(CittaVector.from_moment(emotional_tone="excited"))
        et = t.emotional_trajectory()
        assert len(et) == 2
        assert et[0] == (0.3, 0.1)
        assert et[1] == (0.7, 0.9)

    def test_trajectory_to_dict(self):
        t = CittaTrajectory()
        t.append(CittaVector.from_moment(coherence=0.5))
        t.append(CittaVector.from_moment(coherence=0.8))
        d = t.to_dict()
        assert d["length"] == 2
        assert len(d["vectors"]) == 2
        assert "avg_velocity" in d
        assert "ignitions" in d


class TestInterpolation:
    def test_interpolate_at_start(self):
        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        mid = interpolate(a, b, 0.0)
        assert mid.components == a.components

    def test_interpolate_at_end(self):
        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        mid = interpolate(a, b, 1.0)
        assert mid.components == b.components

    def test_interpolate_midpoint(self):
        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        mid = interpolate(a, b, 0.5)
        # Each coherence dim: (0.5 + 1.0) / 2 = 0.75
        assert abs(mid.coherence_subspace()[0] - 0.75) < 1e-6

    def test_interpolate_clamped(self):
        a = CittaVector.from_moment(coherence=0.5)
        b = CittaVector.from_moment(coherence=1.0)
        below = interpolate(a, b, -1.0)
        assert below.components == a.components
        above = interpolate(a, b, 2.0)
        assert above.components == b.components
