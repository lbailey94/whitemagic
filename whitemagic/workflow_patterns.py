"""
Workflow Patterns - Code equivalent of global/workspace rules.

This module codifies the workflow patterns from .cascade/workspace_rules.md
and .windsurf/rules/whitemagic-project.md as executable Python code.

Purpose:
- Ensure patterns are widely adopted
- Allow AI and humans to customize on the fly
- Provide programmatic access to best practices
- Enable runtime configuration

Based on: Workflow Rules v3.1 (Art of War + I Ching)
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class LoadingTier(Enum):
    """Memory/context loading tiers."""

    TIER_0 = 0  # Quick scan (500 tokens)
    TIER_1 = 1  # Balanced (3K tokens)
    TIER_2 = 2  # Deep dive (10K+ tokens)


class TaskTerrain(Enum):
    """Art of War terrain types for task assessment."""

    ACCESSIBLE = "accessible"  # Straightforward, proceed directly
    ENTANGLING = "entangling"  # Dependencies, resolve first
    TEMPORIZING = "temporizing"  # Need more info, gather intelligence
    NARROW = "narrow"  # Sequential only, no parallelism
    PRECIPITOUS = "precipitous"  # High risk, extreme caution
    DISTANT = "distant"  # Long duration, plan checkpoints


class ThreadingTier(Enum):
    """I Ching-aligned threading tiers."""

    TIER_0 = 8  # 8 trigrams
    TIER_1 = 16
    TIER_2 = 32
    TIER_3 = 64  # 64 hexagrams (sweet spot)
    TIER_4 = 128
    TIER_5 = 256  # Ultimate complexity


@dataclass
class WorkflowConfig:
    """Configuration for workflow patterns."""

    # Memory loading strategy
    default_tier: LoadingTier = LoadingTier.TIER_1
    use_direct_reads: bool = True  # Prefer read_file over MCP for large files
    cache_enabled: bool = True

    # Parallel execution
    parallel_first: bool = True  # Default to parallel when possible
    max_parallel_calls: int = 10

    # Token management
    token_budget: int = 200000
    pause_threshold: float = 0.70  # Pause at 70% usage
    warning_threshold: float = 0.60

    # Session management
    checkpoint_interval_hours: float = 2.0
    auto_consolidate_every: int = 10  # memories

    # Composite reasoning
    max_response_tokens: int = 10000
    use_incremental_build: bool = True

    # Custom rules
    custom_rules: Dict[str, Any] = field(default_factory=dict)


class WorkflowPatterns:
    """
    Executable workflow patterns based on documented rules.

    This class provides programmatic access to the workflow patterns
    described in workspace_rules.md and whitemagic-project.md
    """

    def __init__(self, config: Optional[WorkflowConfig] = None):
        """
        Initialize workflow patterns.

        Args:
            config: Custom configuration (uses defaults if not provided)
        """
        self.config = config or WorkflowConfig()
        self._metrics: Dict[str, Any] = {}

    # ===== MEMORY LOADING STRATEGIES =====

    def should_use_direct_read(self, file_size_bytes: int) -> bool:
        """
        Determine if direct file read should be used over MCP.

        Rule: Use read_file for files >100 lines (10-100x faster)

        Args:
            file_size_bytes: Size of file in bytes

        Returns:
            True if direct read recommended
        """
        # Rough estimate: 100 lines ≈ 5000 bytes
        return self.config.use_direct_reads and file_size_bytes > 5000

    def get_recommended_tier(self, task_type: str, is_continuation: bool = False) -> LoadingTier:
        """
        Get recommended loading tier for a task.

        Rules:
        - Continuation: Tier 0 (minimal)
        - New work: Tier 1 (balanced)
        - Complex/research: Tier 2 (full)

        Args:
            task_type: Type of task (continuation, new, research, etc.)
            is_continuation: Whether continuing from previous session

        Returns:
            Recommended LoadingTier
        """
        if is_continuation:
            return LoadingTier.TIER_0

        task_lower = task_type.lower()

        if any(kw in task_lower for kw in ["research", "explore", "comprehensive"]):
            return LoadingTier.TIER_2
        elif any(kw in task_lower for kw in ["new", "start", "begin"]):
            return LoadingTier.TIER_1
        else:
            return self.config.default_tier

    def get_loading_sequence(self, tier: LoadingTier) -> List[Dict[str, Any]]:
        """
        Get recommended sequence of loading operations.

        Returns optimized sequence based on tier.

        Args:
            tier: Loading tier

        Returns:
            List of loading operations in recommended order
        """
        if tier == LoadingTier.TIER_0:
            return [
                {"action": "mcp3_get_context", "params": {"tier": 0}},
                {"action": "grep_search", "params": {"query": "start-here"}},
            ]
        elif tier == LoadingTier.TIER_1:
            return [
                {"action": "mcp3_get_context", "params": {"tier": 1}},
                {"action": "load_workspace", "params": {"tier": 0}},
            ]
        else:  # TIER_2
            return [
                {"action": "mcp3_get_context", "params": {"tier": 2}},
                {"action": "load_workspace", "params": {"tier": 1}},
                {"action": "search_recent", "params": {"limit": 10}},
            ]

    # ===== PARALLEL EXECUTION =====

    def can_parallelize(self, terrain: TaskTerrain, operations: List[str]) -> bool:
        """
        Determine if operations can be parallelized.

        Rule: Parallel by default unless terrain is NARROW or operations
        have dependencies.

        Args:
            terrain: Task terrain type
            operations: List of operation descriptions

        Returns:
            True if parallelization recommended
        """
        if not self.config.parallel_first:
            return False

        if terrain == TaskTerrain.NARROW:
            return False

        if terrain == TaskTerrain.PRECIPITOUS:
            return False  # High risk, be careful

        # Check for obvious dependencies
        dependency_keywords = ["after", "then", "once", "wait", "requires"]
        op_text = " ".join(operations).lower()

        if any(kw in op_text for kw in dependency_keywords):
            return False

        return True

    def get_threading_tier(self, complexity: str) -> ThreadingTier:
        """
        Get recommended threading tier based on complexity.

        I Ching-aligned tiers: 8, 16, 32, 64, 128, 256

        Args:
            complexity: Complexity level (simple, medium, complex, very_complex)

        Returns:
            Recommended ThreadingTier
        """
        complexity_map = {
            "simple": ThreadingTier.TIER_0,  # 8
            "low": ThreadingTier.TIER_1,  # 16
            "medium": ThreadingTier.TIER_2,  # 32
            "high": ThreadingTier.TIER_3,  # 64 (sweet spot)
            "very_high": ThreadingTier.TIER_4,  # 128
            "extreme": ThreadingTier.TIER_5,  # 256
        }

        return complexity_map.get(complexity.lower(), ThreadingTier.TIER_3)

    # ===== TOKEN MANAGEMENT =====

    def check_token_status(self, tokens_used: int) -> Dict[str, Any]:
        """
        Check token status and provide recommendations.

        Rules:
        - Warning at 60%
        - Pause at 70%
        - Mandatory stop at 80%

        Args:
            tokens_used: Number of tokens used so far

        Returns:
            Status dictionary with recommendations
        """
        budget = self.config.token_budget
        pct_used = tokens_used / budget
        remaining = budget - tokens_used

        status = {
            "tokens_used": tokens_used,
            "tokens_remaining": remaining,
            "percent_used": pct_used * 100,
            "budget": budget,
        }

        if pct_used >= 0.80:
            status["level"] = "CRITICAL"
            status["action"] = "STOP - Create resume memory and end session"
            status["safe_to_continue"] = False
        elif pct_used >= self.config.pause_threshold:
            status["level"] = "WARNING"
            status["action"] = "PAUSE - Consider creating checkpoint"
            status["safe_to_continue"] = False
        elif pct_used >= self.config.warning_threshold:
            status["level"] = "CAUTION"
            status["action"] = "MONITOR - Stay efficient"
            status["safe_to_continue"] = True
        else:
            status["level"] = "GOOD"
            status["action"] = "CONTINUE"
            status["safe_to_continue"] = True

        return status

    def estimate_tokens_needed(self, operation: str, context_size: Optional[int] = None) -> int:
        """
        Estimate tokens needed for an operation.

        Args:
            operation: Operation type (read, write, search, etc.)
            context_size: Optional context size in characters

        Returns:
            Estimated token count
        """
        # Rough estimates (chars / 4 = tokens)
        estimates = {
            "mcp3_get_context_tier0": 500,
            "mcp3_get_context_tier1": 3000,
            "mcp3_get_context_tier2": 10000,
            "mcp3_search": 1000,
            "read_file_small": 1000,
            "read_file_medium": 3000,
            "read_file_large": 8000,
            "write_file": 2000,
            "edit_file": 1500,
        }

        base_estimate = estimates.get(operation, 2000)

        if context_size:
            base_estimate += context_size // 4

        return base_estimate

    # ===== SESSION MANAGEMENT =====

    def should_checkpoint(self, session_duration_minutes: int) -> bool:
        """
        Determine if checkpoint should be created.

        Rule: Checkpoint every 2-3 hours (120-180 minutes)

        Args:
            session_duration_minutes: Current session duration

        Returns:
            True if checkpoint recommended
        """
        threshold_minutes = self.config.checkpoint_interval_hours * 60
        return session_duration_minutes >= threshold_minutes

    def should_consolidate(self, short_term_count: int) -> bool:
        """
        Determine if memory consolidation needed.

        Rule: Consolidate every 5-10 memories

        Args:
            short_term_count: Number of short-term memories

        Returns:
            True if consolidation recommended
        """
        return short_term_count >= self.config.auto_consolidate_every

    # ===== COMPOSITE REASONING =====

    def should_use_incremental_build(self, estimated_output_tokens: int) -> bool:
        """
        Determine if incremental build should be used.

        Rule: Use for outputs >10K tokens

        Args:
            estimated_output_tokens: Estimated output size

        Returns:
            True if incremental build recommended
        """
        return (
            self.config.use_incremental_build
            and estimated_output_tokens > self.config.max_response_tokens
        )

    def plan_incremental_stages(
        self, total_tokens: int, max_per_stage: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Plan stages for incremental build.

        Args:
            total_tokens: Total estimated tokens
            max_per_stage: Max tokens per stage (default: 8000)

        Returns:
            List of stage plans
        """
        if max_per_stage is None:
            max_per_stage = self.config.max_response_tokens - 2000  # Buffer

        num_stages = (total_tokens // max_per_stage) + 1

        stages = []
        for i in range(num_stages):
            stage = {
                "stage_num": i + 1,
                "estimated_tokens": min(max_per_stage, total_tokens - (i * max_per_stage)),
                "description": "Skeleton" if i == 0 else f"Stage {i + 1}",
            }
            stages.append(stage)

        return stages

    # ===== METRICS & REPORTING =====

    def track_metric(self, key: str, value: Any) -> None:
        """Track a metric value."""
        self._metrics[key] = value

    def get_metrics(self) -> Dict[str, Any]:
        """Get all tracked metrics."""
        return self._metrics.copy()

    def generate_session_report(self) -> str:
        """Generate session report with metrics."""
        lines = []
        lines.append("# Session Report")
        lines.append("")

        if "tokens_used" in self._metrics:
            status = self.check_token_status(self._metrics["tokens_used"])
            lines.append(f"**Token Status**: {status['tokens_used']:,} / {status['budget']:,}")
            lines.append(f"**Percent Used**: {status['percent_used']:.1f}%")
            lines.append(f"**Level**: {status['level']}")
            lines.append(f"**Action**: {status['action']}")
            lines.append("")

        lines.append("## Metrics")
        for key, value in self._metrics.items():
            if key != "tokens_used":
                lines.append(f"- **{key}**: {value}")

        return "\n".join(lines)

    # ===== CONFIGURATION =====

    def save_config(self, path: Path) -> None:
        """Save configuration to file."""
        config_dict = {
            "default_tier": self.config.default_tier.value,
            "use_direct_reads": self.config.use_direct_reads,
            "parallel_first": self.config.parallel_first,
            "token_budget": self.config.token_budget,
            "pause_threshold": self.config.pause_threshold,
            "custom_rules": self.config.custom_rules,
        }

        path.write_text(json.dumps(config_dict, indent=2))

    @classmethod
    def load_config(cls, path: Path) -> "WorkflowPatterns":
        """Load configuration from file."""
        config_dict = json.loads(path.read_text())

        config = WorkflowConfig(
            default_tier=LoadingTier(config_dict["default_tier"]),
            use_direct_reads=config_dict["use_direct_reads"],
            parallel_first=config_dict["parallel_first"],
            token_budget=config_dict["token_budget"],
            pause_threshold=config_dict["pause_threshold"],
            custom_rules=config_dict.get("custom_rules", {}),
        )

        return cls(config)


# Singleton instance with defaults
default_workflow = WorkflowPatterns()


def get_workflow() -> WorkflowPatterns:
    """Get the default workflow patterns instance."""
    return default_workflow


def configure_workflow(config: WorkflowConfig) -> WorkflowPatterns:
    """
    Configure workflow patterns.

    Args:
        config: Custom configuration

    Returns:
        WorkflowPatterns instance

    Example:
        >>> config = WorkflowConfig(
        ...     default_tier=LoadingTier.TIER_0,
        ...     parallel_first=True,
        ...     token_budget=100000
        ... )
        >>> workflow = configure_workflow(config)
    """
    global default_workflow
    default_workflow = WorkflowPatterns(config)
    return default_workflow
