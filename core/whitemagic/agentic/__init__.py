"""
WhiteMagic Agentic Execution System

Enables AI agents to operate with confidence-based autonomy,
reducing human intervention while maintaining safety and quality.
"""

from __future__ import annotations

from .auto_activation import AutoActivation, get_auto_activation
from .coherence_persistence import CoherencePersistence, get_coherence_persistence
from .confidence import ConfidenceAssessor, ConfidenceFactors, ConfidenceLevel
from .confidence_learning import (
    ConfidenceLearner,
    TaskOutcome,
    auto_calibrate,
    get_learner,
    record_outcome,
)
from .cpu_inference import (
    CPUInferenceEngine,
    InferenceResult,
    cpu_infer,
    get_cpu_inference,
)
from .local_reasoning import (
    LocalInsight,
    LocalReasoningEngine,
    ReasoningResult,
    get_local_reasoning,
    reason_locally,
)
from .pattern_weather import PatternWeather, get_pattern_weather
from .token_optimizer import (
    QueryCache,
    TokenBudget,
    TokenOptimizer,
    get_token_optimizer,
    optimize_for_ai,
)

__all__ = [
    "ConfidenceAssessor",
    "ConfidenceFactors",
    "ConfidenceLevel",
    "ConfidenceLearner",
    "TaskOutcome",
    "get_learner",
    "record_outcome",
    "auto_calibrate",
    "CPUInferenceEngine",
    "InferenceResult",
    "get_cpu_inference",
    "cpu_infer",
    "LocalReasoningEngine",
    "LocalInsight",
    "ReasoningResult",
    "get_local_reasoning",
    "reason_locally",
    "TokenOptimizer",
    "TokenBudget",
    "QueryCache",
    "get_token_optimizer",
    "optimize_for_ai",
    "CoherencePersistence",
    "get_coherence_persistence",
    "AutoActivation",
    "get_auto_activation",
    "PatternWeather",
    "get_pattern_weather",
]
