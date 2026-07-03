# ruff: noqa: BLE001
"""Neuro-Cognitive Sensorium — integrates all neuro-upgrade systems into citta.

Connects the 9 neuro-upgrade systems to the citta stream, creating a unified
consciousness sensorium. Each system contributes signals that modulate the
citta cycle's emotional coloring, depth layer, and coherence.

Signal flow:
    ThalamicGating → context mask → citta context_awareness
    PredictiveCoding → surprise → citta emotional_tone (novelty)
    MomentumDynamics → activation momentum → citta goal_alignment
    Neuromodulation → DA/5HT/ACh → citta emotional_attunement
    RippleTagging → ripple count → citta memory_accessibility
    ReplaySimulation → trajectory count → citta temporal_orientation
    Metaplasticity → plasticity scores → citta capability_awareness
    GlobalWorkspace → broadcast state → citta context_continuity
    SleepConsolidation → consolidation reports → citta identity_stability
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NeuroSensorium:
    """Integrates neuro-upgrade signals into a unified sensorium for citta.

    This is NOT a replacement for the existing ContextSynthesizer — it's an
    add-on that enriches the citta cycle with neuro-cognitive signals.
    """

    def __init__(self):
        self._last_update = 0.0
        self._cached_state: dict[str, Any] = {}
        self._total_updates = 0

    def compute_sensorium(self) -> dict[str, Any]:
        """Compute the full neuro-cognitive sensorium state.

        Returns a dict with signals from all 9 neuro-upgrade systems,
        normalized for injection into the citta cycle.
        """
        self._total_updates += 1
        self._last_update = time.time()

        signals: dict[str, Any] = {}

        # 1. Thalamic Gating — current context
        try:
            from whitemagic.core.memory.neuro_hotpath import get_thalamic_gating
            tg = get_thalamic_gating()
            signals["thalamic_context"] = tg.get_context()
            signals["thalamic_stats"] = tg.stats()
        except Exception as e:
            logger.debug("Thalamic gating signal failed: %s", e, exc_info=True)
            signals["thalamic_context"] = "default"

        # 2. Predictive Coding — recent surprise level
        try:
            from whitemagic.core.memory.neuro_hotpath import get_predictive_coder
            pc = get_predictive_coder()
            pc_stats = pc.stats()
            signals["predictive_surprise"] = pc_stats.get("avg_surprise", 0.0)
            signals["predictive_context_length"] = pc_stats.get("context_length", 0)
        except Exception as e:
            logger.debug("Predictive coding signal failed: %s", e, exc_info=True)
            signals["predictive_surprise"] = 0.0

        # 3. Momentum Dynamics — active node count
        try:
            from whitemagic.core.memory.neuro_hotpath import get_momentum_dynamics
            md = get_momentum_dynamics()
            md_stats = md.stats()
            signals["momentum_active_nodes"] = md_stats.get("active_nodes", 0)
            signals["momentum_total_updates"] = md_stats.get("total_updates", 0)
        except Exception as e:
            logger.debug("Momentum dynamics signal failed: %s", e, exc_info=True)
            signals["momentum_active_nodes"] = 0

        # 4. Neuromodulation — DA/5HT/ACh levels
        try:
            from whitemagic.core.memory.neuromodulation import stats as neuro_stats
            ns = neuro_stats()
            signals["neuro_da"] = ns.get("da", 0.5)
            signals["neuro_sht"] = ns.get("sht", 0.5)
            signals["neuro_ach"] = ns.get("ach", 0.5)
            signals["neuro_total_computations"] = ns.get("total_computations", 0)
        except Exception as e:
            logger.debug("Neuromodulation signal failed: %s", e, exc_info=True)
            signals["neuro_da"] = 0.5
            signals["neuro_sht"] = 0.5
            signals["neuro_ach"] = 0.5

        # 5. Ripple Tagging — tagged memory count
        try:
            from whitemagic.core.memory.ripple_tagging import stats as ripple_stats
            rs = ripple_stats()
            signals["ripple_tagged_memories"] = rs.get("tagged_memories", 0)
            signals["ripple_total_events"] = rs.get("total_events", 0)
        except Exception as e:
            logger.debug("Ripple tagging signal failed: %s", e, exc_info=True)
            signals["ripple_tagged_memories"] = 0

        # 6. Replay Simulation — trajectory count
        try:
            from whitemagic.core.memory.replay_simulation import stats as replay_stats
            rps = replay_stats()
            signals["replay_total_replays"] = rps.get("total_replays", 0)
            signals["replay_trajectories"] = rps.get("trajectories_detected", 0)
        except Exception as e:
            logger.debug("Replay simulation signal failed: %s", e, exc_info=True)
            signals["replay_total_replays"] = 0

        # 7. Metaplasticity — average plasticity
        try:
            from whitemagic.core.memory.metaplasticity import get_metaplasticity
            mp = get_metaplasticity()
            mp_stats = mp.stats()
            signals["metaplasticity_tracked"] = mp_stats.get("tracked_memories", 0)
            signals["metaplasticity_avg_threshold"] = mp_stats.get("avg_threshold", 0.5)
        except Exception as e:
            logger.debug("Metaplasticity signal failed: %s", e, exc_info=True)
            signals["metaplasticity_tracked"] = 0

        # 8. Global Workspace — current state
        try:
            from whitemagic.core.consciousness.global_workspace import (
                get_global_workspace,
            )
            gw = get_global_workspace()
            gw_state = gw.get_current_state()
            signals["workspace_modules"] = gw_state.get("total_modules", 0)
            signals["workspace_broadcasts"] = gw_state.get("total_broadcasts", 0)
            signals["workspace_latest"] = gw_state.get("latest_broadcast")
        except Exception as e:
            logger.debug("Global workspace signal failed: %s", e, exc_info=True)
            signals["workspace_modules"] = 0

        # Compute composite signals for citta integration
        signals["composite_novelty"] = self._compute_novelty(signals)
        signals["composite_stability"] = self._compute_stability(signals)
        signals["composite_attention"] = self._compute_attention(signals)
        signals["composite_cognitive_load"] = self._compute_cognitive_load(signals)

        self._cached_state = signals
        return signals

    def _compute_novelty(self, s: dict[str, Any]) -> float:
        """Novelty = high DA + high surprise + high ripple activity."""
        da = s.get("neuro_da", 0.5)
        surprise = min(s.get("predictive_surprise", 0.0) / 2.0, 1.0)
        ripple_activity = min(s.get("ripple_total_events", 0) / 100.0, 1.0)
        return (da * 0.4 + surprise * 0.4 + ripple_activity * 0.2)

    def _compute_stability(self, s: dict[str, Any]) -> float:
        """Stability = high 5HT + high metaplasticity threshold + high replay."""
        sht = s.get("neuro_sht", 0.5)
        avg_threshold = s.get("metaplasticity_avg_threshold", 0.5)
        threshold_norm = (avg_threshold - 0.1) / 1.9  # normalize to 0-1
        replay_activity = min(s.get("replay_trajectories", 0) / 50.0, 1.0)
        return (sht * 0.4 + threshold_norm * 0.3 + replay_activity * 0.3)

    def _compute_attention(self, s: dict[str, Any]) -> float:
        """Attention = high ACh + high momentum + high workspace activity."""
        ach = s.get("neuro_ach", 0.5)
        momentum = min(s.get("momentum_active_nodes", 0) / 50.0, 1.0)
        workspace = min(s.get("workspace_broadcasts", 0) / 100.0, 1.0)
        return (ach * 0.5 + momentum * 0.3 + workspace * 0.2)

    def _compute_cognitive_load(self, s: dict[str, Any]) -> float:
        """Cognitive load = combination of all active systems."""
        load = 0.0
        load += min(s.get("momentum_active_nodes", 0) / 100.0, 0.3)
        load += min(s.get("ripple_tagged_memories", 0) / 200.0, 0.2)
        load += min(s.get("metaplasticity_tracked", 0) / 500.0, 0.2)
        load += min(s.get("replay_total_replays", 0) / 100.0, 0.15)
        load += min(s.get("workspace_broadcasts", 0) / 50.0, 0.15)
        return min(load, 1.0)

    def get_citta_enrichment(self) -> dict[str, float]:
        """Get citta-relevant enrichment signals (for the citta cycle).

        Maps neuro-cognitive signals to the 8 coherence dimensions:
        - memory_accessibility: ripple + metaplasticity
        - identity_stability: stability composite
        - context_continuity: workspace + thalamic
        - relationship_awareness: global workspace modules
        - temporal_orientation: replay trajectories
        - capability_awareness: metaplasticity plasticity
        - emotional_attunement: neuromodulation DA/5HT/ACh
        - goal_alignment: momentum + attention
        """
        s = self._cached_state or self.compute_sensorium()

        return {
            "memory_accessibility": min(
                (s.get("ripple_tagged_memories", 0) / 100.0) * 0.5 +
                (1.0 - s.get("metaplasticity_avg_threshold", 0.5)) * 0.5,
                1.0
            ),
            "identity_stability": s.get("composite_stability", 0.5),
            "context_continuity": min(
                (s.get("workspace_modules", 0) / 10.0) * 0.5 +
                (1.0 if s.get("thalamic_context") != "default" else 0.5) * 0.5,
                1.0
            ),
            "relationship_awareness": min(s.get("workspace_modules", 0) / 10.0, 1.0),
            "temporal_orientation": min(s.get("replay_trajectories", 0) / 20.0, 1.0),
            "capability_awareness": 1.0 - min(s.get("metaplasticity_avg_threshold", 0.5) / 2.0, 1.0),
            "emotional_attunement": (
                s.get("neuro_da", 0.5) * 0.3 +
                s.get("neuro_sht", 0.5) * 0.3 +
                s.get("neuro_ach", 0.5) * 0.4
            ),
            "goal_alignment": s.get("composite_attention", 0.5),
            "cognitive_load": s.get("composite_cognitive_load", 0.0),
            "novelty": s.get("composite_novelty", 0.5),
        }

    def stats(self) -> dict[str, Any]:
        return {
            "total_updates": self._total_updates,
            "last_update": self._last_update,
            "signals_tracked": len(self._cached_state),
        }


# Singleton

_sensorium: NeuroSensorium | None = None


def get_neuro_sensorium() -> NeuroSensorium:
    global _sensorium
    if _sensorium is None:
        _sensorium = NeuroSensorium()
    return _sensorium
