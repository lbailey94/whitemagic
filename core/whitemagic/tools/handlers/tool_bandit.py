# ruff: noqa: BLE001
"""Thompson sampling bandit for llama.cpp agent tool selection.

Maintains a Beta(α, β) posterior for each tool in the WhiteMagic
tool registry. When the agent needs to decide which tools to suggest,
it samples from each tool's posterior and recommends the top-K.

- α (alpha) increments on success → tool is good for this task type
- β (beta) increments on failure → tool is bad for this task type
- Exploration happens naturally via sampling variance
- Cold-start: uniform Beta(1, 1) priors

Usage:
    from whitemagic.tools.handlers.tool_bandit import get_tool_bandit
    bandit = get_tool_bandit()
    recommended = bandit.recommend_tools(task="search memories", k=5)
    # After tool execution:
    bandit.record_outcome("memory.search", success=True)
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PRIOR_ALPHA = 1.0
_DEFAULT_PRIOR_BETA = 1.0
_RECOMMENDATION_K = 5


@dataclass
class ToolStats:
    """Beta posterior parameters for a single tool."""

    alpha: float = _DEFAULT_PRIOR_ALPHA
    beta: float = _DEFAULT_PRIOR_BETA
    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    # Per-task-type tracking (task_type → (alpha, beta))
    task_type_stats: dict[str, tuple[float, float]] = field(default_factory=dict)

    def sample(self) -> float:
        """Sample from Beta(alpha, beta) using numpy if available, else Python."""
        try:
            import numpy as np

            return float(np.random.beta(self.alpha, self.beta))
        except ImportError:
            return random.betavariate(self.alpha, self.beta)

    def expected_value(self) -> float:
        """Posterior mean: α / (α + β)."""
        return self.alpha / (self.alpha + self.beta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha": round(self.alpha, 2),
            "beta": round(self.beta, 2),
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "expected_success_rate": round(self.expected_value(), 4),
        }


class ToolBandit:
    """Thompson sampling multi-armed bandit over the WhiteMagic tool space.

    Tracks Beta posteriors per tool and per task-type, enabling the llama.cpp
    agent to learn which tools work best for different kinds of tasks.
    """

    def __init__(
        self,
        prior_alpha: float = _DEFAULT_PRIOR_ALPHA,
        prior_beta: float = _DEFAULT_PRIOR_BETA,
    ) -> None:
        self._prior_alpha = prior_alpha
        self._prior_beta = prior_beta
        self._tools: dict[str, ToolStats] = {}
        self._lock = threading.RLock()

    def register_tool(self, tool_name: str) -> None:
        """Register a new tool with default prior."""
        with self._lock:
            if tool_name not in self._tools:
                self._tools[tool_name] = ToolStats(
                    alpha=self._prior_alpha,
                    beta=self._prior_beta,
                )

    def register_tools(self, tool_names: list[str]) -> None:
        """Batch register tools."""
        with self._lock:
            for name in tool_names:
                if name not in self._tools:
                    self._tools[name] = ToolStats(
                        alpha=self._prior_alpha,
                        beta=self._prior_beta,
                    )

    def record_outcome(
        self,
        tool_name: str,
        success: bool,
        task_type: str | None = None,
        quality: float | None = None,
    ) -> None:
        """Record the outcome of a tool call.

        Args:
            tool_name: Name of the tool that was called
            success: Whether the tool call succeeded
            task_type: Optional task type for context-specific tracking
            quality: Optional quality score (0.0-1.0). When provided,
                updates the Beta posterior with fractional weight instead
                of binary +1/-1, giving the bandit a richer signal.
        """
        with self._lock:
            if tool_name not in self._tools:
                self._tools[tool_name] = ToolStats(
                    alpha=self._prior_alpha,
                    beta=self._prior_beta,
                )

            stats = self._tools[tool_name]
            stats.total_calls += 1
            if success:
                stats.total_successes += 1
            else:
                stats.total_failures += 1

            # Quality-weighted Beta update: use fractional alpha/beta increments
            if quality is not None and 0.0 <= quality <= 1.0:
                stats.alpha += quality
                stats.beta += 1.0 - quality
            elif success:
                stats.alpha += 1.0
            else:
                stats.beta += 1.0

            # Per-task-type tracking
            if task_type:
                if task_type not in stats.task_type_stats:
                    stats.task_type_stats[task_type] = (
                        self._prior_alpha,
                        self._prior_beta,
                    )
                a, b = stats.task_type_stats[task_type]
                if quality is not None and 0.0 <= quality <= 1.0:
                    stats.task_type_stats[task_type] = (
                        a + quality,
                        b + (1.0 - quality),
                    )
                elif success:
                    stats.task_type_stats[task_type] = (a + 1.0, b)
                else:
                    stats.task_type_stats[task_type] = (a, b + 1.0)

    def recommend_tools(
        self,
        task: str | None = None,
        k: int = _RECOMMENDATION_K,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Recommend top-K tools via Thompson sampling.

        Args:
            task: Task description (unused for sampling, but logged)
            k: Number of tools to recommend
            task_type: If provided, use task-type-specific posteriors

        Returns:
            List of {tool, sample, expected_value, stats} dicts, sorted by sample desc.
        """
        with self._lock:
            if not self._tools:
                return []

            samples: list[dict[str, Any]] = []
            for tool_name, stats in self._tools.items():
                # Use task-type-specific posterior if available
                if task_type and task_type in stats.task_type_stats:
                    a, b = stats.task_type_stats[task_type]
                    try:
                        import numpy as np

                        sample = float(np.random.beta(a, b))
                    except ImportError:
                        sample = random.betavariate(a, b)
                    ev = a / (a + b)
                else:
                    sample = stats.sample()
                    ev = stats.expected_value()

                samples.append(
                    {
                        "tool": tool_name,
                        "sample": round(sample, 4),
                        "expected_value": round(ev, 4),
                        "total_calls": stats.total_calls,
                    }
                )

            samples.sort(key=lambda x: x["sample"], reverse=True)
            return samples[:k]

    def get_tool_stats(self, tool_name: str) -> dict[str, Any] | None:
        """Get stats for a specific tool."""
        with self._lock:
            if tool_name not in self._tools:
                return None
            return self._tools[tool_name].to_dict()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all registered tools."""
        with self._lock:
            return {name: stats.to_dict() for name, stats in self._tools.items()}

    def get_top_tools(self, n: int = 10) -> list[dict[str, Any]]:
        """Get top-N tools by expected success rate (posterior mean)."""
        with self._lock:
            tools = [
                {
                    "tool": name,
                    "expected_value": stats.expected_value(),
                    "total_calls": stats.total_calls,
                    **stats.to_dict(),
                }
                for name, stats in self._tools.items()
                if stats.total_calls > 0
            ]
            tools.sort(key=lambda x: x["expected_value"], reverse=True)
            return tools[:n]

    def classify_task_type(self, task: str) -> str:
        """Classify a task into a task type based on keywords.

        This is a simple heuristic classifier. In production, this could
        use the ComplexityClassifier or an embedding-based approach.
        """
        task_lower = task.lower()
        task_types = {
            "knowledge_graph": ["graph", "association", "connection", "relationship"],
            "planning": ["plan", "strategy", "roadmap", "decompose", "route"],
            "memory_search": ["memory", "recall", "search", "find", "remember"],
            "analysis": ["analyze", "examine", "investigate", "study", "review"],
            "creation": ["create", "generate", "write", "build", "compose"],
            "governance": ["dharma", "ethics", "consent", "boundary", "evaluate"],
            "dreaming": ["dream", "consolidate", "sleep", "cycle"],
            "clone_deployment": ["clone", "army", "deploy", "war_room", "campaign"],
        }

        for task_type, keywords in task_types.items():
            if any(kw in task_lower for kw in keywords):
                return task_type

        return "general"

    def record_clone_outcome(
        self,
        strategy: str,
        success: bool,
        clone_type: str = "thought",
        task_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        quality: float | None = None,
    ) -> None:
        """Record the outcome of a clone deployment for bandit learning.

        Maps clone strategies to tool-like entries so the bandit learns
        which strategies work best for different task types.

        Args:
            strategy: Clone strategy (e.g. "analytical", "creative", "adversarial")
            success: Whether the clone deployment succeeded
            clone_type: Type of clone ("thought", "immortal", "code_writing")
            task_type: Optional task type for context-specific tracking
            metadata: Optional metadata (duration, tokens, confidence, etc.)
            quality: Optional quality score (0.0-1.0) from confidence or other metric.
                When provided, uses fractional Beta updates for richer signal.
        """
        tool_name = f"clone.{clone_type}.{strategy}"
        if quality is None and metadata:
            quality = metadata.get("confidence")
        self.record_outcome(
            tool_name, success=success, task_type=task_type, quality=quality
        )
        logger.debug(
            "Recorded clone outcome: %s success=%s quality=%s task_type=%s",
            tool_name,
            success,
            quality,
            task_type,
        )

    def recommend_clone_strategies(
        self,
        task: str,
        clone_type: str = "thought",
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Recommend top-K clone strategies via Thompson sampling.

        Args:
            task: Task description for task type classification
            clone_type: Type of clone ("thought", "immortal", "code_writing")
            k: Number of strategies to recommend

        Returns:
            List of {strategy, sample, expected_value, total_calls} dicts
        """
        task_type = self.classify_task_type(task)
        prefix = f"clone.{clone_type}."

        with self._lock:
            samples: list[dict[str, Any]] = []
            for tool_name, stats in self._tools.items():
                if not tool_name.startswith(prefix):
                    continue
                strategy = tool_name[len(prefix) :]

                if task_type and task_type in stats.task_type_stats:
                    a, b = stats.task_type_stats[task_type]
                    try:
                        import numpy as np

                        sample = float(np.random.beta(a, b))
                    except ImportError:
                        sample = random.betavariate(a, b)
                    ev = a / (a + b)
                else:
                    sample = stats.sample()
                    ev = stats.expected_value()

                samples.append(
                    {
                        "strategy": strategy,
                        "sample": round(sample, 4),
                        "expected_value": round(ev, 4),
                        "total_calls": stats.total_calls,
                    }
                )

            samples.sort(key=lambda x: x["sample"], reverse=True)
            return samples[:k]

    def to_dict(self) -> dict[str, Any]:
        """Get a summary of the bandit state."""
        with self._lock:
            total_calls = sum(s.total_calls for s in self._tools.values())
            total_tools = len(self._tools)
            tools_with_data = sum(1 for s in self._tools.values() if s.total_calls > 0)
            return {
                "total_tools": total_tools,
                "tools_with_data": tools_with_data,
                "total_calls": total_calls,
                "top_tools": self.get_top_tools(5),
            }


_bandit: ToolBandit | None = None
_bandit_lock = threading.Lock()


def get_tool_bandit() -> ToolBandit:
    """Get or create the global ToolBandit singleton."""
    global _bandit
    if _bandit is None:
        with _bandit_lock:
            if _bandit is None:
                _bandit = ToolBandit()
    return _bandit


def reset_tool_bandit() -> None:
    """Reset the global bandit (for testing)."""
    global _bandit
    with _bandit_lock:
        _bandit = None
