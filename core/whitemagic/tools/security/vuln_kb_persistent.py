"""Persistent Vulnerability Knowledge Base — SQLite-backed vuln pattern storage.

Wraps VulnKnowledgeBase with automatic SQLite persistence via safe_connect().
Patterns are auto-loaded on startup and auto-saved on add_pattern() and ingest_audit_report().
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.tools.security.vuln_knowledge import (
    VulnerabilityPattern,
    VulnKnowledgeBase,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vuln_patterns (
    pattern_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'unknown',
    severity TEXT NOT NULL DEFAULT 'info',
    description TEXT NOT NULL DEFAULT '',
    detection_regex TEXT,
    detection_keywords TEXT NOT NULL DEFAULT '',
    false_positive_indicators TEXT NOT NULL DEFAULT '',
    mitigation TEXT NOT NULL DEFAULT '',
    cwe_id TEXT,
    swc_id TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence REAL NOT NULL DEFAULT 1.0,
    last_seen REAL NOT NULL DEFAULT 0.0,
    times_seen INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS semantic_attack_corpus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_text TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'general',
    severity TEXT NOT NULL DEFAULT 'medium',
    source TEXT NOT NULL DEFAULT 'manual',
    added_at REAL NOT NULL DEFAULT 0.0
);
"""


def _kw_list_to_str(keywords: list[str]) -> str:
    return "|".join(keywords)


def _str_to_kw_list(s: str) -> list[str]:
    if not s:
        return []
    return s.split("|")


