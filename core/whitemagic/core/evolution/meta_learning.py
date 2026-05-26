"""Meta-Learning System - Patterns About Patterns

Learns which types of patterns work best, when to apply them,
and how to discover new patterns. This is the system learning
about its own learning process.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from whitemagic.config.paths import MEMORY_DIR


@dataclass
class PatternMetrics:
    """Metrics about a pattern's effectiveness"""
    pattern_id: str
    pattern_type: str
    total_applications: int
    successful_applications: int
    failed_applications: int
    avg_performance_gain: float
    avg_quality_score: float
    avg_confidence: float
    source_count: int
    sources: List[str]
    first_seen: str
    last_applied: str

    @property
    def success_rate(self) -> float:
        if self.total_applications == 0:
            return 0.0
        return self.successful_applications / self.total_applications

    @property
    def effectiveness_score(self) -> float:
        """Combined score: success_rate * avg_performance_gain * avg_quality_score"""
        return self.success_rate * self.avg_performance_gain * self.avg_quality_score


@dataclass
class MetaPattern:
    """A pattern about patterns - meta-level insights"""
    meta_pattern_id: str
    insight: str
    evidence_count: int
    confidence: float
    discovered_at: str
    pattern_types_involved: List[str]

    # Examples of meta-patterns:
    # - "Cross-source patterns have 2.5x higher success rate"
    # - "Optimization patterns work best on hot paths"
    # - "Consciousness patterns improve with reflection patterns"
    # - "Patterns with >3 sources rarely fail"


