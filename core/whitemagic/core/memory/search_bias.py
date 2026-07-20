"""Search Bias — Working memory and Citta state influence on search results.

Implements Phase 4 of the Memory & Cognitive Systems Strategy 2026.

Wires cognitive state into the search pipeline:
  1. Working memory bias: Memories currently in working memory (recently
     attended) get a small boost in search results. This models cognitive
     priming — things you're thinking about are easier to recall.
  2. Citta state personalization: The current emotional/cognitive state
     (citta cycle) influences search by boosting memories with matching
     emotional valence.

Both biases are additive adjustments to the RRF score, preserving the
0-token search guarantee.

Usage:
    from whitemagic.core.memory.search_bias import apply_search_bias

    results = apply_search_bias(query, results)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Bias weights
WM_BOOST = 0.05  # Boost for memories in working memory
CITTA_VALENCE_MATCH_BOOST = 0.03  # Boost for matching emotional valence
CITTA_VALENCE_MISMATCH_PENALTY = 0.01  # Small penalty for mismatched valence
CITTA_COHERENCE_HIGH_BOOST = 0.04  # Boost for distant memories when coherence is high
CITTA_COHERENCE_LOW_BOOST = 0.04  # Boost for familiar memories when coherence is low
CITTA_REM_BOOST = 0.06  # Boost for dream-consolidated memories in REM mode
WM_AUTO_ATTEND_TOP_K = 3  # How many top search results to auto-attend to WM


def _get_working_memory_ids() -> set[str]:
    """Get the set of memory IDs currently in working memory."""
    try:
        from whitemagic.core.intelligence.working_memory import get_working_memory
        wm = get_working_memory()
        return set(wm.get_active_ids())
    except (ImportError, ModuleNotFoundError, Exception):  # noqa: BLE001
        return set()


def _get_citta_valence() -> float | None:
    """Get the current citta emotional valence (-1 to 1).

    Returns None if citta system is unavailable.
    """
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        cycle = get_citta_cycle()
        state = cycle.get_state()
        # Citta state may have valence info
        if isinstance(state, dict):
            return state.get("emotional_valence")
        if hasattr(state, "emotional_valence"):
            return state.emotional_valence
    except (ImportError, ModuleNotFoundError, Exception):  # noqa: BLE001
        pass
    return None


def _get_citta_coherence() -> float | None:
    """Get the current citta coherence score (0 to 1).

    Returns None if citta system is unavailable.
    """
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        cycle = get_citta_cycle()
        state = cycle.get_state()
        if isinstance(state, dict):
            return state.get("coherence")
        if hasattr(state, "coherence"):
            return state.coherence
    except (ImportError, ModuleNotFoundError, Exception):  # noqa: BLE001
        pass
    return None


def _get_citta_depth() -> str | None:
    """Get the current citta depth layer.

    Returns None if citta system is unavailable.
    """
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        cycle = get_citta_cycle()
        state = cycle.get_state()
        if isinstance(state, dict):
            return state.get("depth")
        if hasattr(state, "depth"):
            return state.depth
    except (ImportError, ModuleNotFoundError, Exception):  # noqa: BLE001
        pass
    return None


def apply_working_memory_bias(
    results: list[Any],
    boost: float = WM_BOOST,
) -> list[Any]:
    """Boost memories that are currently in working memory.

    Args:
        results: List of Memory objects with metadata
        boost: RRF score boost for working memory matches

    Returns:
        Results with working_memory_boost metadata set.
    """
    if not results:
        return results

    wm_ids = _get_working_memory_ids()
    if not wm_ids:
        return results

    for mem in results:
        mid = str(mem.id)
        if mid in wm_ids:
            # Apply boost to RRF score
            rrf = float(mem.metadata.get("rrf_score", 0.0))
            mem.metadata["rrf_score"] = round(rrf + boost, 6)
            mem.metadata["working_memory_boosted"] = True

    # Re-sort by RRF score
    results.sort(key=lambda m: float(m.metadata.get("rrf_score", 0.0)), reverse=True)
    return results


def apply_citta_bias(
    results: list[Any],
    valence: float | None = None,
    match_boost: float = CITTA_VALENCE_MATCH_BOOST,
    mismatch_penalty: float = CITTA_VALENCE_MISMATCH_PENALTY,
) -> list[Any]:
    """Apply citta emotional valence bias to search results.

    Memories with emotional valence matching the current citta state get
    a small boost. Memories with opposing valence get a small penalty.

    Args:
        results: List of Memory objects
        valence: Current citta valence (-1 to 1). If None, auto-detected.
        match_boost: Boost for matching valence
        mismatch_penalty: Penalty for mismatched valence

    Returns:
        Results with citta_bias metadata set.
    """
    if not results:
        return results

    if valence is None:
        valence = _get_citta_valence()

    if valence is None:
        return results  # No citta state available

    # Determine valence sign
    citta_positive = valence > 0.1
    citta_negative = valence < -0.1

    if not citta_positive and not citta_negative:
        return results  # Neutral citta state — no bias

    for mem in results:
        mem_valence = float(getattr(mem, "emotional_valence", 0.0))

        if citta_positive and mem_valence > 0.1:
            rrf = float(mem.metadata.get("rrf_score", 0.0))
            mem.metadata["rrf_score"] = round(rrf + match_boost, 6)
            mem.metadata["citta_bias"] = "positive_match"
        elif citta_negative and mem_valence < -0.1:
            rrf = float(mem.metadata.get("rrf_score", 0.0))
            mem.metadata["rrf_score"] = round(rrf + match_boost, 6)
            mem.metadata["citta_bias"] = "negative_match"
        elif (citta_positive and mem_valence < -0.1) or (citta_negative and mem_valence > 0.1):
            rrf = float(mem.metadata.get("rrf_score", 0.0))
            mem.metadata["rrf_score"] = round(rrf - mismatch_penalty, 6)
            mem.metadata["citta_bias"] = "mismatch"

    # Re-sort by RRF score
    results.sort(key=lambda m: float(m.metadata.get("rrf_score", 0.0)), reverse=True)
    return results


def auto_attend_to_working_memory(
    results: list[Any],
    top_k: int = WM_AUTO_ATTEND_TOP_K,
) -> None:
    """Auto-attend top search results into working memory.

    This implements the cognitive integration where search results
    automatically enter working memory, making them available for
    future search bias and consciousness loop context.

    Args:
        results: List of Memory objects from search
        top_k: Number of top results to attend
    """
    if not results:
        return
    try:
        from whitemagic.core.intelligence.working_memory import get_working_memory
        wm = get_working_memory()
        for mem in results[:top_k]:
            wm.attend(
                memory_id=str(mem.id),
                content=str(mem.content)[:500],
                title=getattr(mem, "title", "") or "",
                importance=getattr(mem, "importance", 0.5),
                tags=getattr(mem, "tags", None),
            )
    except (ImportError, ModuleNotFoundError, Exception) as e:  # noqa: BLE001
        logger.debug("Auto-attend to WM failed: %s", e)


def apply_citta_coherence_bias(
    results: list[Any],
    coherence: float | None = None,
) -> list[Any]:
    """Apply citta coherence-based search bias.

    High coherence → prioritize semantically distant but relevant memories
    (exploration mode). Low coherence → prioritize familiar, high-importance
    memories (exploitation mode).

    Args:
        results: List of Memory objects
        coherence: Current coherence score (0-1). If None, auto-detected.

    Returns:
        Results with coherence bias applied.
    """
    if not results:
        return results

    if coherence is None:
        coherence = _get_citta_coherence()

    if coherence is None:
        return results

    if coherence > 0.7:
        # High coherence: boost distant memories (high galactic_distance)
        for mem in results:
            gdist = float(getattr(mem, "galactic_distance", 0.5))
            if gdist > 0.5:
                rrf = float(mem.metadata.get("rrf_score", 0.0))
                mem.metadata["rrf_score"] = round(rrf + CITTA_COHERENCE_HIGH_BOOST, 6)
                mem.metadata["coherence_bias"] = "distant_boost"
    elif coherence < 0.4:
        # Low coherence: boost familiar, high-importance memories
        for mem in results:
            importance = float(getattr(mem, "importance", 0.5))
            if importance > 0.7:
                rrf = float(mem.metadata.get("rrf_score", 0.0))
                mem.metadata["rrf_score"] = round(rrf + CITTA_COHERENCE_LOW_BOOST, 6)
                mem.metadata["coherence_bias"] = "familiar_boost"

    results.sort(key=lambda m: float(m.metadata.get("rrf_score", 0.0)), reverse=True)
    return results


def apply_citta_rem_bias(
    results: list[Any],
    depth: str | None = None,
) -> list[Any]:
    """Apply REM mode bias for dream-consolidated associations.

    When citta depth is 'dream' or 'rem', boost memories from the
    dreams galaxy that were created during dream cycle consolidation.

    Args:
        results: List of Memory objects
        depth: Current citta depth. If None, auto-detected.

    Returns:
        Results with REM bias applied.
    """
    if not results:
        return results

    if depth is None:
        depth = _get_citta_depth()

    if depth is None or depth.lower() not in ("dream", "rem", "flow"):
        return results

    for mem in results:
        galaxy = getattr(mem, "galaxy", "") or ""
        if galaxy == "dreams":
            rrf = float(mem.metadata.get("rrf_score", 0.0))
            mem.metadata["rrf_score"] = round(rrf + CITTA_REM_BOOST, 6)
            mem.metadata["rem_bias"] = True

    results.sort(key=lambda m: float(m.metadata.get("rrf_score", 0.0)), reverse=True)
    return results


def apply_search_bias(
    query: str,
    results: list[Any],
    enable_wm: bool = True,
    enable_citta: bool = True,
    auto_attend: bool = True,
) -> list[Any]:
    """Apply all search biases (working memory + citta state).

    This is the main entry point for search bias. It applies both
    working memory priming and citta emotional valence bias, plus
    coherence-based and REM mode biases.

    Args:
        query: The search query (unused but kept for interface consistency)
        results: List of Memory objects with metadata
        enable_wm: Whether to apply working memory bias
        enable_citta: Whether to apply citta state bias
        auto_attend: Whether to auto-attend top results to working memory

    Returns:
        Biased and re-sorted results.
    """
    if not results:
        return results

    if enable_wm:
        results = apply_working_memory_bias(results)

    if enable_citta:
        results = apply_citta_bias(results)
        results = apply_citta_coherence_bias(results)
        results = apply_citta_rem_bias(results)

    if auto_attend:
        auto_attend_to_working_memory(results)

    return results
