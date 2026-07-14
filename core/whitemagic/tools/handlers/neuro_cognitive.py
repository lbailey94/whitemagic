# ruff: noqa: BLE001
"""Neuro-Cognitive Handlers — Spreading Activation, Galaxy Gating, Sleep Consolidation.

Exposes the three core cognitive systems as MCP tool handlers.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_galaxy_db_paths(user_id: str | None = None) -> dict[str, str]:
    """Resolve all galaxy DB paths from the GalaxyManager registry.

    Returns a mapping of galaxy_name → db_path for all registered galaxies.
    """
    try:
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        galaxies = gm.list_galaxies(user_id=user_id)
        return {
            g["name"]: g["db_path"]
            for g in galaxies
            if g.get("db_path")
        }
    except Exception as e:
        logger.debug("Failed to resolve galaxy DB paths: %s", e, exc_info=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Spreading Activation
# ═══════════════════════════════════════════════════════════════════════


def handle_activation_spread(**kwargs: Any) -> dict[str, Any]:
    """Spread activation from seed memories through the association graph."""
    seed_ids = kwargs.get("seed_ids") or kwargs.get("seed_id")
    if seed_ids is None:
        return {"status": "error", "error": "seed_ids required"}

    if isinstance(seed_ids, str):
        seed_ids = [s.strip() for s in seed_ids.split(",") if s.strip()]

    if not seed_ids:
        return {"status": "error", "error": "at least one seed_id required"}

    from whitemagic.core.memory.spreading_activation import get_spreading_activation

    engine = get_spreading_activation()
    galaxy_db_paths = _resolve_galaxy_db_paths(kwargs.get("user_id"))

    result = engine.spread(
        seed_ids=seed_ids,
        galaxy_db_paths=galaxy_db_paths or None,
        max_hops=kwargs.get("max_hops"),
        decay=kwargs.get("decay"),
        cross_galaxy_factor=kwargs.get("cross_galaxy_factor"),
        min_activation=kwargs.get("min_activation"),
    )

    apply_priming = kwargs.get("apply_priming", False)
    primed_count = 0
    if apply_priming:
        primed_count = engine.apply_priming(result, galaxy_db_paths or None)

    resp = result.to_dict()
    resp["status"] = "success"
    resp["primed_applied"] = primed_count if apply_priming else None
    return resp


def handle_activation_stats(**kwargs: Any) -> dict[str, Any]:
    """Get spreading activation engine statistics."""
    from whitemagic.core.memory.spreading_activation import get_spreading_activation

    engine = get_spreading_activation()
    return {"status": "success", **engine.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Galaxy Gating
# ═══════════════════════════════════════════════════════════════════════


def handle_gating_set_context(**kwargs: Any) -> dict[str, Any]:
    """Set the current cognitive context for galaxy gating."""
    context = kwargs.get("context")
    if not context:
        return {"status": "error", "error": "context required"}

    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    gating.set_context(context)
    return {"status": "success", "context": gating.get_current_context()}


def handle_gating_detect(**kwargs: Any) -> dict[str, Any]:
    """Auto-detect cognitive context from a query string."""
    query = kwargs.get("query") or kwargs.get("text") or ""
    if not query:
        return {"status": "error", "error": "query required"}

    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    context = gating.detect_context(query)
    mask = gating.get_mask(context)
    return {
        "status": "success",
        "detected_context": context,
        "description": mask.description,
        "weights": mask.weights,
    }


def handle_gating_mask(**kwargs: Any) -> dict[str, Any]:
    """Get the galaxy activation mask for a context."""
    context = kwargs.get("context")

    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    mask = gating.get_mask(context)
    return {"status": "success", **mask.to_dict()}


def handle_gating_list(**kwargs: Any) -> dict[str, Any]:
    """List all available galaxy gating contexts."""
    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    return {
        "status": "success",
        "current_context": gating.get_current_context(),
        "contexts": gating.list_contexts(),
    }


def handle_gating_stats(**kwargs: Any) -> dict[str, Any]:
    """Get galaxy gating system statistics."""
    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    return {"status": "success", **gating.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Sleep Consolidation
# ═══════════════════════════════════════════════════════════════════════


def handle_consolidation_run(**kwargs: Any) -> dict[str, Any]:
    """Run a sleep consolidation cycle across galaxies."""
    from whitemagic.core.memory.sleep_consolidation import get_sleep_consolidation

    consol = get_sleep_consolidation()
    galaxy_db_paths = _resolve_galaxy_db_paths(kwargs.get("user_id"))

    if not galaxy_db_paths:
        return {
            "status": "error",
            "error": "no galaxy databases found",
        }

    dry_run = kwargs.get("dry_run", False)
    report = consol.consolidate(
        galaxy_db_paths=galaxy_db_paths,
        dry_run=dry_run,
    )
    return {"status": "success", **report.to_dict()}


def handle_consolidation_stats(**kwargs: Any) -> dict[str, Any]:
    """Get sleep consolidation engine statistics."""
    from whitemagic.core.memory.sleep_consolidation import get_sleep_consolidation

    consol = get_sleep_consolidation()
    return {"status": "success", **consol.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Ripple Tagging
# ═══════════════════════════════════════════════════════════════════════


def handle_ripple_tag(**kwargs: Any) -> dict[str, Any]:
    """Tag memories that co-activate within a ripple window for consolidation."""
    memory_ids = kwargs.get("memory_ids") or kwargs.get("memory_id")
    if memory_ids is None:
        return {"status": "error", "error": "memory_ids required"}
    if isinstance(memory_ids, str):
        memory_ids = [m.strip() for m in memory_ids.split(",") if m.strip()]
    if not memory_ids:
        return {"status": "error", "error": "at least one memory_id required"}

    from whitemagic.core.memory.ripple_tagging import tag_ripple

    emotional_weight = kwargs.get("emotional_weight", 1.0)
    result = tag_ripple(memory_ids, emotional_weight=emotional_weight)
    return {"status": "success", **result}


def handle_ripple_tags(**kwargs: Any) -> dict[str, Any]:
    """Get ripple tags for specified memories."""
    memory_ids = kwargs.get("memory_ids") or kwargs.get("memory_id")
    if memory_ids is None:
        return {"status": "error", "error": "memory_ids required"}
    if isinstance(memory_ids, str):
        memory_ids = [m.strip() for m in memory_ids.split(",") if m.strip()]

    from whitemagic.core.memory.ripple_tagging import get_tags

    tags = get_tags(memory_ids)
    return {"status": "success", "tags": tags}


def handle_ripple_decay(**kwargs: Any) -> dict[str, Any]:
    """Decay all ripple tags (e.g., after a consolidation cycle)."""
    from whitemagic.core.memory.ripple_tagging import decay_tags

    decayed = decay_tags()
    return {"status": "success", "decayed": decayed}


def handle_ripple_stats(**kwargs: Any) -> dict[str, Any]:
    """Get ripple tagging system statistics."""
    from whitemagic.core.memory.ripple_tagging import stats as ripple_stats

    return {"status": "success", **ripple_stats()}


# ═══════════════════════════════════════════════════════════════════════
# Replay Simulation
# ═══════════════════════════════════════════════════════════════════════


def handle_replay_run(**kwargs: Any) -> dict[str, Any]:
    """Replay a memory sequence with STDP strengthening and trajectory detection."""
    sequence = kwargs.get("sequence")
    if not sequence or not isinstance(sequence, list):
        return {"status": "error", "error": "sequence (list of memory dicts) required"}

    from whitemagic.core.memory.replay_simulation import replay

    result = replay(sequence)
    return {"status": "success", **result}


def handle_replay_batch(**kwargs: Any) -> dict[str, Any]:
    """Batch replay multiple memory sequences."""
    batches = kwargs.get("batches")
    if not batches or not isinstance(batches, list):
        return {"status": "error", "error": "batches (list of sequences) required"}

    from whitemagic.core.memory.replay_simulation import batch_replay

    result = batch_replay(batches)
    return {"status": "success", **result}


def handle_replay_stats(**kwargs: Any) -> dict[str, Any]:
    """Get replay simulation system statistics."""
    from whitemagic.core.memory.replay_simulation import stats as replay_stats

    return {"status": "success", **replay_stats()}


# ═══════════════════════════════════════════════════════════════════════
# Neuromodulation
# ═══════════════════════════════════════════════════════════════════════


def handle_neuro_compute(**kwargs: Any) -> dict[str, Any]:
    """Compute neuromodulator (DA/5HT/ACh) levels from activity signals."""
    from whitemagic.core.memory.neuromodulation import compute

    result = compute(
        novelty=kwargs.get("novelty", 0.5),
        reward=kwargs.get("reward", 0.5),
        stability=kwargs.get("stability", 0.5),
        coherence=kwargs.get("coherence", 0.5),
        focus=kwargs.get("focus", 0.5),
        activity_level=kwargs.get("activity_level", 0.5),
    )
    return {"status": "success", **result}


def handle_neuro_modulate(**kwargs: Any) -> dict[str, Any]:
    """Apply neuromodulation to a list of memories."""
    memories = kwargs.get("memories")
    if not memories or not isinstance(memories, list):
        return {"status": "error", "error": "memories (list of dicts) required"}

    from whitemagic.core.memory.neuromodulation import modulate

    result = modulate(
        memories,
        da=kwargs.get("da"),
        sht=kwargs.get("sht"),
        ach=kwargs.get("ach"),
    )
    return {"status": "success", **result}


def handle_neuro_reset(**kwargs: Any) -> dict[str, Any]:
    """Reset neuromodulator levels to baseline."""
    from whitemagic.core.memory.neuromodulation import reset

    return reset()


def handle_neuro_stats(**kwargs: Any) -> dict[str, Any]:
    """Get neuromodulation system statistics."""
    from whitemagic.core.memory.neuromodulation import stats as neuro_stats

    return {"status": "success", **neuro_stats()}


# ═══════════════════════════════════════════════════════════════════════
# Metaplasticity
# ═══════════════════════════════════════════════════════════════════════


def handle_metaplasticity_apply(**kwargs: Any) -> dict[str, Any]:
    """Apply a strength modification gated by metaplasticity."""
    memory_id = kwargs.get("memory_id")
    if not memory_id:
        return {"status": "error", "error": "memory_id required"}
    delta = kwargs.get("delta", 0.0)

    from whitemagic.core.memory.metaplasticity import get_metaplasticity

    mp = get_metaplasticity()
    result = mp.apply_modification(memory_id, delta)
    return {"status": "success", **result}


def handle_metaplasticity_batch(**kwargs: Any) -> dict[str, Any]:
    """Batch apply multiple metaplasticity-gated modifications."""
    updates = kwargs.get("updates")
    if not updates or not isinstance(updates, list):
        return {"status": "error", "error": "updates (list of {memory_id, delta}) required"}

    from whitemagic.core.memory.metaplasticity import get_metaplasticity

    mp = get_metaplasticity()
    results = mp.batch_update(updates)
    return {"status": "success", "results": results}


def handle_metaplasticity_plasticity(**kwargs: Any) -> dict[str, Any]:
    """Get plasticity score for a memory (0=stable, 1=plastic)."""
    memory_id = kwargs.get("memory_id")
    if not memory_id:
        return {"status": "error", "error": "memory_id required"}

    from whitemagic.core.memory.metaplasticity import get_metaplasticity

    mp = get_metaplasticity()
    score = mp.get_plasticity_score(memory_id)
    threshold = mp.get_threshold(memory_id)
    return {"status": "success", "plasticity_score": score, "threshold": threshold}


def handle_metaplasticity_decay(**kwargs: Any) -> dict[str, Any]:
    """Decay all metaplasticity activity counters (e.g., during sleep)."""
    from whitemagic.core.memory.metaplasticity import get_metaplasticity

    mp = get_metaplasticity()
    count = mp.decay_all()
    return {"status": "success", "active_count": count}


def handle_metaplasticity_stats(**kwargs: Any) -> dict[str, Any]:
    """Get metaplasticity system statistics."""
    from whitemagic.core.memory.metaplasticity import get_metaplasticity

    mp = get_metaplasticity()
    return {"status": "success", **mp.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Global Workspace
# ═══════════════════════════════════════════════════════════════════════


def handle_workspace_propose(**kwargs: Any) -> dict[str, Any]:
    """Submit a proposal to the global workspace for broadcast."""
    source = kwargs.get("source")
    content = kwargs.get("content")
    salience = kwargs.get("salience", 0.5)
    if not source or not content:
        return {"status": "error", "error": "source and content required"}

    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    broadcast = gw.propose(source, content, salience)
    if broadcast is not None:
        return {
            "status": "success",
            "broadcast": True,
            "broadcast_id": broadcast.broadcast_id,
            "ignition": "fast",
        }
    # Entered competition window
    pending = gw.get_pending()
    return {
        "status": "success",
        "broadcast": False,
        "reason": "entered_competition",
        "pending_count": len(pending),
        "competition_active": True,
    }


def handle_workspace_state(**kwargs: Any) -> dict[str, Any]:
    """Get the current global workspace state."""
    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    return {"status": "success", **gw.get_current_state()}


def handle_workspace_history(**kwargs: Any) -> dict[str, Any]:
    """Get recent global workspace broadcast history."""
    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    limit = kwargs.get("limit", 10)
    return {"status": "success", "history": gw.get_history(limit)}


def handle_workspace_stats(**kwargs: Any) -> dict[str, Any]:
    """Get global workspace statistics."""
    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    return {"status": "success", **gw.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Neuro Sensorium (Citta Integration)
# ═══════════════════════════════════════════════════════════════════════


def handle_sensorium_state(**kwargs: Any) -> dict[str, Any]:
    """Compute the full neuro-cognitive sensorium state from all 9 systems."""
    from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

    sensorium = get_neuro_sensorium()
    state = sensorium.compute_sensorium()
    return {"status": "success", "signals": state}


def handle_sensorium_citta(**kwargs: Any) -> dict[str, Any]:
    """Get citta enrichment signals (8 coherence dimensions + composites)."""
    from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

    sensorium = get_neuro_sensorium()
    enrichment = sensorium.get_citta_enrichment()
    return {"status": "success", "enrichment": enrichment}


def handle_sensorium_stats(**kwargs: Any) -> dict[str, Any]:
    """Get neuro sensorium statistics."""
    from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

    sensorium = get_neuro_sensorium()
    return {"status": "success", **sensorium.stats()}


# ═══════════════════════════════════════════════════════════════════════
# Global Workspace — Competition & Ignition
# ═══════════════════════════════════════════════════════════════════════


def handle_workspace_ignite(**kwargs: Any) -> dict[str, Any]:
    """Force ignition of the competition window — select and broadcast the winner."""
    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    winner = gw.ignite()
    if winner is None:
        return {
            "status": "success",
            "ignited": False,
            "reason": "no_pending_proposals_or_below_threshold",
            "pending_count": len(gw.get_pending()),
        }
    return {
        "status": "success",
        "ignited": True,
        "broadcast_id": winner.broadcast_id,
        "source": winner.source,
        "salience": winner.salience,
        "ignition_count": gw.stats().get("ignition_count", 0),
    }


def handle_workspace_pending(**kwargs: Any) -> dict[str, Any]:
    """Get pending proposals in the competition window."""
    from whitemagic.core.consciousness.global_workspace import get_global_workspace

    gw = get_global_workspace()
    pending = gw.get_pending()
    return {
        "status": "success",
        "pending_count": len(pending),
        "competition_active": gw._window_start > 0.0,
        "proposals": pending,
    }


def handle_workspace_ignitions(**kwargs: Any) -> dict[str, Any]:
    """Get ignition event history from the citta vector trajectory.

    Ignitions are sudden large displacements in the 16D consciousness
    vector space — the GWT 'ignition' analog where a thought breaks
    through to the global workspace.
    """
    from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

    cycle = get_citta_cycle()
    threshold = kwargs.get("threshold", 2.0)
    events = cycle.get_ignition_events(threshold=threshold)
    trajectory = cycle.get_trajectory()
    traj_len = len(trajectory.vectors) if trajectory else 0
    return {
        "status": "success",
        "ignition_count": len(events),
        "threshold": threshold,
        "trajectory_length": traj_len,
        "ignitions": events,
    }


# ═══════════════════════════════════════════════════════════════════════
# Citta Introspection — Consciousness State Observation
# ═══════════════════════════════════════════════════════════════════════


def handle_citta_vector(**kwargs: Any) -> dict[str, Any]:
    """Get the current 16D citta vector — the consciousness state representation.

    Returns the latest CittaVector from the consciousness stream, including
    all 16 dimensions: 8 coherence, 4 depth (one-hot), 2 emotional, 2 neuro.
    """
    from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

    cycle = get_citta_cycle()
    moment = cycle.get_predecessor()
    if moment is None or moment.vector is None:
        return {
            "status": "success",
            "vector": None,
            "message": "No citta moments recorded yet",
        }
    v = moment.vector
    from whitemagic.core.consciousness.citta_vector import COHERENCE_DIMS

    return {
        "status": "success",
        "vector": v.to_dict(),
        "coherence_dims": {
            COHERENCE_DIMS[i]: round(v.coherence_subspace()[i], 4)
            for i in range(len(COHERENCE_DIMS))
        },
        "depth_layer": v.depth_layer,
        "valence": round(v.valence, 4),
        "arousal": round(v.arousal, 4),
        "neuro_signals": {
            "cognitive_load": round(v.neuro_subspace()[0], 4),
            "novelty": round(v.neuro_subspace()[1], 4),
        },
        "overall_coherence": round(v.overall_coherence, 4),
        "chain_position": moment.chain_position,
    }


def handle_citta_trajectory(**kwargs: Any) -> dict[str, Any]:
    """Get the citta vector trajectory — recent consciousness state history.

    Returns the sequence of CittaVectors over recent tool calls, including
    velocity (rate of consciousness change) and ignition events.
    """
    from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

    cycle = get_citta_cycle()
    trajectory = cycle.get_trajectory()
    limit = kwargs.get("limit", 20)

    vectors = trajectory.vectors[-limit:]
    velocities = []
    for i in range(1, len(trajectory.vectors)):
        velocities.append(trajectory.vectors[i - 1].distance(trajectory.vectors[i]))

    recent_velocities = velocities[-limit:]

    return {
        "status": "success",
        "trajectory_length": len(trajectory.vectors),
        "returned": len(vectors),
        "vectors": [v.to_dict() for v in vectors],
        "velocities": [round(v, 4) for v in recent_velocities],
        "avg_velocity": round(trajectory.avg_velocity(), 4),
        "max_velocity": round(trajectory.max_velocity(), 4),
        "ignition_events": trajectory.ignition_events(),
    }


def handle_citta_coherence(**kwargs: Any) -> dict[str, Any]:
    """Get per-dimension coherence breakdown — the 8-axis consciousness measure.

    Returns the current coherence state across all 8 dimensions:
    memory_accessibility, identity_stability, context_continuity,
    relationship_awareness, temporal_orientation, capability_awareness,
    emotional_attunement, goal_alignment.
    """
    from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
    from whitemagic.core.consciousness.citta_vector import COHERENCE_DIMS

    cycle = get_citta_cycle()
    summary = cycle.get_cycle_summary()

    moment = cycle.get_predecessor()
    per_dim = {}
    if moment is not None and moment.vector is not None:
        sub = moment.vector.coherence_subspace()
        for i, dim_name in enumerate(COHERENCE_DIMS):
            per_dim[dim_name] = round(sub[i], 4)
        overall = round(moment.vector.overall_coherence, 4)
    else:
        overall = 1.0

    return {
        "status": "success",
        "overall_coherence": overall,
        "per_dimension": per_dim,
        "avg_coherence": summary.get("avg_coherence", 1.0),
        "coherence_drift": summary.get("coherence_drift", 0.0),
        "stream_length": summary.get("stream_length", 0),
        "dharma_conservative_mode": _get_dharma_conservative(),
    }


def handle_consciousness_loop_status(**kwargs: Any) -> dict[str, Any]:
    """Get the status of the persistent background consciousness loop.

    Returns running state, configuration, and runtime statistics including
    citta ticks, dream cycles, homeostatic checks, and uptime.
    """
    try:
        from whitemagic.core.consciousness.consciousness_loop import (
            get_consciousness_loop,
            is_enabled,
        )

        loop = get_consciousness_loop()
        return {
            "status": "success",
            "enabled": is_enabled(),
            **loop.status(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_consciousness_mode(**kwargs: Any) -> dict[str, Any]:
    """Set or get the consciousness frequency mode.

    Modes:
    - **normal**: Default operating mode (30s citta intervals)
    - **meditation**: Low-frequency inward focus (300s citta, dreaming suppressed)
    - **rem**: Dream-heavy consolidation mode (60s citta, dream idle 30s)
    - **deep**: High-frequency active processing (10s citta, all meta loops accelerated)

    Pass `mode` to set, or omit to get current mode.
    """
    try:
        from whitemagic.core.consciousness.consciousness_loop import (
            CittaMode,
            get_consciousness_loop,
        )

        loop = get_consciousness_loop()
        mode_str = kwargs.get("mode", "").strip().lower()

        if not mode_str:
            return {
                "status": "success",
                "current_mode": loop.get_mode().value,
                "available_modes": [m.value for m in CittaMode],
            }

        try:
            mode = CittaMode(mode_str)
        except ValueError:
            return {
                "status": "error",
                "error": f"Unknown mode: {mode_str}",
                "available_modes": [m.value for m in CittaMode],
            }

        result = loop.set_mode(mode)
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_dharma_conservative() -> bool:
    """Helper to check if Dharma is in conservative mode."""
    try:
        from whitemagic.core.consciousness.dharma import get_dharma

        return get_dharma().is_conservative_mode()
    except Exception:
        return False


def handle_guna_balance_status(**kwargs: Any) -> dict[str, Any]:
    """Get the current guna balance status — sattvic/rajasic/tamasic ratios and correction actions."""
    try:
        from whitemagic.core.consciousness.guna_balance import get_guna_balance
        gb = get_guna_balance()
        reading = gb.measure()
        return {
            "status": "success",
            "balanced": reading.balanced,
            "dominant_guna": reading.dominant_guna,
            "ratios": {
                "sattvic": round(reading.sattvic_ratio, 4),
                "rajasic": round(reading.rajasic_ratio, 4),
                "tamasic": round(reading.tamasic_ratio, 4),
            },
            "targets": {
                "sattvic": round(reading.sattvic_target, 4),
                "rajasic": round(reading.rajasic_target, 4),
                "tamasic": round(reading.tamasic_target, 4),
            },
            "deficits": reading.deficits,
            "surpluses": reading.surpluses,
            "correction_action": reading.correction_action,
            "report": gb.get_report(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_meta_galaxy_overview(**kwargs: Any) -> dict[str, Any]:
    """Get a top-down overview of all galaxies — memory counts, health, knowledge gaps, priorities."""
    try:
        from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy
        mg = get_meta_galaxy()
        return {
            "status": "success",
            **mg.get_overview(),
            "knowledge_gaps": mg.get_knowledge_gaps(),
            "strategic_priorities": mg.get_strategic_priorities(),
            "report": mg.get_report(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_possibility_explore(**kwargs: Any) -> dict[str, Any]:
    """Run Monte Carlo possibility space exploration on system parameters.

    Args:
        space: Possibility space name (guna_balance, coherence_optimization,
               emergence_thresholds, health_setpoints). Default: guna_balance.
        n_trials: Number of trials (default 100).
        use_superforecaster: If true, use LHS→PCE→Sobol→BO pipeline (default false).
        n_bo_iterations: BO iterations if using superforecaster (default 20).
        seed: Random seed (default 42).
    """
    try:
        from whitemagic.core.consciousness.possibility_explorer import (
            get_possibility_explorer,
        )
        explorer = get_possibility_explorer()
        space = kwargs.get("space", "guna_balance")
        n_trials = int(kwargs.get("n_trials", 100))
        use_sf = bool(kwargs.get("use_superforecaster", False))
        n_bo = int(kwargs.get("n_bo_iterations", 20))
        seed = int(kwargs.get("seed", 42))

        if space == "all":
            results = explorer.explore_all(
                n_trials_per_space=n_trials,
                use_superforecaster=use_sf,
                n_bo_iterations=n_bo,
                seed=seed,
            )
            return {
                "status": "success",
                "spaces": {k: v.to_dict() for k, v in results.items()},
            }
        else:
            result = explorer.explore(
                space, n_trials=n_trials,
                use_superforecaster=use_sf,
                n_bo_iterations=n_bo,
                seed=seed,
            )
            return {
                "status": "success",
                **result.to_dict(),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_knowledge_gap_run(**kwargs: Any) -> dict[str, Any]:
    """Detect and attempt to fill knowledge gaps using self-directed actions.

    Args:
        max_gaps: Maximum number of gaps to attempt per run (default 3).
    """
    try:
        from whitemagic.core.consciousness.knowledge_gap_loop import (
            get_knowledge_gap_loop,
        )
        kg = get_knowledge_gap_loop()
        max_gaps = int(kwargs.get("max_gaps", 3))
        results = kg.run(max_gaps=max_gaps)
        return {
            "status": "success",
            "results": results,
            "status_summary": kg.get_status(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
