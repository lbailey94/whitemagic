# ruff: noqa: BLE001
"""Entity-Graph Retrieval Boosting & Second-Pass Reranker (v24.3).

Upgrades the existing RRF search pipeline with:
  1. Entity-graph retrieval boosting — extract entities from query, find
     memories sharing those entities via the associations table, boost RRF scores.
  2. Second-pass reranking — post-RRF multi-signal re-scoring using entity
     overlap, recency, importance, and lexical precision.
  3. Procedural memory integration — match query against SkillForge trigger
     phrases, inject matching skills as procedural results.
  4. Time-decay scoring — explicit temporal decay factor in RRF fusion.

All four upgrades are designed as drop-in enhancements to search_hybrid().
Each can be independently toggled via weight parameters.
"""

from __future__ import annotations

import logging
import math
import re
import sqlite3
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_entity(name: str) -> str:
    """Normalize entity name to match the format used in associations table."""
    normalized = name.lower().strip()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return normalized


def extract_query_entities(query: str) -> list[str]:
    """Extract normalized entity names from a search query.

    Uses LightNER for pattern-based extraction, falls back to simple
    capitalized word matching if LightNER is unavailable.

    Returns list of normalized entity names (without the 'entity:' prefix).
    """
    if not query or not query.strip():
        return []

    entities: list[str] = []

    try:
        from whitemagic.core.intelligence.lightweight_ner import get_light_ner

        ner = get_light_ner()
        ner_entities, _ = ner.extract(query)
        for e in ner_entities:
            normalized = _normalize_entity(e.text)
            if normalized and len(normalized) >= 2:
                entities.append(normalized)
    except (ImportError, ModuleNotFoundError, Exception) as e:
        logger.debug("LightNER extraction failed for query: %s", e)
        # Fallback: simple capitalized word extraction
        for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", query):
            normalized = _normalize_entity(match.group(1))
            if normalized and len(normalized) >= 3:
                entities.append(normalized)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def lookup_entity_memories(
    entity_names: list[str],
    conn: sqlite3.Connection,
    limit_per_entity: int = 20,
) -> dict[str, float]:
    """Look up memories associated with the given entity names.

    Queries the associations table for target_id entries matching
    'entity:<normalized_name>' and returns a mapping of
    memory_id -> entity_boost_score.

    The boost score is proportional to the number of matching entities
    and the association strength.
    """
    if not entity_names:
        return {}

    entity_ids = [f"entity:{name}" for name in entity_names]
    placeholders = ",".join("?" * len(entity_ids))

    try:
        sql = f"""
            SELECT source_id, SUM(strength) as total_strength, COUNT(*) as match_count
            FROM associations
            WHERE target_id IN ({placeholders})
              AND source_id NOT LIKE 'entity:%'
            GROUP BY source_id
            ORDER BY total_strength DESC
            LIMIT ?
        """
        rows = conn.execute(sql, entity_ids + [limit_per_entity * len(entity_names)]).fetchall()

        boosts: dict[str, float] = {}
        max_strength = max((row[1] for row in rows), default=1.0)
        for row in rows:
            mid = row[0]
            total_strength = row[1] or 0.0
            match_count = row[2] or 0
            # Normalized strength * match count factor
            normalized_strength = total_strength / max_strength if max_strength > 0 else 0.0
            match_factor = min(1.0, match_count / len(entity_names))
            boosts[mid] = normalized_strength * match_factor

        return boosts
    except sqlite3.Error as e:
        logger.debug("Entity lookup failed: %s", e)
        return {}


def compute_time_decay(
    memory: Any,
    half_life_days: float = 30.0,
    max_boost: float = 0.15,
) -> float:
    """Compute temporal decay factor for a memory.

    Recent memories get a positive boost (up to max_boost).
    Old memories get a penalty approaching -max_boost.
    At exactly one half-life, the factor is 0 (neutral).

    Returns a value in [-max_boost, +max_boost].
    """
    created = getattr(memory, "created_at", None)
    if not created:
        return 0.0

    try:
        if isinstance(created, str):
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        elif isinstance(created, datetime):
            created_dt = created
        else:
            return 0.0
    except (ValueError, TypeError):
        return 0.0

    now = datetime.now(created_dt.tzinfo) if created_dt.tzinfo else datetime.now()
    age_days = (now - created_dt).total_seconds() / 86400.0

    if age_days < 0:
        return max_boost  # Future-dated (clock skew) → max boost

    # Exponential decay: factor = max_boost * (2^(-age/half_life) - 0.5)
    # At age=0: factor = max_boost * 0.5 (positive boost)
    # At age=half_life: factor = 0 (neutral)
    # At age=2*half_life: factor = max_boost * (-0.25) (penalty)
    decay = math.pow(2.0, -age_days / half_life_days) - 0.5
    return max(-max_boost, min(max_boost, max_boost * decay))