class PersistentVulnKnowledgeBase(VulnKnowledgeBase):
    """SQLite-backed vulnerability knowledge base.

    Auto-loads patterns from SQLite on init, auto-saves on modifications.
    Falls back to in-memory if SQLite is unavailable.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self._db_path = db_path
        self._db_available = False
        if db_path is not None:
            self._init_db()
            self._load_from_db()

    def _init_db(self) -> None:
        """Initialize SQLite tables."""
        if self._db_path is None:
            return
        try:
            from whitemagic.core.memory.db_manager import safe_connect

            with safe_connect(str(self._db_path)) as conn:
                conn.executescript(_SCHEMA)
                conn.commit()
            self._db_available = True
        except Exception as e:  # noqa: BLE001
            logger.debug("PersistentVulnKB: SQLite init failed (%s), using in-memory", e)
            self._db_available = False

    def _load_from_db(self) -> None:
        """Load all patterns from SQLite into memory."""
        if not self._db_available or self._db_path is None:
            return
        try:
            from whitemagic.core.memory.db_manager import safe_connect

            with safe_connect(str(self._db_path)) as conn:
                rows = conn.execute(
                    "SELECT pattern_id, name, category, severity, description, detection_regex, detection_keywords, false_positive_indicators, mitigation, cwe_id, swc_id, source, confidence, last_seen, times_seen FROM vuln_patterns WHERE source != 'builtin'"
                ).fetchall()
            for row in rows:
                pattern = VulnerabilityPattern(
                    pattern_id=row[0],
                    name=row[1],
                    category=row[2],
                    severity=row[3],
                    description=row[4],
                    detection_regex=row[5],
                    detection_keywords=_str_to_kw_list(row[6]),
                    false_positive_indicators=_str_to_kw_list(row[7]),
                    mitigation=row[8],
                    cwe_id=row[9],
                    swc_id=row[10],
                    source=row[11],
                    confidence=row[12],
                    last_seen=row[13],
                    times_seen=row[14],
                )
                self._patterns[pattern.pattern_id] = pattern
            logger.debug("PersistentVulnKB: loaded %d patterns from SQLite", len(rows))
        except Exception as e:  # noqa: BLE001
            logger.debug("PersistentVulnKB: load failed: %s", e)

    def _save_pattern(self, pattern: VulnerabilityPattern) -> None:
        """Save a single pattern to SQLite."""
        if not self._db_available or self._db_path is None:
            return
        try:
            from whitemagic.core.memory.db_manager import safe_connect

            with safe_connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO vuln_patterns
                    (pattern_id, name, category, severity, description, detection_regex,
                     detection_keywords, false_positive_indicators, mitigation, cwe_id,
                     swc_id, source, confidence, last_seen, times_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        pattern.pattern_id,
                        pattern.name,
                        pattern.category,
                        pattern.severity,
                        pattern.description,
                        pattern.detection_regex,
                        _kw_list_to_str(pattern.detection_keywords),
                        _kw_list_to_str(pattern.false_positive_indicators),
                        pattern.mitigation,
                        pattern.cwe_id,
                        pattern.swc_id,
                        pattern.source,
                        pattern.confidence,
                        pattern.last_seen,
                        pattern.times_seen,
                    ),
                )
                conn.commit()
        except Exception as e:  # noqa: BLE001
            logger.debug("PersistentVulnKB: save failed: %s", e)

    def add_pattern(self, pattern: VulnerabilityPattern) -> None:
        """Add a pattern and persist to SQLite."""
        super().add_pattern(pattern)
        self._save_pattern(pattern)

    def ingest_audit_report(self, report_text: str, source: str = "audit_report") -> int:
        """Extract patterns from audit report and persist to SQLite."""
        count = super().ingest_audit_report(report_text, source)
        # Save newly ingested patterns
        if self._db_available and count > 0:
            for pattern in self._patterns.values():
                if pattern.source == source:
                    self._save_pattern(pattern)
        return count

    def increment_seen(self, pattern_id: str) -> None:
        """Increment the times_seen counter and update last_seen."""
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            return
        pattern.times_seen += 1
        pattern.last_seen = time.time()
        self._save_pattern(pattern)

    # ── Semantic attack corpus ───────────────────────────────────────────

    def add_attack_pattern(
        self,
        pattern_text: str,
        category: str = "general",
        severity: str = "medium",
        source: str = "manual",
    ) -> bool:
        """Add a semantic attack pattern to the corpus."""
        if not self._db_available or self._db_path is None:
            return False
        try:
            from whitemagic.core.memory.db_manager import safe_connect

            with safe_connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO semantic_attack_corpus
                    (pattern_text, category, severity, source, added_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (pattern_text, category, severity, source, time.time()),
                )
                conn.commit()
            return True
        except Exception as e:  # noqa: BLE001
            logger.debug("PersistentVulnKB: add_attack_pattern failed: %s", e)
            return False

    def get_attack_patterns(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve semantic attack patterns."""
        if not self._db_available or self._db_path is None:
            return []
        try:
            from whitemagic.core.memory.db_manager import safe_connect

            with safe_connect(str(self._db_path)) as conn:
                if category:
                    rows = conn.execute(
                        "SELECT pattern_text, category, severity, source, added_at FROM semantic_attack_corpus WHERE category = ? ORDER BY added_at DESC LIMIT ?",
                        (category, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT pattern_text, category, severity, source, added_at FROM semantic_attack_corpus ORDER BY added_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            return [{"pattern_text": r[0], "category": r[1], "severity": r[2], "source": r[3], "added_at": r[4]} for r in rows]
        except Exception as e:  # noqa: BLE001
            logger.debug("PersistentVulnKB: get_attack_patterns failed: %s", e)
            return []

    def status(self) -> dict[str, Any]:
        base = super().status()
        base["persistent"] = self._db_available
        if self._db_path:
            base["db_path"] = str(self._db_path)
        return base


_persistent_kb: PersistentVulnKnowledgeBase | None = None


def get_persistent_vuln_kb() -> PersistentVulnKnowledgeBase:
    """Get the global PersistentVulnKnowledgeBase singleton."""
    global _persistent_kb
    if _persistent_kb is None:
        import os
        from pathlib import Path

        wm_root = os.environ.get("WM_ROOT", os.path.expanduser("~/.whitemagic"))
        db_path = Path(wm_root) / "security" / "vuln_kb.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _persistent_kb = PersistentVulnKnowledgeBase(db_path)
    return _persistent_kb
