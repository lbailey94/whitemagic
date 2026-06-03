"""Association Miner — Keyword extraction and overlap scoring for memory links."""

from __future__ import annotations

import re
from typing import Set

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "and", "but", "or", "yet", "so", "if",
    "because", "although", "though", "while", "where", "when", "that",
    "which", "who", "whom", "whose", "what", "this", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
}


class AssociationMiner:
    """Extract keywords and compute overlap scores for memory associations."""

    def __init__(self, persist: bool = True) -> None:
        self.persist = persist
        self.total_runs = 0

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract lowercase alphanumeric keywords, excluding stop words."""
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return {w for w in words if w not in _STOP_WORDS and len(w) > 2}

    @staticmethod
    def _compute_overlap(a: Set[str], b: Set[str]) -> tuple[float, Set[str]]:
        """Compute Jaccard-like overlap score and shared keywords."""
        if not a or not b:
            return 0.0, set()
        shared = a & b
        score = len(shared) / max(len(a), len(b))
        return score, shared

    def get_stats(self) -> dict[str, object]:
        return {"total_runs": self.total_runs, "persist": self.persist}