def compute_lexical_precision(query: str, memory: Any) -> float:
    """Compute lexical precision — fraction of query terms found in memory content.

    Returns a value in [0.0, 1.0].
    """
    query_terms = set(re.findall(r"\b[a-z]{2,}\b", query.lower()))
    if not query_terms:
        return 0.0

    content = str(getattr(memory, "content", "")).lower()
    title = str(getattr(memory, "title", "") or "").lower()
    text = f"{title} {content}"

    # Skip very common words
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "can", "of", "in", "on", "at", "to",
        "for", "with", "from", "by", "as", "and", "or", "not", "but", "if",
        "then", "else", "when", "where", "why", "how", "what", "who", "which",
        "this", "that", "these", "those", "it", "its", "they", "them", "their",
    }
    query_terms -= stopwords
    if not query_terms:
        return 0.0

    matches = sum(1 for term in query_terms if term in text)
    return matches / len(query_terms)


def rerank_results(
    results: list[Any],
    query: str,
    query_entities: list[str],
    entity_weight: float = 0.25,
    recency_weight: float = 0.15,
    importance_weight: float = 0.20,
    lexical_weight: float = 0.15,
) -> list[Any]:
    """Second-pass reranking of RRF results using multi-signal scoring.

    Re-scores each result based on:
      - Entity overlap: does the memory share entities with the query?
      - Recency: how recent is the memory?
      - Importance: memory.importance field
      - Lexical precision: fraction of query terms in memory content

    The reranking adjusts the existing RRF score multiplicatively.
    """
    if not results:
        return results

    if len(results) == 1:
        # Still add metadata to single result
        mem = results[0]
        rrf_score = float(mem.metadata.get("rrf_score", 0.0))
        mem.metadata["rerank_score"] = round(rrf_score, 6)
        mem.metadata["entity_overlap"] = 0.0
        mem.metadata["recency_factor"] = round(compute_time_decay(mem), 3)
        mem.metadata["lexical_precision"] = round(compute_lexical_precision(query, mem), 3)
        return results

    # Get entity-associated memory IDs if entities were extracted
    entity_boosts: dict[str, float] = {}
    if query_entities:
        try:
            from whitemagic.config.paths import DB_PATH
            from whitemagic.core.memory.db_manager import safe_connect

            if DB_PATH.exists():
                conn = safe_connect(str(DB_PATH))
                try:
                    entity_boosts = lookup_entity_memories(query_entities, conn)
                finally:
                    conn.close()
        except (ImportError, ModuleNotFoundError, Exception) as e:
            logger.debug("Entity boost lookup failed: %s", e)

    scored: list[tuple[float, int, Any]] = []
    for idx, mem in enumerate(results):
        rrf_score = float(mem.metadata.get("rrf_score", 0.0))

        # Entity overlap score [0, 1]
        entity_score = entity_boosts.get(mem.id, 0.0)

        # Recency score [-1, 1]
        recency_score = compute_time_decay(mem)

        # Importance score [0, 1]
        importance_score = float(getattr(mem, "importance", 0.5))

        # Lexical precision [0, 1]
        lex_precision = compute_lexical_precision(query, mem)

        # Combined adjustment
        adjustment = (
            entity_weight * entity_score
            + recency_weight * recency_score
            + importance_weight * importance_score
            + lexical_weight * lex_precision
        )

        final_score = rrf_score * (1.0 + adjustment)

        # Store rerank metadata
        mem.metadata["rerank_score"] = round(final_score, 6)
        mem.metadata["entity_overlap"] = round(entity_score, 3)
        mem.metadata["recency_factor"] = round(recency_score, 3)
        mem.metadata["lexical_precision"] = round(lex_precision, 3)

        scored.append((final_score, idx, mem))

    # Sort by final score descending, preserving original order for ties
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item[2] for item in scored]


