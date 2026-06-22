# ruff: noqa: BLE001
"""
Rubedo: The Stage of Synthesis
==============================
The final stage of the Great Work.
Synthesizes purified pattern clusters into "Golden Rules" (Philosopher's Stone).
Uses Local LLM (if available) or simple extraction to generate the rules.

Usage:
    synthesizer = RubedoSynthesizer()
    rules = synthesizer.synthesize(clusters)
"""

import logging
from collections import Counter
from typing import Any

# Import Local LLM for synthesis
try:
    from whitemagic.inference.local_llm import LocalLLM
except ImportError:
    LocalLLM = None  # type: ignore

logger = logging.getLogger(__name__)

class RubedoSynthesizer:
    """Synthesizes clusters into Golden Rules."""

    def __init__(self):
        self.llm: Any | None = None
        if LocalLLM is not None:
            self.llm = LocalLLM()
            if self.llm is not None and not self.llm.is_available:
                logger.warning("Local LLM not available. Rubedo will use heuristic synthesis.")
                self.llm = None

    def synthesize(self, clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Turn clusters into rules.
        """
        golden_rules = []

        for cluster in clusters:
            rule = self._synthesize_cluster(cluster)
            if rule:
                golden_rules.append(rule)

        return golden_rules

    def _synthesize_cluster(self, cluster: dict[str, Any]) -> dict[str, Any] | None:
        """
        Generate a rule for a single cluster.
        """
        items = cluster.get('items', [])
        if not items:
            return None

        # Extract common terms for title
        all_text = " ".join([m.get('title', '') for m in items])
        common_words = [w for w in all_text.split() if len(w) > 4]
        top_words = [w for w, c in Counter(common_words).most_common(3)]

        rule_title = f"Pattern: {' '.join(top_words).title()}"
        rule_body = "Captured pattern from multiple memories."

        # Try LLM Synthesis
        if self.llm:
            try:
                # Sample content
                samples = [m.get('content', '')[:300] for m in items[:5]]
                prompt = (
                    "Synthesize a single 'Golden Rule' or principle from these memory excerpts.\n"
                    "The rule should be a concise actionable instruction.\n\n"
                    "Excerpts:\n" + "\n---\n".join(samples) + "\n\n"
                    "Golden Rule:"
                )
                response = self.llm.complete(prompt, max_tokens=64)
                if response and not response.startswith("Error"):
                    rule_body = response.strip()
                    # Improve title based on body
                    rule_title = self.llm.complete(f"Generate a 3-5 word title for this rule: {rule_body}", max_tokens=10).strip().strip('"')
            except Exception as e:
                logger.warning("LLM synthesis failed: %s", e, exc_info=True)

        return {
            "id": f"rule_{cluster['cluster_id']}",
            "title": rule_title,
            "description": rule_body,
            "support_count": cluster['size'],
            "example_ids": [m['id'] for m in items[:3]]
        }
