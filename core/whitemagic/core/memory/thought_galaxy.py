# ruff: noqa: BLE001
"""
Thought Galaxy (G003)
=====================

Manages the "Thought Galaxy" — a dedicated storage zone for Cognitive Episodes.
Enables introspection, pattern mining, and retrieval of past reasoning strategies.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from whitemagic.core.memory.cognitive_episode import CognitiveEpisode

logger = logging.getLogger(__name__)

class ThoughtGalaxy:
    """Manager for the Thought Galaxy (meta-cognitive memory)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the thought galaxy schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_episodes (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    task_type TEXT,
                    strategy TEXT,
                    thought_trace TEXT,
                    context_summary TEXT,
                    outcome_score REAL,
                    outcome_metrics TEXT,
                    tags TEXT
                )
            """)
            # Index for fast retrieval by task/score
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_task_score ON cognitive_episodes(task_type, outcome_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_strategy ON cognitive_episodes(strategy)")

    def record_episode(self, episode: CognitiveEpisode):
        """Save a cognitive episode to the galaxy."""
        if not episode.id:
            episode.id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cognitive_episodes
                (id, timestamp, task_type, strategy, thought_trace, context_summary,
                 outcome_score, outcome_metrics, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode.id,
                episode.timestamp.isoformat(),
                episode.task_type,
                episode.strategy,
                episode.thought_trace,
                episode.context_summary,
                episode.outcome_score,
                json.dumps(episode.outcome_metrics),
                json.dumps(episode.tags)
            ))
        logger.info(f"Recorded cognitive episode {episode.id} (score: {episode.outcome_score})")

    def recall_best_strategies(self, task_type: str, min_score: float = 0.5, limit: int = 5) -> list[CognitiveEpisode]:
        """Retrieve high-scoring episodes for a similar task, including Golden Rules."""
        episodes = []

        # 1. Fetch from Holocron (The Golden Rules)
        try:
            from whitemagic.alchemy.holocron import Holocron
            holocron = Holocron()
            holocron.load()
            # Use task_type as context for relevance
            rules = holocron.get_relevant_rules(task_type, limit=3)

            for rule in rules:
                # Convert Rule -> Pseudo-Episode
                episodes.append(CognitiveEpisode(
                    id=rule["id"],
                    timestamp=datetime.now(), # Timeless/Now
                    task_type=task_type,
                    strategy="Golden Rule",
                    thought_trace=f"Apply the Golden Rule: {rule['title']}",
                    context_summary=rule["description"],
                    outcome_score=1.1, # Higher than normal max 1.0 to prioritize wisdom
                    outcome_metrics={"source": "holocron", "support": rule["support_count"]},
                    tags=["golden_rule", "wisdom"]
                ))
        except Exception as e:
            logger.warning(f"Failed to retrieve Golden Rules: {e}")

        # 2. Fetch from Galaxy DB
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM cognitive_episodes
                WHERE task_type = ? AND outcome_score >= ?
                ORDER BY outcome_score DESC
                LIMIT ?
            """, (task_type, min_score, limit)).fetchall()

            episodes.extend([self._row_to_episode(row) for row in rows])

        # Sort combined list by score desc
        episodes.sort(key=lambda x: x.outcome_score, reverse=True)
        return episodes[:limit]

    def get_anti_patterns(self, task_type: str | None = None, limit: int = 5) -> list[CognitiveEpisode]:
        """Retrieve lowest-scoring episodes (what NOT to do)."""
        query = "SELECT * FROM cognitive_episodes WHERE outcome_score < 0"
        params = []
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY outcome_score ASC LIMIT ?"
        params.append(str(limit))

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_episode(row) for row in rows]

    def _row_to_episode(self, row: sqlite3.Row) -> CognitiveEpisode:
        """Convert DB row to CognitiveEpisode object."""
        return CognitiveEpisode(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            task_type=row["task_type"],
            strategy=row["strategy"],
            thought_trace=row["thought_trace"],
            context_summary=row["context_summary"],
            outcome_score=row["outcome_score"],
            outcome_metrics=json.loads(row["outcome_metrics"]),
            tags=json.loads(row["tags"])
        )

    def stats(self) -> dict[str, Any]:
        """Return statistics about the thought galaxy."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM cognitive_episodes").fetchone()[0]
            avg_score = conn.execute("SELECT AVG(outcome_score) FROM cognitive_episodes").fetchone()[0] or 0.0

            # Top strategies
            top_strats = conn.execute("""
                SELECT strategy, AVG(outcome_score) as avg_s, COUNT(*) as c
                FROM cognitive_episodes
                GROUP BY strategy
                ORDER BY avg_s DESC LIMIT 5
            """).fetchall()

            return {
                "total_episodes": count,
                "average_score": avg_score,
                "top_strategies": [dict(zip(["strategy", "avg_score", "count"], r)) for r in top_strats]
            }