def match_procedural_skills(
    query: str,
    max_matches: int = 3,
) -> list[dict[str, Any]]:
    """Match query against SkillForge trigger phrases.

    Returns a list of matching skill dicts with name, description,
    trigger, and step count. These can be injected as procedural
    memory results alongside regular search results.
    """
    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        if not forge.known_skills:
            return []

        query_lower = query.lower()
        query_terms = set(re.findall(r"\b[a-z]{2,}\b", query_lower))

        matches: list[tuple[float, dict[str, Any]]] = []
        for name, skill in forge.known_skills.items():
            # Check trigger phrase overlap
            best_score = 0.0
            for trigger in skill.trigger_phrases:
                trigger_lower = trigger.lower()
                trigger_terms = set(re.findall(r"\b[a-z]{2,}\b", trigger_lower))

                if not trigger_terms:
                    continue

                # Jaccard-like overlap
                overlap = len(query_terms & trigger_terms)
                score = overlap / len(query_terms | trigger_terms)

                # Exact substring match gets a big boost
                if trigger_lower in query_lower:
                    score = max(score, 0.8)

                best_score = max(best_score, score)

            if best_score >= 0.15:
                matches.append((
                    best_score,
                    {
                        "skill_name": skill.name,
                        "description": skill.description,
                        "trigger": skill.trigger_phrases[0] if skill.trigger_phrases else "",
                        "step_count": len(skill.optimized_chain.steps),
                        "forge_count": skill.forge_count,
                        "match_score": round(best_score, 3),
                    },
                ))

        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:max_matches]]
    except (ImportError, ModuleNotFoundError, Exception) as e:
        logger.debug("Skill matching failed: %s", e)
        return []


def apply_entity_boosts(
    rrf_scores: dict[str, float],
    query_entities: list[str],
    entity_weight: float = 0.3,
    backend: Any = None,
) -> dict[str, float]:
    """Apply entity-graph retrieval boosting to RRF scores.

    Boosts scores of memories that share entities with the query.
    Modifies rrf_scores in-place and returns the updated dict.
    """
    if not query_entities or entity_weight <= 0:
        return rrf_scores

    entity_boosts: dict[str, float] = {}

    # Try to get a connection from the backend's pool
    if backend and hasattr(backend, "pool"):
        try:
            with backend.pool.connection() as conn:
                entity_boosts = lookup_entity_memories(query_entities, conn)
        except (sqlite3.Error, AttributeError, TypeError) as e:
            logger.debug("Entity boost via pool failed: %s", e)

    # Fallback: direct connection
    if not entity_boosts:
        try:
            from whitemagic.config.paths import DB_PATH
            from whitemagic.core.memory.db_manager import safe_connect

            if DB_PATH.exists():
                conn = safe_connect(str(DB_PATH))
                try:
                    entity_boosts = lookup_entity_memories(query_entities, conn)
                finally:
                    conn.close()
        except (ImportError, ModuleNotFoundError, Exception) as e:
            logger.debug("Entity boost fallback failed: %s", e)

    # Apply boosts to existing RRF scores
    for mid, boost in entity_boosts.items():
        if mid in rrf_scores:
            rrf_scores[mid] += entity_weight * boost
        else:
            # Entity match not in RRF results — add with base score
            rrf_scores[mid] = entity_weight * boost

    return rrf_scores


def batch_constellation_memberships(
    memory_ids: list[str],
    backend: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    """Batch-fetch constellation memberships for multiple memories.

    Queries the backend once with all candidate IDs, eliminating the
    N+1 pattern of per-candidate get_constellation_memberships() calls.

    Returns:
        Dict mapping memory_id -> list of membership dicts.
    """
    if not memory_ids:
        return {}

    result: dict[str, list[dict[str, Any]]] = {}

    # Collect all backends to query
    backends: list[Any] = []
    if backend and hasattr(backend, "_galaxy_backends"):
        backends.extend(backend._galaxy_backends.values())
    if backend and hasattr(backend, "_get_default_backend"):
        backends.append(backend._get_default_backend())

    for b in backends:
        try:
            with b.pool.connection() as conn:
                placeholders = ",".join("?" * len(memory_ids))
                rows = conn.execute(
                    f"""
                    SELECT memory_id, constellation_name, membership_confidence
                    FROM constellation_memberships
                    WHERE memory_id IN ({placeholders})
                    """,
                    memory_ids,
                ).fetchall()
                for row in rows:
                    mid = row[0]
                    if mid not in result:
                        result[mid] = []
                    result[mid].append({
                        "constellation_name": row[1],
                        "membership_confidence": row[2] if len(row) > 2 else 0.5,
                    })
        except (sqlite3.Error, AttributeError, Exception) as e:
            logger.debug("Batch constellation lookup failed: %s", e)

    return result
