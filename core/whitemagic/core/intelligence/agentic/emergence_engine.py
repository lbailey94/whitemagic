# ruff: noqa: BLE001
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
from datetime import UTC, datetime, timedelta
from typing import Any

from whitemagic.core.memory.db_manager import safe_connect
from whitemagic.core.memory.galaxy_scan import scan_query_all

logger = logging.getLogger(__name__)

# System-generated tags that are metadata, not cognitive signals
_NOISE_TAG_PREFIXES = {"galaxy:", "source:", "confidence-", "auto-", "auto_"}
_NOISE_TAGS = {"ingested", "auto_generated", "auto-finalized", "scratchpad"}


def _is_noise_tag(tag: str) -> bool:
    """Check if a tag is system-generated metadata rather than a cognitive signal."""
    if tag in _NOISE_TAGS:
        return True
    for prefix in _NOISE_TAG_PREFIXES:
        if tag.startswith(prefix):
            return True
    return False


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
    - Creative tensions: bicameral low-confidence events indicating unresolved
      cognitive dissonance (v23.3: wired from BicameralReasoner)
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import DB_PATH

            self.db_path = str(DB_PATH)
        else:
            self.db_path = db_path
        self._past_insights: list[dict[str, Any]] = []
        self._creative_tensions: list[dict[str, Any]] = []
        self._listening = False
        # Novelty filtering: track seen signatures to suppress recursive echoes
        self._seen_signatures: dict[str, int] = {}  # signature → count seen
        self._novelty_threshold = 2  # After seeing same signature N times, suppress
        self._start_listening()

    def _get_conn(self) -> sqlite3.Connection:
        conn = safe_connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _start_listening(self) -> None:
        """Register on the Gan Ying bus for bicameral low-confidence events."""
        if self._listening:
            return
        try:
            from whitemagic.core.resonance import EventType, get_bus

            get_bus().listen(
                EventType.CREATIVE_BRIDGE_LOW_CONFIDENCE, self._on_creative_tension
            )
            self._listening = True
            logger.debug("EmergenceEngine listening for bicameral creative tensions")
        except Exception as e:
            logger.debug("EmergenceEngine could not register listener: %s", e)

    def _on_creative_tension(self, event: Any) -> None:
        """Handle bicameral low-confidence events as emergence signals."""
        data = getattr(event, "data", {})
        if not data:
            return
        self._creative_tensions.append(
            {
                "query": data.get("query", ""),
                "tension": data.get("tension", 0.0),
                "confidence": data.get("confidence", 0.0),
                "dominant": data.get("dominant", "balanced"),
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self._creative_tensions) > 50:
            self._creative_tensions = self._creative_tensions[-50:]

    def _compute_signature(self, insight: EmergenceInsight) -> str:
        """Compute a novelty signature for an insight.

        Two insights with the same signature are considered the same pattern.
        For tag clusters, the signature includes the tag pair but NOT the count,
        so that the same pair at different counts is still recognized as a repeat.
        """
        if insight.source == "tag_cluster":
            tags = sorted([insight.metadata.get("tag_a", ""), insight.metadata.get("tag_b", "")])
            return f"tag_cluster:{tags[0]}+{tags[1]}"
        elif insight.source == "resonance_cascade":
            return f"cascade:{insight.metadata.get('tag', '')}"
        elif insight.source == "novelty_spike":
            return f"novelty:{insight.metadata.get('tag', '')}"
        elif insight.source == "cross_domain":
            c1 = insight.metadata.get("constellation_1", "")
            c2 = insight.metadata.get("constellation_2", "")
            return f"bridge:{min(c1, c2)}+{max(c1, c2)}"
        elif insight.source == "creative_tension":
            return f"tension:{insight.metadata.get('query', '')[:60]}"
        return insight.id

    def _filter_novel(self, insights: list[EmergenceInsight]) -> list[EmergenceInsight]:
        """Filter out recursive echoes — insights we've seen too many times.

        An insight is suppressed if its signature has been seen >= novelty_threshold
        times before. This prevents the emergence engine from reporting the same
        tag clusters and patterns repeatedly, which creates a recursive echo
        chamber rather than true emergence.

        The first occurrence is always reported (novelty = 1.0).
        The second is reported with reduced confidence (novelty = 0.5).
        The third and beyond are suppressed entirely.
        """
        novel: list[EmergenceInsight] = []
        for ins in insights:
            sig = self._compute_signature(ins)
            seen_count = self._seen_signatures.get(sig, 0)

            if seen_count == 0:
                # First occurrence — full novelty
                novel.append(ins)
            elif seen_count == 1:
                # Second occurrence — reduced confidence, still reported
                ins.confidence *= 0.5
                ins.title = f"{ins.title} (recurring)"
                novel.append(ins)
            # seen_count >= 2: suppress (recursive echo)

            self._seen_signatures[sig] = seen_count + 1

        # Prune signatures that haven't been seen recently (keep dict bounded)
        if len(self._seen_signatures) > 500:
            # Keep only the most recent 250 signatures
            sorted_sigs = sorted(self._seen_signatures.items(), key=lambda x: -x[1])
            self._seen_signatures = dict(sorted_sigs[:250])

        return novel

    def scan_for_emergence(self) -> list[EmergenceInsight]:
        """Run full emergence scan across all detection modes.

        Applies novelty filtering to suppress recursive echoes — patterns
        that have been detected before are suppressed or reported with
        reduced confidence, ensuring the engine surfaces truly novel
        emergence rather than repeating the same findings.
        """
        raw_insights: list[EmergenceInsight] = []

        raw_insights.extend(self._detect_tag_clusters())
        raw_insights.extend(self._detect_resonance_cascades())
        raw_insights.extend(self._detect_novelty_spikes())
        raw_insights.extend(self._detect_cross_domain_bridges())
        raw_insights.extend(self._detect_creative_tensions())

        # Novelty filter: suppress recursive echoes
        insights = self._filter_novel(raw_insights)

        for ins in insights:
            self._past_insights.append(
                {
                    "id": ins.id,
                    "title": ins.title,
                    "description": ins.description,
                    "confidence": ins.confidence,
                    "source": ins.source,
                    "timestamp": ins.timestamp,
                }
            )

        # Keep only last 100 past insights
        if len(self._past_insights) > 100:
            self._past_insights = self._past_insights[-100:]

        suppressed = len(raw_insights) - len(insights)
        logger.info(
            "Emergence scan: %s patterns detected, %s suppressed as recursive echoes",
            len(insights),
            suppressed,
        )

        # Persist novel insights to knowledge galaxy
        if insights:
            try:
                self._persist_insights(insights)
            except Exception:
                logger.debug("Failed to persist emergence insights", exc_info=True)

        return insights

    def _persist_insights(self, insights: list[EmergenceInsight]) -> None:
        """Persist emergence insights to the knowledge galaxy."""
        from datetime import datetime

        from whitemagic.config.paths import galaxy_db_path
        from whitemagic.core.memory.db_manager import safe_connect

        db = galaxy_db_path("knowledge")
        if not db.exists():
            db.parent.mkdir(parents=True, exist_ok=True)

        conn = safe_connect(str(db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergence_insights (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT,
                metadata_json TEXT,
                persisted_at TEXT
            )
        """)

        now = datetime.now(UTC).isoformat()
        rows = []
        skipped = 0
        for ins in insights:
            import json as _json
            # Check if an insight with the same content already exists
            existing = conn.execute(
                "SELECT 1 FROM emergence_insights WHERE id = ? OR "
                "(source = ? AND title = ? AND description = ?)",
                (ins.id, ins.source, ins.title, ins.description),
            ).fetchone()
            if existing:
                skipped += 1
                continue

            rows.append((
                ins.id,
                ins.title,
                ins.description,
                ins.confidence,
                ins.source,
                ins.timestamp,
                _json.dumps(ins.metadata),
                now,
            ))

        if rows:
            conn.executemany(
                "INSERT OR IGNORE INTO emergence_insights (id, title, description, confidence, source, timestamp, metadata_json, persisted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        conn.close()
        logger.info("Persisted %d emergence insights to knowledge galaxy (%d duplicates skipped)", len(rows), skipped)

    def get_insights(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return past emergence insights."""
        return self._past_insights[-limit:]

    def record_ignition(self, ignition: dict[str, Any], tool: str = "") -> None:
        """WI 5: Record a citta ignition event as a candidate emergence pattern.

        Ignition events are sudden large displacements in 16D citta space.
        Recording them here makes them visible to emergence scans and
        knowledge gap detection.
        """
        try:
            insight = EmergenceInsight(
                id=f"ignition_{ignition.get('position', 0)}",
                title=f"Ignition event during {tool}" if tool else "Ignition event",
                description=(
                    f"Citta ignition: displacement={ignition.get('displacement', 0.0):.3f}, "
                    f"layer={ignition.get('layer', 'unknown')}"
                ),
                confidence=0.5,
                source="citta_ignition",
                metadata=ignition,
            )
            self._past_insights.append(
                {
                    "id": insight.id,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "source": insight.source,
                    "timestamp": insight.timestamp,
                }
            )
            if len(self._past_insights) > 100:
                self._past_insights = self._past_insights[-100:]
        except Exception as e:
            logger.debug("Failed to record ignition: %s", e)

    def _detect_tag_clusters(self) -> list[EmergenceInsight]:
        """Find tags that co-occur more frequently than expected by chance."""
        try:
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            rows = scan_query_all(
                "SELECT t1.tag as tag_a, t2.tag as tag_b, COUNT(*) as co_count "
                "FROM tags t1 "
                "JOIN tags t2 ON t1.memory_id = t2.memory_id AND t1.tag < t2.tag "
                "JOIN memories m ON t1.memory_id = m.id "
                "WHERE m.created_at > ? "
                "GROUP BY t1.tag, t2.tag "
                "HAVING co_count >= 3 "
                "ORDER BY co_count DESC LIMIT 10",
                (cutoff,),
            )
        except Exception as e:
            logger.debug("Tag cluster detection skipped: %s", e, exc_info=True)
            return []

        insights: list[EmergenceInsight] = []
        for r in rows:
            tag_a, tag_b, count = r["tag_a"], r["tag_b"], r["co_count"]
            if _is_noise_tag(tag_a) or _is_noise_tag(tag_b):
                continue
            insights.append(
                EmergenceInsight(
                    id=f"tag_cluster_{tag_a}_{tag_b}",
                    title=f"Tag cluster: {tag_a} + {tag_b}",
                    description=f"Tags '{tag_a}' and '{tag_b}' co-occurred {count} times in the last 7 days — "
                    f"above the emergence threshold. This may indicate a new topic nexus forming.",
                    confidence=min(0.95, 0.5 + count * 0.1),
                    source="tag_cluster",
                    metadata={"tag_a": tag_a, "tag_b": tag_b, "co_count": count},
                )
            )
        return insights

    def _detect_resonance_cascades(self) -> list[EmergenceInsight]:
        """Find bursts of related memories appearing in short time windows."""
        try:
            rows = scan_query_all(
                "SELECT t.tag, COUNT(*) as burst_count, "
                "MIN(m.created_at) as first_seen, MAX(m.created_at) as last_seen "
                "FROM tags t JOIN memories m ON t.memory_id = m.id "
                "WHERE m.created_at > datetime('now', '-3 days') "
                "GROUP BY t.tag HAVING burst_count >= 5 "
                "ORDER BY burst_count DESC LIMIT 10"
            )
        except Exception as e:
            logger.debug("Resonance cascade detection skipped: %s", e, exc_info=True)
            return []

        insights: list[EmergenceInsight] = []
        for r in rows:
            tag, count = r["tag"], r["burst_count"]
            if _is_noise_tag(tag):
                continue
            insights.append(
                EmergenceInsight(
                    id=f"cascade_{tag}",
                    title=f"Resonance cascade: '{tag}'",
                    description=f"Tag '{tag}' appeared {count} times in the last 3 days — "
                    f"a resonance cascade indicating heightened attention on this topic.",
                    confidence=min(0.95, 0.4 + count * 0.08),
                    source="resonance_cascade",
                    metadata={"tag": tag, "burst_count": count},
                )
            )
        return insights

    def _detect_novelty_spikes(self) -> list[EmergenceInsight]:
        """Find tags that are newly appearing or suddenly increasing in frequency."""
        try:
            rows = scan_query_all(
                "SELECT recent.tag, "
                "recent.recent_count, "
                "COALESCE(historical.hist_count, 0) as hist_count "
                "FROM ("
                "  SELECT t.tag, COUNT(*) as recent_count "
                "  FROM tags t JOIN memories m ON t.memory_id = m.id "
                "  WHERE m.created_at > datetime('now', '-3 days') "
                "  GROUP BY t.tag"
                ") recent "
                "LEFT JOIN ("
                "  SELECT t.tag, COUNT(*) as hist_count "
                "  FROM tags t JOIN memories m ON t.memory_id = m.id "
                "  WHERE m.created_at BETWEEN datetime('now', '-33 days') AND datetime('now', '-3 days') "
                "  GROUP BY t.tag"
                ") historical ON recent.tag = historical.tag "
                "WHERE recent.recent_count >= 3 "
                "  AND (historical.hist_count = 0 OR recent.recent_count > historical.hist_count * 2) "
                "ORDER BY recent.recent_count DESC LIMIT 10"
            )
        except Exception as e:
            logger.debug("Novelty spike detection skipped: %s", e, exc_info=True)
            return []

        insights: list[EmergenceInsight] = []
        for r in rows:
            tag, recent, hist = r["tag"], r["recent_count"], r["hist_count"]
            if _is_noise_tag(tag):
                continue
            if hist == 0:
                desc = f"Tag '{tag}' is brand new — {recent} appearances in the last 3 days with zero prior history."
            else:
                desc = f"Tag '{tag}' spiked from {hist} (30-day baseline) to {recent} (last 3 days) — "
                desc += f"a {recent / max(hist, 1):.1f}x increase indicating a novelty spike."
            insights.append(
                EmergenceInsight(
                    id=f"novelty_{tag}",
                    title=f"Novelty spike: '{tag}'",
                    description=desc,
                    confidence=min(0.95, 0.5 + (recent - hist) * 0.1),
                    source="novelty_spike",
                    metadata={"tag": tag, "recent_count": recent, "hist_count": hist},
                )
            )
        return insights

    def _detect_cross_domain_bridges(self) -> list[EmergenceInsight]:
        """Find memories that bridge previously separate constellations."""
        try:
            from whitemagic.core.intelligence.core_access import get_core_access

            cal = get_core_access()
        except Exception as e:
            logger.debug(
                "Cross-domain bridge detection skipped (no CoreAccess): %s",
                e,
                exc_info=True,
            )
            return []

        bridges = cal.find_constellation_bridges(limit=10) if cal else []
        if not bridges:
            return []

        insights: list[EmergenceInsight] = []
        for b in bridges[:5]:
            c1, c2 = b.get("constellation_1", "?"), b.get("constellation_2", "?")
            strength = b.get("bridge_strength", 0.5)
            insights.append(
                EmergenceInsight(
                    id=f"bridge_{c1}_{c2}",
                    title=f"Cross-domain bridge: {c1} ↔ {c2}",
                    description=f"Constellations '{c1}' and '{c2}' are forming a bridge "
                    f"(strength: {strength:.2f}) — previously separate domains converging.",
                    confidence=min(0.95, strength),
                    source="cross_domain",
                    metadata={
                        "constellation_1": c1,
                        "constellation_2": c2,
                        "strength": strength,
                    },
                )
            )
        return insights

    def _detect_creative_tensions(self) -> list[EmergenceInsight]:
        """Surface bicameral creative tensions as emergence insights.

        When the BicameralReasoner produces low-confidence results (tension
        between left/right hemispheres), it indicates the system is
        grappling with a problem that doesn't have a clear analytical or
        creative solution — an emergence signal worth surfacing.
        """
        if not self._creative_tensions:
            return []

        insights: list[EmergenceInsight] = []
        # Group by query prefix to avoid duplicates
        seen_queries: set[str] = set()

        for ct in self._creative_tensions[-10:]:
            query = ct.get("query", "")[:80]
            if query in seen_queries:
                continue
            seen_queries.add(query)

            tension = ct.get("tension", 0.0)
            confidence = ct.get("confidence", 0.0)
            dominant = ct.get("dominant", "balanced")

            # Only surface if tension is meaningful (>0.4)
            if tension < 0.4:
                continue

            insights.append(
                EmergenceInsight(
                    id=f"creative_tension_{hash(query) % 100000}",
                    title=f"Creative tension: {query[:60]}",
                    description=(
                        f"Bicameral reasoning produced a creative tension "
                        f"(tension={tension:.2f}, confidence={confidence:.2f}, "
                        f"dominant={dominant}). The analytical and creative "
                        f"hemispheres disagree — this may indicate an emerging "
                        f"problem space that requires novel approaches."
                    ),
                    confidence=min(0.9, 0.5 + tension * 0.3),
                    source="creative_tension",
                    metadata={
                        "query": query,
                        "tension": tension,
                        "confidence": confidence,
                        "dominant": dominant,
                    },
                )
            )
        return insights


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
