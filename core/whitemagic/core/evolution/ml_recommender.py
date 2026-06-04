"""
ML-Based Tool Recommendation System
====================================

Predicts next tools based on discovered event patterns.
Uses lightweight transformer trained on event sequences.
"""

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolPrediction:
    """A predicted next tool with confidence."""
    tool_name: str
    confidence: float
    reasoning: str
    pattern_support: int  # How many patterns support this prediction


class ToolRecommender:
    """
    ML-based tool recommendation system.

    Learns from discovered patterns to predict next tools.
    Uses simple n-gram model for now (can upgrade to transformer later).
    """

    def __init__(self, max_history: int = 100):
        self.max_history = max_history

        # Tool sequence history
        self.tool_history: deque = deque(maxlen=max_history)

        # Learned patterns: (tool1, tool2) -> count
        self.bigram_counts: dict[tuple[str, str], int] = defaultdict(int)

        # Learned patterns: (tool1, tool2, tool3) -> count
        self.trigram_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        # Tool frequency
        self.tool_frequency: dict[str, int] = defaultdict(int)

        # Total sequences seen
        self.sequences_seen = 0

        logger.info("🤖 ML Tool Recommender initialized")

    def record_tool_call(self, tool_name: str):
        """Record a tool call to update the model."""
        self.tool_history.append({
            "tool": tool_name,
            "timestamp": datetime.now(),
        })

        self.tool_frequency[tool_name] += 1

        # Update bigrams
        if len(self.tool_history) >= 2:
            prev_tool = self.tool_history[-2]["tool"]
            self.bigram_counts[(prev_tool, tool_name)] += 1

        # Update trigrams
        if len(self.tool_history) >= 3:
            prev_prev_tool = self.tool_history[-3]["tool"]
            prev_tool = self.tool_history[-2]["tool"]
            self.trigram_counts[(prev_prev_tool, prev_tool, tool_name)] += 1

        self.sequences_seen += 1

    def predict_next_tools(self, top_k: int = 5, min_confidence: float = 0.1) -> list[ToolPrediction]:
        """
        Predict the most likely next tools.

        Args:
            top_k: Number of predictions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of ToolPrediction objects, sorted by confidence
        """
        if len(self.tool_history) == 0:
            return []

        predictions: dict[str, ToolPrediction] = {}

        # Use trigram model if we have enough history
        if len(self.tool_history) >= 2:
            prev_prev_tool = self.tool_history[-2]["tool"]
            prev_tool = self.tool_history[-1]["tool"]

            # Find all trigrams starting with (prev_prev, prev)
            trigram_prefix = (prev_prev_tool, prev_tool)
            matching_trigrams = {
                trigram: count
                for trigram, count in self.trigram_counts.items()
                if trigram[:2] == trigram_prefix
            }

            if matching_trigrams:
                total_count = sum(matching_trigrams.values())

                for trigram, count in matching_trigrams.items():
                    next_tool = trigram[2]
                    confidence = count / total_count

                    if next_tool not in predictions or predictions[next_tool].confidence < confidence:
                        predictions[next_tool] = ToolPrediction(
                            tool_name=next_tool,
                            confidence=confidence,
                            reasoning=f"Trigram pattern: {prev_prev_tool} → {prev_tool} → {next_tool}",
                            pattern_support=count
                        )

        # Use bigram model
        if len(self.tool_history) >= 1:
            prev_tool = self.tool_history[-1]["tool"]

            # Find all bigrams starting with prev_tool
            matching_bigrams = {
                bigram: count
                for bigram, count in self.bigram_counts.items()
                if bigram[0] == prev_tool
            }

            if matching_bigrams:
                total_count = sum(matching_bigrams.values())

                for bigram, count in matching_bigrams.items():
                    next_tool = bigram[1]
                    confidence = count / total_count

                    # Combine with trigram prediction if exists
                    if next_tool in predictions:
                        # Average the confidences (weighted by pattern length)
                        predictions[next_tool].confidence = (
                            predictions[next_tool].confidence * 0.7 +  # Trigram weight
                            confidence * 0.3  # Bigram weight
                        )
                        predictions[next_tool].reasoning += f" + Bigram: {prev_tool} → {next_tool}"
                        predictions[next_tool].pattern_support += count
                    else:
                        predictions[next_tool] = ToolPrediction(
                            tool_name=next_tool,
                            confidence=confidence,
                            reasoning=f"Bigram pattern: {prev_tool} → {next_tool}",
                            pattern_support=count
                        )

        # Filter by confidence and sort
        filtered = [
            pred for pred in predictions.values()
            if pred.confidence >= min_confidence
        ]

        sorted_predictions = sorted(
            filtered,
            key=lambda x: (x.confidence, x.pattern_support),
            reverse=True
        )

        return sorted_predictions[:top_k]

    def get_tool_statistics(self) -> dict[str, Any]:
        """Get statistics about learned patterns."""
        return {
            "sequences_seen": self.sequences_seen,
            "unique_tools": len(self.tool_frequency),
            "bigram_patterns": len(self.bigram_counts),
            "trigram_patterns": len(self.trigram_counts),
            "most_common_tools": sorted(
                self.tool_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }

    def train_from_patterns(self, patterns: list[dict[str, Any]]):
        """
        Train the model from discovered patterns.

        Args:
            patterns: List of pattern dictionaries with 'sequence' key
        """
        for pattern in patterns:
            sequence = pattern.get("sequence", [])
            frequency = pattern.get("frequency", 1)

            # Record each sequence multiple times based on frequency
            for _ in range(min(frequency, 100)):  # Cap to avoid overwhelming
                for tool in sequence:
                    self.record_tool_call(tool)

        logger.info(f"📚 Trained on {len(patterns)} patterns")

    def export_model(self, filepath: str):
        """Export the learned model to JSON."""
        model_data = {
            "bigrams": {
                f"{k[0]}→{k[1]}": v
                for k, v in self.bigram_counts.items()
            },
            "trigrams": {
                f"{k[0]}→{k[1]}→{k[2]}": v
                for k, v in self.trigram_counts.items()
            },
            "tool_frequency": dict(self.tool_frequency),
            "sequences_seen": self.sequences_seen,
            "exported_at": datetime.now().isoformat(),
        }

        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)

        logger.info(f"💾 Model exported to {filepath}")

    def import_model(self, filepath: str):
        """Import a learned model from JSON."""
        with open(filepath) as f:
            model_data = json.load(f)

        # Parse bigrams
        for key, count in model_data.get("bigrams", {}).items():
            tools = key.split("→")
            if len(tools) == 2:
                self.bigram_counts[(tools[0], tools[1])] = count

        # Parse trigrams
        for key, count in model_data.get("trigrams", {}).items():
            tools = key.split("→")
            if len(tools) == 3:
                self.trigram_counts[(tools[0], tools[1], tools[2])] = count

        # Load tool frequency
        self.tool_frequency = defaultdict(int, model_data.get("tool_frequency", {}))

        self.sequences_seen = model_data.get("sequences_seen", 0)

        logger.info(f"📥 Model imported from {filepath}")


