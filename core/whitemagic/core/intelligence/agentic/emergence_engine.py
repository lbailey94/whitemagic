"""Emergence Engine — Novel Pattern & Resonance Cascade Detection.

Detects emergent phenomena in the memory system:
- Tag clusters forming around new topics
- Resonance cascades (multiple related memories in short time windows)
- Novelty spikes (sudden increases in previously rare tags)
- Cross-domain bridges (memories connecting previously separate constellations)
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmergenceInsight:
    """A detected emergent pattern."""

    id: str
    title: str
    description: str
    confidence: float
    source: str  # "tag_cluster", "resonance_cascade", "novelty_spike", "cross_domain"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class EmergenceEngine:
    """Detects emergent patterns in the WhiteMagic memory system.

    Scans for:
    - Tag clusters: groups of tags appearing together more frequently than baseline
    - Resonance cascades: bursts of related memories within short time windows
    - Novelty spikes: sudden increases in previously rare or new tags
    - Cross-domain bridges: memories that connect previously separate constellations
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import DB_PATH
            self.db_path = str(DB_PATH)
        else:
            self.db_path = db_path
        self._past_insights: list[dict[str, Any]] = []

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def scan_for_emergence(self) -> list[EmergenceInsight]:
        """Run full emergence scan across all detection modes."""
        insights: list[EmergenceInsight] = []

        insights.extend(self._detect_tag_clusters())
        insights.extend(self._detect_resonance_cascades())
        insights.extend(self._detect_novelty_spikes())
        insights.extend(self._detect_cross_domain_bridges())

        # Store for later retrieval
        for ins in insights:
            self._past_insights.append({
                "id": ins.id,
                "title": ins.title,
                "description": ins.description,
                "confidence": ins.confidence,
                "source": ins.source,
                "timestamp": ins.timestamp,
            })

        # Keep only last 100 past insights
        if len(self._past_insights) > 100:
            self._past_insights = self._past_insights[-100:]

        logger.info(f"Emergence scan complete: {len(insights)} patterns detected")
        return insights

    def get_insights(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return past emergence insights."""
        return self._past_insights[-limit:]

    # ------------------------------------------------------------------
    # Detection modes
    # ------------------------------------------------------------------

    def _detect_tag_clusters(self) -> list[EmergenceInsight]:
        """Find tags that co-occur more frequently than expected by chance."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Get tag co-occurrence pairs from recent memories (last 7 days)
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            cur.execute("""
                SELECT t1.tag as tag_a, t2.tag as tag_b, COUNT(*) as co_count
                FROM tags t1
                JOIN tags t2 ON t1.memory_id = t2.memory_id AND t1.tag < t2.tag
                JOIN memories m ON t1.memory_id = m.id
                WHERE m.created_at > ?
                GROUP BY t1.tag, t2.tag
                HAVING co_count >= 3
                ORDER BY co_count DESC
                LIMIT 10
            """, (cutoff,))
        except Exception as e:
            logger.debug(f"Tag cluster detection skipped: {e}")
            return []

        rows = cur.fetchall()
        insights: list[EmergenceInsight] = []
        for r in rows:
            tag_a, tag_b, count = r["tag_a"], r["tag_b"], r["co_count"]
            insights.append(EmergenceInsight(
                id=f"tag_cluster_{tag_a}_{tag_b}",
                title=f"Tag cluster: {tag_a} + {tag_b}",
                description=f"Tags '{tag_a}' and '{tag_b}' co-occurred {count} times in the last 7 days — "
                            f"above the emergence threshold. This may indicate a new topic nexus forming.",
                confidence=min(0.95, 0.5 + count * 0.1),
                source="tag_cluster",
                metadata={"tag_a": tag_a, "tag_b": tag_b, "co_count": count},
            ))
        return insights

    def _detect_resonance_cascades(self) -> list[EmergenceInsight]:
        """Find bursts of related memories appearing in short time windows."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Find tags that had a burst of activity (>=5 memories in a single hour)
            cur.execute("""
                SELECT t.tag, COUNT(*) as burst_count,
                       MIN(m.created_at) as first_seen, MAX(m.created_at) as last_seen
                FROM tags t
                JOIN memories m ON t.memory_id = m.id
                WHERE m.created_at > datetime('now', '-3 days')
                GROUP BY t.tag
                HAVING burst_count >= 5
                ORDER BY burst_count DESC
                LIMIT 10
            """)
        except Exception as e:
            logger.debug(f"Resonance cascade detection skipped: {e}")
            return []

        rows = cur.fetchall()
        insights: list[EmergenceInsight] = []
        for r in rows:
            tag, count = r["tag"], r["burst_count"]
            insights.append(EmergenceInsight(
                id=f"cascade_{tag}",
                title=f"Resonance cascade: '{tag}'",
                description=f"Tag '{tag}' appeared {count} times in the last 3 days — "
                            f"a resonance cascade indicating heightened attention on this topic.",
                confidence=min(0.95, 0.4 + count * 0.08),
                source="resonance_cascade",
                metadata={"tag": tag, "burst_count": count},
            ))
        return insights

    def _detect_novelty_spikes(self) -> list[EmergenceInsight]:
        """Find tags that are newly appearing or suddenly increasing in frequency."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Compare tag frequency in last 3 days vs previous 30 days
            cur.execute("""
                SELECT recent.tag,
                       recent.recent_count,
                       COALESCE(historical.hist_count, 0) as hist_count
                FROM (
                    SELECT t.tag, COUNT(*) as recent_count
                    FROM tags t
                    JOIN memories m ON t.memory_id = m.id
                    WHERE m.created_at > datetime('now', '-3 days')
                    GROUP BY t.tag
                ) recent
                LEFT JOIN (
                    SELECT t.tag, COUNT(*) as hist_count
                    FROM tags t
                    JOIN memories m ON t.memory_id = m.id
                    WHERE m.created_at BETWEEN datetime('now', '-33 days') AND datetime('now', '-3 days')
                    GROUP BY t.tag
                ) historical ON recent.tag = historical.tag
                WHERE recent.recent_count >= 3
                  AND (historical.hist_count = 0 OR recent.recent_count > historical.hist_count * 2)
                ORDER BY recent.recent_count DESC
                LIMIT 10
            """)
        except Exception as e:
            logger.debug(f"Novelty spike detection skipped: {e}")
            return []

        rows = cur.fetchall()
        insights: list[EmergenceInsight] = []
        for r in rows:
            tag, recent, hist = r["tag"], r["recent_count"], r["hist_count"]
            if hist == 0:
                desc = f"Tag '{tag}' is brand new — {recent} appearances in the last 3 days with zero prior history."
            else:
                desc = f"Tag '{tag}' spiked from {hist} (30-day baseline) to {recent} (last 3 days) — "
                desc += f"a {recent / max(hist, 1):.1f}x increase indicating a novelty spike."
            insights.append(EmergenceInsight(
                id=f"novelty_{tag}",
                title=f"Novelty spike: '{tag}'",
                description=desc,
                confidence=min(0.95, 0.5 + (recent - hist) * 0.1),
                source="novelty_spike",
                metadata={"tag": tag, "recent_count": recent, "hist_count": hist},
            ))
        return insights

    def _detect_cross_domain_bridges(self) -> list[EmergenceInsight]:
        """Find memories that bridge previously separate constellations."""
        try:
            from whitemagic.core.intelligence.core_access import get_core_access
            cal = get_core_access()
        except Exception as e:
            logger.debug(f"Cross-domain bridge detection skipped (no CoreAccess): {e}")
            return []

        bridges = cal.find_constellation_bridges(limit=10) if cal else []
        if not bridges:
            return []

        insights: list[EmergenceInsight] = []
        for b in bridges[:5]:
            c1, c2 = b.get("constellation_1", "?"), b.get("constellation_2", "?")
            strength = b.get("bridge_strength", 0.5)
            insights.append(EmergenceInsight(
                id=f"bridge_{c1}_{c2}",
                title=f"Cross-domain bridge: {c1} ↔ {c2}",
                description=f"Constellations '{c1}' and '{c2}' are forming a bridge "
                            f"(strength: {strength:.2f}) — previously separate domains converging.",
                confidence=min(0.95, strength),
                source="cross_domain",
                metadata={"constellation_1": c1, "constellation_2": c2, "strength": strength},
            ))
        return insights


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_emergence_engine: EmergenceEngine | None = None


def get_emergence_engine() -> EmergenceEngine:
    """
    Get the emergence engine.
    
    Returns:
        EmergenceEngine
    """
    global _emergence_engine
    if _emergence_engine is None:
        _emergence_engine = EmergenceEngine()
    return _emergence_engine
