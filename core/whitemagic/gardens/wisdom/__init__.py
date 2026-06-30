"""Wisdom Garden — Search, Recall & Vector Intelligence.

Mansion: #6 Winnowing Basket (箕 Ji)
Quadrant: Eastern (Azure Dragon)
PRAT Gana: gana_winnowing_basket — search, recall, vector search,
    hybrid recall, rerank, JIT research

The Winnowing Basket Gana discerns. The Wisdom Garden provides the
substrate for intelligent search: tracking query patterns, recall
quality, vector search analytics, and the wisdom that comes from
knowing what to look for.

Holographic Integration:
- Balanced (X-axis -0.1) — wisdom is calm, neither pure logic nor emotion
- Abstract (Y-axis +0.5) — wisdom generalizes from specifics
- Past-informed (Z-axis -0.2) — wisdom learns from experience
- High importance (W-axis +0.35) — wisdom guides all else
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any

from whitemagic.core.resonance.gan_ying_enhanced import EventType
from whitemagic.core.resonance.integration_helpers import (
    GanYingMixin,
    init_listeners,
    listen_for,
)
from whitemagic.gardens.base_garden import BaseGarden, CoordinateBias

logger = logging.getLogger(__name__)


class WisdomGarden(BaseGarden, GanYingMixin):
    """Garden of Wisdom — Search and recall intelligence engine.

    Serves the Winnowing Basket Gana's search tools by maintaining:
    - Query pattern log for identifying common search themes
    - Recall quality tracking for search result relevance
    - Wisdom insights extracted from accumulated knowledge
    - Discernment metrics for filtering quality
    """

    name = "wisdom"
    category = "search_intelligence"
    resonance_partners = ["truth", "mystery", "patience", "stillness"]
    mansion_number = 6
    gana_name = "gana_winnowing_basket"

    def __init__(self) -> None:
        BaseGarden.__init__(self)
        self._lock = threading.Lock()
        self.query_log: deque[dict[str, Any]] = deque(maxlen=200)
        self.wisdom_insights: deque[dict[str, Any]] = deque(maxlen=100)
        self.recall_quality_scores: deque[float] = deque(maxlen=50)
        self.wisdom_level: float = 0.0
        self._total_queries: int = 0
        self._total_insights: int = 0
        init_listeners(self)
        self.emit(EventType.SYSTEM_STARTED, {"garden": "Wisdom", "mansion": 6})

    def get_name(self) -> str:
        return "wisdom"

    def get_coordinate_bias(self) -> CoordinateBias:
        return CoordinateBias(x=-0.1, y=0.5, z=-0.2, w=0.35)

    def record_query(
        self, query: str, result_count: int = 0, quality_score: float = 0.0
    ) -> dict[str, Any]:
        """Record a search query for pattern analysis."""
        entry = {
            "query": query,
            "result_count": result_count,
            "quality_score": quality_score,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.query_log.append(entry)
            self._total_queries += 1
            if quality_score > 0:
                self.recall_quality_scores.append(quality_score)
        return entry

    def record_insight(
        self, insight: str, source: str = "unknown", confidence: float = 0.7
    ) -> dict[str, Any]:
        """Record a wisdom insight — a distilled understanding."""
        entry = {
            "insight": insight,
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.wisdom_insights.append(entry)
            self._total_insights += 1
            self.wisdom_level = min(1.0, self.wisdom_level + 0.03)
        self.emit(EventType.WISDOM_INTEGRATED, entry)
        return entry

    def get_search_summary(self) -> dict[str, Any]:
        """Get summary of search activity for the Winnowing Basket tools."""
        with self._lock:
            avg_quality = (
                sum(self.recall_quality_scores) / len(self.recall_quality_scores)
                if self.recall_quality_scores
                else 0.0
            )
            return {
                "total_queries": self._total_queries,
                "total_insights": self._total_insights,
                "avg_recall_quality": round(avg_quality, 3),
                "wisdom_level": round(self.wisdom_level, 3),
                "recent_queries": list(self.query_log)[-5:],
            }

    def get_status(self) -> dict[str, Any]:
        base = super().get_status()
        base.update(
            {
                "mansion": self.mansion_number,
                "gana": self.gana_name,
                "total_queries": self._total_queries,
                "total_insights": self._total_insights,
                "wisdom_level": round(self.wisdom_level, 3),
            }
        )
        return base

    @listen_for(EventType.TRUTH_SPOKEN)
    def on_truth(self, event: Any) -> None:
        """Truth spoken generates wisdom."""
        self.record_insight("Truth reveals wisdom", source="truth", confidence=0.8)

    @listen_for(EventType.PATTERN_DETECTED)
    def on_pattern(self, event: Any) -> None:
        """Pattern detection feeds wisdom."""
        self.record_insight(
            "Pattern recognized as wisdom", source="pattern", confidence=0.7
        )


_instance = None


def get_wisdom_garden() -> WisdomGarden:
    global _instance
    if _instance is None:
        _instance = WisdomGarden()
    return _instance
