"""Adaptive Integration - Pattern Application Engine

Integrates discovered patterns with the AdaptiveSystem for automatic application.
Manages the complete cycle: pattern → application → measurement → learning.
"""

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from whitemagic.core.evolution.autodidactic_loop import (
    AutodidacticLoop,
    PatternApplication,
    PatternOutcome,
)


@dataclass
class DiscoveredPattern:
    """A pattern discovered through mining and cross-validation"""
    pattern_id: str
    tag: str
    confidence: float
    sources: list[str]
    source_count: int
    cv_score: float
    outcome_score: float
    frequency_score: float
    longevity_score: float
    metadata: dict[str, Any]

class AdaptiveIntegration:
    """Manages pattern integration with adaptive systems"""

    def __init__(
        self,
        auto_apply_threshold: float = 0.77,
        manual_review_threshold: float = 0.60,
        autodidactic_loop: AutodidacticLoop | None = None,
    ):
        self.auto_apply_threshold = auto_apply_threshold
        self.manual_review_threshold = manual_review_threshold
        self.autodidactic_loop = autodidactic_loop or AutodidacticLoop()

        # Pattern queues
        self.auto_apply_queue: list[DiscoveredPattern] = []
        self.manual_review_queue: list[DiscoveredPattern] = []
        self.applied_patterns: list[str] = []

    def load_patterns(self, results_file: Path) -> None:
        """Load patterns from cross-validation results"""
        with open(results_file) as f:
            results = json.load(f)

        # Load ultra-high confidence patterns
        for pattern_data in results.get('ultra_high_patterns', []):
            pattern = DiscoveredPattern(
                pattern_id=pattern_data['pattern_id'],
                tag=pattern_data['tag'],
                confidence=pattern_data['confidence'],
                sources=pattern_data['sources'],
                source_count=pattern_data['source_count'],
                cv_score=pattern_data['cv_score'],
                outcome_score=pattern_data['outcome_score'],
                frequency_score=pattern_data['frequency_score'],
                longevity_score=pattern_data['longevity_score'],
                metadata=pattern_data,
            )

            if pattern.confidence >= self.auto_apply_threshold:
                self.auto_apply_queue.append(pattern)
            elif pattern.confidence >= self.manual_review_threshold:
                self.manual_review_queue.append(pattern)

    def apply_pattern(self, pattern: DiscoveredPattern, context: dict[str, Any]) -> str:
        """Apply a pattern and record the application"""
        application_id = str(uuid.uuid4())

        # Record application
        application = PatternApplication(
            application_id=application_id,
            pattern_id=pattern.pattern_id,
            pattern_type=pattern.tag,
            timestamp=time.time(),
            initial_confidence=pattern.confidence,
            context=context,
        )

        self.autodidactic_loop.record_application(application)
        self.applied_patterns.append(pattern.pattern_id)

        return application_id

    def record_outcome(
        self,
        application_id: str,
        pattern_id: str,
        success: bool,
        performance_gain: float | None = None,
        quality_score: float | None = None,
        user_feedback: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Record the outcome of a pattern application"""
        outcome = PatternOutcome(
            application_id=application_id,
            pattern_id=pattern_id,
            success=success,
            performance_gain=performance_gain,
            quality_score=quality_score,
            user_feedback=user_feedback,
            measured_at=time.time(),
            metrics=metrics or {},
        )

        self.autodidactic_loop.record_outcome(outcome)

    def get_next_pattern(self) -> DiscoveredPattern | None:
        """Get the next pattern to apply (highest confidence first)"""
        if self.auto_apply_queue:
            return self.auto_apply_queue.pop(0)
        return None

    def get_pattern_stats(self, pattern_id: str) -> dict[str, Any] | None:
        """Get learning statistics for a pattern"""
        return self.autodidactic_loop.get_pattern_stats(pattern_id)

    def get_integration_summary(self) -> dict[str, Any]:
        """Get summary of integration status"""
        learning_summary = self.autodidactic_loop.get_learning_summary()

        return {
            'auto_apply_queue': len(self.auto_apply_queue),
            'manual_review_queue': len(self.manual_review_queue),
            'applied_patterns': len(self.applied_patterns),
            'learning_summary': learning_summary,
        }


def simulate_pattern_application(
    pattern: DiscoveredPattern,
    integration: AdaptiveIntegration,
) -> dict[str, Any]:
    """Simulate applying a pattern and measuring the outcome

    In production, this would actually apply the optimization.
    For now, we simulate based on pattern characteristics.
    """

    # Apply pattern
    context = {
        'pattern_tag': pattern.tag,
        'confidence': pattern.confidence,
        'sources': pattern.sources,
        'simulation': True,
    }

    application_id = integration.apply_pattern(pattern, context)

    # Simulate outcome based on pattern confidence
    # Higher confidence = higher success probability
    success_probability = pattern.confidence
    success = success_probability > 0.75  # Threshold for success

    # Simulate performance gain
    # Patterns related to "optimization", "speedup", "performance" get gains
    performance_gain = None
    if any(keyword in pattern.tag for keyword in ['optimization', 'speedup', 'performance']):
        # Simulate gain based on confidence (higher confidence = higher gain)
        base_gain = 1.5 + (pattern.confidence * 5.0)  # 1.5x to 6.5x range
        performance_gain = base_gain if success else None

    # Simulate quality score
    quality_score = pattern.confidence * 0.95 if success else 0.3

    # Record outcome
    integration.record_outcome(
        application_id=application_id,
        pattern_id=pattern.pattern_id,
        success=success,
        performance_gain=performance_gain,
        quality_score=quality_score,
        user_feedback="Simulated application" if success else "Simulated failure",
        metrics={
            'simulated': True,
            'pattern_tag': pattern.tag,
            'confidence': pattern.confidence,
        }
    )

    return {
        'application_id': application_id,
        'pattern_id': pattern.pattern_id,
        'pattern_tag': pattern.tag,
        'success': success,
        'performance_gain': performance_gain,
        'quality_score': quality_score,
        'confidence_before': pattern.confidence,
    }
