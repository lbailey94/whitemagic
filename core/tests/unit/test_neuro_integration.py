"""Integration test: all 9 neuro-upgrade systems working together."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_neuro_int_"))
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")


def test_full_cognitive_cycle():
    from whitemagic.core.memory.neuro_hotpath import get_thalamic_gating
    tg = get_thalamic_gating()
    tg.set_context("coding")
    weights = tg.compute_weights(["codex", "citta", "universal"])
    assert weights["codex"] > weights["citta"]

    from whitemagic.core.memory.neuro_hotpath import get_predictive_coder
    pc = get_predictive_coder()
    pc.reset()
    surprise = pc.process([0.8, 0.2, 0.1, 0.0] * 32)
    assert surprise >= 0.0
    novelty = pc.novelty_score(surprise)
    assert 0.0 <= novelty <= 1.0

    from whitemagic.core.memory.neuromodulation import compute, modulate, reset
    reset()
    neuro = compute(novelty=novelty, reward=0.7, stability=0.6, coherence=0.8, focus=0.9, activity_level=0.5)
    assert 0 <= neuro["da"] <= 1.0

    from whitemagic.core.memory.ripple_tagging import tag_ripple, get_tags
    ripple_result = tag_ripple(["mem-1", "mem-2", "mem-3"], emotional_weight=1.5)
    assert ripple_result["tagged"] is True

    from whitemagic.core.memory.neuro_hotpath import get_momentum_dynamics
    md = get_momentum_dynamics()
    md.reset()
    md.update({"mem-1": 0.8, "mem-2": 0.6, "mem-3": 0.4})
    boosted = md.apply_momentum([("mem-1", 0.5), ("mem-4", 0.3)])
    mem1_score = [s for n, s in boosted if n == "mem-1"][0]
    mem4_score = [s for n, s in boosted if n == "mem-4"][0]
    assert mem1_score > mem4_score

    from whitemagic.core.memory.metaplasticity import get_metaplasticity
    mp = get_metaplasticity()
    mod_result = mp.apply_modification("mem-1", 0.3)
    assert "applied_delta" in mod_result

    from whitemagic.core.memory.replay_simulation import replay
    replay_result = replay([
        {"memory_id": "mem-1", "timestamp": 0.0, "importance": 0.8},
        {"memory_id": "mem-2", "timestamp": 3.0, "importance": 0.7},
        {"memory_id": "mem-3", "timestamp": 7.0, "importance": 0.9},
    ])
    assert replay_result["total_items"] == 3

    from whitemagic.core.consciousness.global_workspace import get_global_workspace
    gw = get_global_workspace()
    received = []
    gw.register("citta-listener", lambda b: received.append(b))
    broadcast = gw.propose("neuro-cycle", {
        "surprise": surprise, "novelty": novelty, "da": neuro["da"],
    }, salience=0.8)
    assert broadcast is not None
    assert len(received) == 1

    from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium
    sensorium = get_neuro_sensorium()
    state = sensorium.compute_sensorium()
    enrichment = sensorium.get_citta_enrichment()

    for dim in ["memory_accessibility", "identity_stability", "context_continuity",
                "relationship_awareness", "temporal_orientation", "capability_awareness",
                "emotional_attunement", "goal_alignment"]:
        assert dim in enrichment
        assert 0.0 <= enrichment[dim] <= 1.0

    assert 0.0 <= state["composite_novelty"] <= 1.0
    assert 0.0 <= state["composite_stability"] <= 1.0
    assert 0.0 <= state["composite_attention"] <= 1.0
    assert 0.0 <= state["composite_cognitive_load"] <= 1.0


def test_neuro_sensorium_reflects_activity():
    from whitemagic.core.memory.neuro_hotpath import get_thalamic_gating
    from whitemagic.core.memory.neuromodulation import compute, reset
    from whitemagic.core.memory.ripple_tagging import tag_ripple
    from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

    tg = get_thalamic_gating()
    tg.set_context("introspection")
    reset()
    compute(novelty=0.9, reward=0.8, stability=0.7, coherence=0.8, focus=0.9)
    tag_ripple(["s1", "s2", "s3"], emotional_weight=1.5)

    sensorium = get_neuro_sensorium()
    state = sensorium.compute_sensorium()

    assert state["thalamic_context"] == "introspection"
    assert state["ripple_total_events"] > 0
    assert state["neuro_da"] > 0.3
