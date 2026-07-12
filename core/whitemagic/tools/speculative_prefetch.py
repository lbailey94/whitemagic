"""Speculative Prefetch — Predict Next Tool, Pre-warm Pipeline (v14).
===================================================================
After each PRAT call, predicts the most likely next Gana based on
observed transition patterns (simple Markov chain), and pre-warms
the retrieval pipeline for that Gana's top tools in a background thread.

When the predicted tool is actually called, the result is served from
cache — achieving "negative latency" for common tool sequences.

Architecture:
  1. record_transition(from_gana, to_gana) — updates transition counts
  2. predict_next(current_gana) -> list[str] — top-K predicted next Ganas
  3. prefetch_for_gana(gana_name) — runs retrieval pipeline for top tools
  4. get_cached(tool_name) -> result | None — returns prefetched result

Cache is invalidated after a configurable TTL (default 5s) to avoid stale data.
"""
# ruff: noqa: BLE001

import json
import logging
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from whitemagic.config.paths import CACHE_DIR

logger = logging.getLogger(__name__)

_DEFAULT_TRANSITIONS_PATH = CACHE_DIR / "gana_transitions.json"


class TransitionTracker:
    """Tracks Gana→Gana transition frequencies for prediction."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._state_path = state_path or _DEFAULT_TRANSITIONS_PATH
        # transitions[from_gana][to_gana] = count
        self._transitions: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._total_from: dict[str, int] = defaultdict(int)
        self._record_count = 0
        self._save_interval = 50
        self.load_state()

    def record(self, from_gana: str, to_gana: str) -> None:
        """Record a transition from one Gana to another."""
        with self._lock:
            self._transitions[from_gana][to_gana] += 1
            self._total_from[from_gana] += 1
            self._record_count += 1
            if self._record_count % self._save_interval == 0:
                self._save_state_unlocked()

    def predict(self, current_gana: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Predict top-K most likely next Ganas with probabilities.

        Returns list of (gana_name, probability) sorted by probability desc.
        """
        with self._lock:
            counts = self._transitions.get(current_gana, {})
            total = self._total_from.get(current_gana, 0)
            if total == 0:
                return []

            ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            return [(gana, count / total) for gana, count in ranked[:top_k]]

    def stats(self) -> dict[str, Any]:
        """Get transition tracker statistics."""
        with self._lock:
            total_transitions = sum(self._total_from.values())
            unique_from = len(self._transitions)
            return {
                "total_transitions": total_transitions,
                "unique_source_ganas": unique_from,
                "top_transitions": self._top_transitions(5),
            }

    def _top_transitions(self, n: int) -> list[dict[str, Any]]:
        """Get the N most frequent transitions."""
        all_transitions: list[dict[str, int | str]] = []
        for from_g, targets in self._transitions.items():
            for to_g, count in targets.items():
                all_transitions.append(
                    {
                        "from": from_g,
                        "to": to_g,
                        "count": count,
                    }
                )

        def _count_key(item: dict[str, int | str]) -> int:
            count = item.get("count")
            return count if isinstance(count, int) else 0

        all_transitions.sort(
            key=_count_key,
            reverse=True,
        )
        return all_transitions[:n]

    def save_state(self) -> None:
        """Persist transitions to disk."""
        with self._lock:
            self._save_state_unlocked()

    def _save_state_unlocked(self) -> None:
        """Save state without acquiring lock (caller must hold lock)."""
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "transitions": {
                    k: dict(v) for k, v in self._transitions.items()
                },
                "total_from": dict(self._total_from),
            }
            self._state_path.write_text(json.dumps(state))
        except Exception as e:
            logger.warning("Failed to save transition state: %s", e, exc_info=True)

    def load_state(self) -> None:
        """Restore transitions from disk."""
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            state = json.loads(self._state_path.read_text())
            raw_transitions = state.get("transitions", {})
            self._transitions = defaultdict(lambda: defaultdict(int))
            for from_g, targets in raw_transitions.items():
                for to_g, count in targets.items():
                    self._transitions[from_g][to_g] = int(count)
            raw_totals = state.get("total_from", {})
            self._total_from = defaultdict(int)
            for gana, total in raw_totals.items():
                self._total_from[gana] = int(total)
            logger.info(
                "Restored transition state: %s source Ganas, %s total transitions",
                len(self._transitions),
                sum(self._total_from.values()),
            )
        except Exception as e:
            logger.warning("Failed to load transition state: %s", e, exc_info=True)