class MetaLearningEngine:
    """Learns about the learning process itself"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(MEMORY_DIR / "meta_learning.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize meta-learning database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Pattern metrics table
        c.execute('''
            CREATE TABLE IF NOT EXISTS pattern_metrics (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                total_applications INTEGER DEFAULT 0,
                successful_applications INTEGER DEFAULT 0,
                failed_applications INTEGER DEFAULT 0,
                avg_performance_gain REAL DEFAULT 0.0,
                avg_quality_score REAL DEFAULT 0.0,
                avg_confidence REAL DEFAULT 0.0,
                source_count INTEGER DEFAULT 0,
                sources TEXT,
                first_seen TEXT,
                last_applied TEXT
            )
        ''')

        # Meta-patterns table
        c.execute('''
            CREATE TABLE IF NOT EXISTS meta_patterns (
                meta_pattern_id TEXT PRIMARY KEY,
                insight TEXT,
                evidence_count INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.0,
                discovered_at TEXT,
                pattern_types_involved TEXT
            )
        ''')

        # Pattern correlations table
        c.execute('''
            CREATE TABLE IF NOT EXISTS pattern_correlations (
                pattern_a TEXT,
                pattern_b TEXT,
                co_occurrence_count INTEGER DEFAULT 0,
                combined_success_rate REAL DEFAULT 0.0,
                synergy_score REAL DEFAULT 0.0,
                PRIMARY KEY (pattern_a, pattern_b)
            )
        ''')

        conn.commit()
        conn.close()

    def update_pattern_metrics(
        self,
        pattern_id: str,
        pattern_type: str,
        success: bool,
        performance_gain: float,
        quality_score: float,
        confidence: float,
        sources: List[str]
    ) -> None:
        """Update metrics for a pattern after application"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get existing metrics
        c.execute('SELECT * FROM pattern_metrics WHERE pattern_id = ?', (pattern_id,))
        row = c.fetchone()

        now = datetime.now().isoformat()

        if row is None:
            # New pattern
            c.execute('''
                INSERT INTO pattern_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern_id, pattern_type, 1,
                1 if success else 0,
                0 if success else 1,
                performance_gain, quality_score, confidence,
                len(sources), json.dumps(sources),
                now, now
            ))
        else:
            # Update existing
            total = row[2] + 1
            successful = row[3] + (1 if success else 0)
            failed = row[4] + (0 if success else 1)

            # Running average
            new_avg_perf = (row[5] * row[2] + performance_gain) / total
            new_avg_quality = (row[6] * row[2] + quality_score) / total
            new_avg_conf = (row[7] * row[2] + confidence) / total

            c.execute('''
                UPDATE pattern_metrics
                SET total_applications = ?,
                    successful_applications = ?,
                    failed_applications = ?,
                    avg_performance_gain = ?,
                    avg_quality_score = ?,
                    avg_confidence = ?,
                    last_applied = ?
                WHERE pattern_id = ?
            ''', (total, successful, failed, new_avg_perf, new_avg_quality, new_avg_conf, now, pattern_id))

        conn.commit()
        conn.close()

    def discover_meta_patterns(self) -> List[MetaPattern]:
        """Analyze pattern metrics to discover meta-patterns"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        meta_patterns = []

        # Meta-pattern 1: Cross-source effectiveness
        c.execute('''
            SELECT
                AVG(CASE WHEN source_count >= 2 THEN
                    CAST(successful_applications AS REAL) / total_applications
                    ELSE 0 END) as multi_source_success,
                AVG(CASE WHEN source_count = 1 THEN
                    CAST(successful_applications AS REAL) / total_applications
                    ELSE 0 END) as single_source_success
            FROM pattern_metrics
            WHERE total_applications > 0
        ''')
        row = c.fetchone()
        if row and row[0] and row[1]:
            multi_success = row[0]
            single_success = row[1]
            if multi_success > single_success * 1.2:
                ratio = multi_success / single_success if single_success > 0 else 0
                meta_patterns.append(MetaPattern(
                    meta_pattern_id='cross_source_advantage',
                    insight=f'Cross-source patterns have {ratio:.1f}x higher success rate',
                    evidence_count=10,
                    confidence=0.9,
                    discovered_at=datetime.now().isoformat(),
                    pattern_types_involved=['all']
                ))

        # Meta-pattern 2: Performance gain by pattern type
        c.execute('''
            SELECT pattern_type, AVG(avg_performance_gain), COUNT(*)
            FROM pattern_metrics
            WHERE total_applications > 0
            GROUP BY pattern_type
            HAVING COUNT(*) >= 2
            ORDER BY AVG(avg_performance_gain) DESC
            LIMIT 3
        ''')
        for row in c.fetchall():
            pattern_type, avg_gain, count = row
            if avg_gain > 10.0:
                meta_patterns.append(MetaPattern(
                    meta_pattern_id=f'high_impact_{pattern_type}',
                    insight=f'{pattern_type} patterns deliver {avg_gain:.1f}x average performance gain',
                    evidence_count=count,
                    confidence=min(0.95, 0.5 + (count * 0.1)),
                    discovered_at=datetime.now().isoformat(),
                    pattern_types_involved=[pattern_type]
                ))

        # Meta-pattern 3: Confidence threshold effectiveness
        c.execute('''
            SELECT
                AVG(CASE WHEN avg_confidence >= 0.9 THEN
                    CAST(successful_applications AS REAL) / total_applications
                    ELSE 0 END) as high_conf_success,
                AVG(CASE WHEN avg_confidence < 0.9 THEN
                    CAST(successful_applications AS REAL) / total_applications
                    ELSE 0 END) as low_conf_success
            FROM pattern_metrics
            WHERE total_applications > 0
        ''')
        row = c.fetchone()
        if row and row[0] and row[1]:
            high_conf = row[0]
            low_conf = row[1]
            if high_conf > low_conf * 1.3:
                meta_patterns.append(MetaPattern(
                    meta_pattern_id='confidence_threshold_validation',
                    insight=f'Patterns with ≥90% confidence have {high_conf/low_conf:.1f}x better success rate',
                    evidence_count=15,
                    confidence=0.85,
                    discovered_at=datetime.now().isoformat(),
                    pattern_types_involved=['all']
                ))

        conn.close()

        # Save discovered meta-patterns
        self._save_meta_patterns(meta_patterns)

        return meta_patterns

    def _save_meta_patterns(self, meta_patterns: List[MetaPattern]):
        """Save meta-patterns to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # N+1 fix: executemany instead of per-row INSERT loop
        c.executemany(
            'INSERT OR REPLACE INTO meta_patterns VALUES (?, ?, ?, ?, ?, ?)',
            [
                (mp.meta_pattern_id, mp.insight, mp.evidence_count,
                 mp.confidence, mp.discovered_at, json.dumps(mp.pattern_types_involved))
                for mp in meta_patterns
            ]
        )
        conn.commit()
        conn.close()

    def get_pattern_recommendations(
        self,
        context: Dict,
        limit: int = 5
    ) -> List[Tuple[str, float, str]]:
        """Recommend patterns based on context and meta-learning"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get top patterns by effectiveness score
        c.execute('''
            SELECT
                pattern_id,
                pattern_type,
                CAST(successful_applications AS REAL) / total_applications as success_rate,
                avg_performance_gain,
                avg_quality_score,
                source_count
            FROM pattern_metrics
            WHERE total_applications >= 2
            ORDER BY
                (CAST(successful_applications AS REAL) / total_applications) *
                avg_performance_gain *
                avg_quality_score DESC
            LIMIT ?
        ''', (limit,))

        recommendations = []
        for row in c.fetchall():
            pattern_id, pattern_type, success_rate, avg_gain, avg_quality, source_count = row
            effectiveness = success_rate * avg_gain * avg_quality

            reason = f"{pattern_type} pattern: {success_rate:.0%} success, {avg_gain:.1f}x gain"
            if source_count >= 2:
                reason += f", {source_count} sources"

            recommendations.append((pattern_id, effectiveness, reason))

        conn.close()
        return recommendations

    def get_meta_learning_summary(self) -> Dict:
        """Get summary of meta-learning insights"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Overall stats
        c.execute('''
            SELECT
                COUNT(*) as total_patterns,
                SUM(total_applications) as total_applications,
                AVG(CAST(successful_applications AS REAL) / NULLIF(total_applications, 0)) as avg_success_rate,
                AVG(avg_performance_gain) as avg_performance_gain,
                COUNT(CASE WHEN source_count >= 2 THEN 1 END) as multi_source_count
            FROM pattern_metrics
        ''')
        row = c.fetchone()

        # Meta-patterns
        c.execute('SELECT COUNT(*) FROM meta_patterns')
        meta_pattern_count = c.fetchone()[0]

        c.execute('SELECT * FROM meta_patterns ORDER BY confidence DESC')
        meta_patterns = []
        for row in c.fetchall():
            meta_patterns.append({
                'id': row[0],
                'insight': row[1],
                'evidence': row[2],
                'confidence': row[3]
            })

        conn.close()

        return {
            'total_patterns_tracked': row[0] if row else 0,
            'total_applications': row[1] if row else 0,
            'avg_success_rate': row[2] if row else 0.0,
            'avg_performance_gain': row[3] if row else 0.0,
            'multi_source_patterns': row[4] if row else 0,
            'meta_patterns_discovered': meta_pattern_count,
            'top_meta_patterns': meta_patterns[:5]
        }