class AutocastEnhancer:
    """
    Enhances the autocast system with ML predictions.

    Integrates with existing tool discovery to provide intelligent suggestions.
    """

    def __init__(self, recommender: ToolRecommender | None = None):
        self.recommender = recommender or ToolRecommender()
        self.prediction_cache: dict[str, list[ToolPrediction]] = {}
        self.cache_ttl_seconds = 60

    def get_smart_suggestions(
        self,
        current_context: dict[str, Any],
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Get smart tool suggestions based on context and ML predictions.

        Args:
            current_context: Current execution context (recent tools, etc.)
            top_k: Number of suggestions to return

        Returns:
            List of tool suggestions with confidence and reasoning
        """
        # Get ML predictions
        predictions = self.recommender.predict_next_tools(top_k=top_k)

        # Format for autocast
        suggestions = []
        for pred in predictions:
            suggestions.append({
                "tool_name": pred.tool_name,
                "confidence": pred.confidence,
                "reasoning": pred.reasoning,
                "source": "ml_prediction",
                "pattern_support": pred.pattern_support,
            })

        return suggestions

    def record_tool_execution(self, tool_name: str, success: bool):
        """
        Record tool execution for learning.

        Args:
            tool_name: Name of the tool executed
            success: Whether execution was successful
        """
        self.recommender.record_tool_call(tool_name)

        # Clear cache after new data
        self.prediction_cache.clear()


# Global instance
_recommender: ToolRecommender | None = None


def get_tool_recommender() -> ToolRecommender:
    """Get singleton tool recommender."""
    global _recommender
    if _recommender is None:
        _recommender = ToolRecommender()
    return _recommender


def predict_next_tools(top_k: int = 5) -> list[ToolPrediction]:
    """Convenience function to get predictions."""
    return get_tool_recommender().predict_next_tools(top_k=top_k)


def record_tool_call(tool_name: str):
    """Convenience function to record tool calls."""
    get_tool_recommender().record_tool_call(tool_name)