class PrefetchCache:
    """TTL-based cache for prefetched tool results."""

    def __init__(self, ttl_seconds: float = 5.0) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[Any, float]] = {}  # key -> (result, expire_time)
        self._hits = 0
        self._misses = 0
        self._ttl = ttl_seconds

    def put(self, key: str, result: Any) -> None:
        """Store a prefetched result."""
        with self._lock:
            self._cache[key] = (result, time.monotonic() + self._ttl)

    def get(self, key: str) -> Any | None:
        """Get a prefetched result if it exists and hasn't expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            result, expire_time = entry
            if time.monotonic() > expire_time:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return result

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate a specific key or all keys."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """
        Perform the stats operation.

        Returns:
            dict[str, Any]
        """
        with self._lock:
            return {
                "cached_items": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(1, self._hits + self._misses), 4),
                "ttl_seconds": self._ttl,
            }


# Tool-to-Gana reverse mapping (lazy loaded)
_GANA_TOOLS: dict[str, list[str]] | None = None


def _get_gana_tools() -> dict[str, list[str]]:
    """Build Gana→[tools] reverse mapping from PRAT router."""
    global _GANA_TOOLS
    if _GANA_TOOLS is not None:
        return _GANA_TOOLS
    try:
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        gana_tools: dict[str, list[str]] = defaultdict(list)
        for tool, gana in TOOL_TO_GANA.items():
            gana_tools[gana].append(tool)
        _GANA_TOOLS = dict(gana_tools)
    except (ImportError, ModuleNotFoundError):
        _GANA_TOOLS = {}
    return _GANA_TOOLS


class SpeculativePrefetcher:
    """Predicts next tool calls and pre-warms the retrieval pipeline.

    Usage (wired into PRAT router):
        prefetcher.on_call_complete(gana_name)  # after each PRAT call
        result = prefetcher.get_cached(tool_name)  # before dispatch
    """

    def __init__(self, max_prefetch_tools: int = 3, ttl_seconds: float = 5.0) -> None:
        self._tracker = TransitionTracker()
        self._cache = PrefetchCache(ttl_seconds=ttl_seconds)
        self._max_prefetch = max_prefetch_tools
        self._last_gana: str | None = None
        self._prefetch_count = 0
        self._enabled = True

    def on_call_complete(self, gana_name: str) -> None:
        """Called after a PRAT call completes. Records transition and
        triggers speculative prefetch for predicted next Ganas."""
        if not self._enabled:
            return

        # Skip prefetch in test environments to prevent thread accumulation
        import os

        if os.environ.get("WM_SILENT_INIT") == "1":
            return

        # Record transition
        if self._last_gana is not None:
            self._tracker.record(self._last_gana, gana_name)
        self._last_gana = gana_name

        # Broadcast transition for cross-agent prefetch (Phase 4)
        try:
            from whitemagic.core.resonance import emit_event, EventType
            emit_event(
                source="speculative_prefetch",
                event_type=EventType.CACHE_TRANSFER,
                data={
                    "gana": gana_name,
                    "previous_gana": self._last_gana,
                    "operation": "gana_transition",
                },
            )
        except Exception:
            pass

        # Predict next and prefetch in background
        # Try citta-informed prediction first, fall back to plain Markov
        predictions = self._predict_with_citta_if_available(gana_name, top_k=2)
        if predictions:
            # Only prefetch if prediction confidence > 30%
            top_predictions = [(g, p) for g, p in predictions if p > 0.3]
            if top_predictions:
                if not self._try_go_prefetch(top_predictions):
                    # Fallback: Python threading
                    thread = threading.Thread(
                        target=self._prefetch_for_predictions,
                        args=(top_predictions,),
                        daemon=True,
                    )
                    thread.start()

    def _try_go_prefetch(self, predictions: list[tuple[str, float]]) -> bool:
        """Try Go concurrent prefetch. Returns True if Go handled it."""
        try:
            from whitemagic.core.acceleration.go_mesh_bridge import (
                go_concurrent_prefetch,
            )

            gana_tools = _get_gana_tools()
            tools_to_prefetch = []
            for gana_name, prob in predictions:
                for tool_name in gana_tools.get(gana_name, [])[: self._max_prefetch]:
                    tools_to_prefetch.append(
                        {
                            "name": tool_name,
                            "gana": gana_name,
                            "probability": round(prob, 3),
                        }
                    )
            if tools_to_prefetch:
                result = go_concurrent_prefetch(tools_to_prefetch)
                if result and result.get("status") == "ok":
                    for r in result.get("results", []):
                        if r.get("prefetched"):
                            self._cache.put(
                                f"prefetch:{r['tool']}",
                                {
                                    "prefetched": True,
                                    "gana": r.get("gana"),
                                    "tool": r.get("tool"),
                                    "probability": r.get("probability"),
                                    "timestamp": time.time(),
                                    "backend": "go_goroutine",
                                },
                            )
                            self._prefetch_count += 1
                    logger.debug(
                        "Go prefetch: %d tools in %.2fms (%d goroutines)",
                        len(tools_to_prefetch),
                        result.get("total_ms", 0),
                        result.get("goroutines", 0),
                    )
                    return True
        except (ImportError, OSError, ValueError, RuntimeError):
            pass
        return False

    def _prefetch_for_predictions(self, predictions: list[tuple[str, float]]) -> None:
        """Background thread: pre-warm retrieval pipeline for predicted Ganas."""
        gana_tools = _get_gana_tools()

        for gana_name, probability in predictions:
            tools = gana_tools.get(gana_name, [])
            # Prefetch top N tools for this Gana
            for tool_name in tools[: self._max_prefetch]:
                try:
                    self._prefetch_tool(tool_name, gana_name, probability)
                except Exception as e:
                    logger.debug(
                        "Prefetch failed for %s: %s", tool_name, e, exc_info=True
                    )

    def _prefetch_tool(
        self, tool_name: str, gana_name: str, probability: float
    ) -> None:
        """Pre-warm the retrieval pipeline for a specific tool.

        This runs the search/retrieval that would normally happen
        when the tool is called, caching the result.
        """
        # Only prefetch tools that involve memory search or introspection (the expensive path)
        search_tools = {
            "search_memories",
            "vector.search",
            "read_memory",
            "list_memories",
            "fast_read_memory",
            "batch_read_memories",
            "pattern_search",
            "gnosis",
            # Phase 4: introspection and consciousness tools
            "capabilities",
            "galaxy.stats",
            "galaxy.list",
            "meta_galaxy",
            "coherence",
            "consciousness.loop.status",
            "karma.report",
            "karmic.debt",
            "cache.status",
            "effect.trace",
        }
        if tool_name not in search_tools:
            return

        # Skip if already cached
        cache_key = f"prefetch:{tool_name}"
        if self._cache.get(cache_key) is not None:
            return

        # Pre-warm: run a lightweight retrieval pipeline probe
        try:
            from whitemagic.optimization.rust_accelerators import retrieval_pipeline

            # Create a minimal probe — just warm the Rust pipeline cache
            probe_candidates = [
                {
                    "id": "probe",
                    "score": 0.5,
                    "importance": 0.5,
                    "memory_type": "LONG_TERM",
                    "tags": [gana_name],
                    "age_days": 1.0,
                },
            ]
            probe_config = {
                "query": tool_name,
                "limit": 1,
                "enable_importance_rerank": True,
            }
            retrieval_pipeline(probe_candidates, probe_config)  # warm pipeline cache

            # Cache the fact that we pre-warmed this path
            self._cache.put(
                cache_key,
                {
                    "prefetched": True,
                    "gana": gana_name,
                    "tool": tool_name,
                    "probability": round(probability, 3),
                    "timestamp": time.time(),
                },
            )
            self._prefetch_count += 1
        except (ImportError, AttributeError):
            pass

    def _predict_with_citta_if_available(
        self, gana_name: str, top_k: int = 2
    ) -> list[tuple[str, float]]:
        """Try citta-informed prediction, fall back to plain Markov.

        Reads emotional_valence, coherence, and depth from the citta stream
        if available, then delegates to predict_with_citta. If citta is not
        running or fails, falls back to _tracker.predict().
        """
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_stream

            stream = get_citta_stream()
            state = stream.current_state if hasattr(stream, "current_state") else None
            if state and hasattr(state, "emotional_valence"):
                return self.predict_with_citta(
                    gana_name,
                    emotional_valence=getattr(state, "emotional_valence", 0.0),
                    coherence=getattr(state, "coherence", 0.5),
                    depth=getattr(state, "depth_label", "surface"),
                    top_k=top_k,
                )
        except Exception:
            pass
        return self._tracker.predict(gana_name, top_k=top_k)

    def predict_with_citta(
        self,
        current_gana: str,
        emotional_valence: float = 0.0,
        coherence: float = 0.5,
        depth: str = "surface",
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        """Citta-informed prediction: bias Markov predictions using emotional/cognitive state.

        Positive emotional valence biases toward exploration (winnowing_basket, star, wings).
        Negative valence biases toward safety (straddling_legs, wall, room).
        Low coherence biases toward introspection (ghost, heart).
        Deep states bias toward synthesis (three_stars, dipper).

        Returns list of (gana_name, adjusted_probability) sorted by probability desc.
        """
        base_predictions = self._tracker.predict(current_gana, top_k=top_k * 2)
        if not base_predictions:
            return []

        # Citta bias weights per Gana
        citta_bias: dict[str, float] = {
            "gana_winnowing_basket": 1.0 + max(0.0, emotional_valence) * 0.3,
            "gana_star": 1.0 + max(0.0, emotional_valence) * 0.2,
            "gana_wings": 1.0 + max(0.0, emotional_valence) * 0.2,
            "gana_straddling_legs": 1.0 + max(0.0, -emotional_valence) * 0.3,
            "gana_wall": 1.0 + max(0.0, -emotional_valence) * 0.2,
            "gana_room": 1.0 + max(0.0, -emotional_valence) * 0.2,
            "gana_ghost": 1.0 + max(0.0, 0.5 - coherence) * 0.4,
            "gana_heart": 1.0 + max(0.0, 0.5 - coherence) * 0.3,
            "gana_three_stars": 1.0 + (0.2 if depth == "deep" else 0.0),
            "gana_dipper": 1.0 + (0.2 if depth == "deep" else 0.0),
        }

        adjusted = []
        for gana, prob in base_predictions:
            bias = citta_bias.get(gana, 1.0)
            adjusted.append((gana, prob * bias))

        # Re-normalize
        total = sum(p for _, p in adjusted)
        if total > 0:
            adjusted = [(g, p / total) for g, p in adjusted]

        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted[:top_k]

    def get_cached(self, tool_name: str) -> dict[str, Any] | None:
        """Check if a tool's retrieval was prefetched."""
        return self._cache.get(f"prefetch:{tool_name}")

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable speculative prefetch."""
        self._enabled = enabled

    def stats(self) -> dict[str, Any]:
        """Get prefetcher statistics."""
        return {
            "enabled": self._enabled,
            "last_gana": self._last_gana,
            "prefetch_count": self._prefetch_count,
            "transitions": self._tracker.stats(),
            "cache": self._cache.stats(),
        }


_prefetcher: SpeculativePrefetcher | None = None
_prefetcher_lock = threading.Lock()


def get_prefetcher() -> SpeculativePrefetcher:
    """Get or create the global speculative prefetcher."""
    global _prefetcher
    if _prefetcher is None:
        with _prefetcher_lock:
            if _prefetcher is None:
                _prefetcher = SpeculativePrefetcher()
                # Auto-register with CacheRegistry
                try:
                    from whitemagic.core.memory.cache_registry import get_cache_registry
                    reg = get_cache_registry()
                    reg.register(
                        "prefetch",
                        flush_func=_prefetcher._cache.invalidate,
                        stats_func=_prefetcher.stats,
                    )
                except Exception:
                    logger.debug("CacheRegistry registration skipped", exc_info=True)
                # Listen for cross-agent Gana transitions (Phase 4)
                try:
                    from whitemagic.core.resonance import EventType, get_bus
                    bus = get_bus()

                    def _on_cache_transfer(event):
                        if event.event_type == EventType.CACHE_TRANSFER:
                            data = event.data
                            prev = data.get("previous_gana")
                            curr = data.get("gana")
                            if prev and curr:
                                _prefetcher._tracker.record(prev, curr)

                    bus.listen(EventType.CACHE_TRANSFER, _on_cache_transfer)
                    logger.debug("Prefetcher listening for CACHE_TRANSFER events")
                except Exception:
                    logger.debug("CACHE_TRANSFER subscription skipped", exc_info=True)
    return _prefetcher
