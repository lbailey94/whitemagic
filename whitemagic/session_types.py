"""
Session Type Detection & Configuration - Auto-optimize context loading.

Automatically detects session type and adjusts context loading strategy:
- CONTINUATION: Minimal context, pick up where left off
- NEW_CONTRIBUTOR: Full onboarding, comprehensive context
- DEBUG: Focus on error logs, relevant code only
- EXPLORATION: Broader context, discovery mode

Philosophy:
- Context should match intent
- Auto-detect when possible, allow override
- Different contexts for different goals

Based on Five Factors (五事): Know the situation (知彼知己)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class SessionType(Enum):
    """Types of sessions with different context needs."""

    CONTINUATION = "continuation"
    NEW_CONTRIBUTOR = "new_contributor"
    DEBUG = "debug"
    EXPLORATION = "exploration"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    RELEASE = "release"


@dataclass
class ContextStrategy:
    """Strategy for loading context based on session type."""

    session_type: SessionType
    tier: int  # Default tier for this session type
    load_workspace: bool  # Whether to load full workspace structure
    workspace_tier: int  # Tier for workspace loading (0, 1, 2)
    focus_areas: List[str]  # Which areas to focus on
    exclude_patterns: List[str]  # What to exclude
    initial_token_budget: int  # Expected initial token usage
    search_queries: List[str]  # Suggested search queries
    description: str  # Human-readable description


class SessionTypeDetector:
    """
    Detects session type based on various signals.

    Uses multiple heuristics:
    - Time since last session
    - Recent activity patterns
    - Explicit markers in task description
    - Memory patterns
    """

    # Context strategies for each session type
    STRATEGIES = {
        SessionType.CONTINUATION: ContextStrategy(
            session_type=SessionType.CONTINUATION,
            tier=0,  # Minimal memory context
            load_workspace=False,
            workspace_tier=0,  # Only task-relevant dirs
            focus_areas=["recent-changes", "in-progress"],
            exclude_patterns=["archive", "backups", "docs/archive"],
            initial_token_budget=8000,
            search_queries=["start-here", "in-progress", "session"],
            description="Continue from last session with minimal context",
        ),
        SessionType.NEW_CONTRIBUTOR: ContextStrategy(
            session_type=SessionType.NEW_CONTRIBUTOR,
            tier=2,  # Full memory context
            load_workspace=True,
            workspace_tier=2,  # Full workspace tree
            focus_areas=["architecture", "getting-started", "vision"],
            exclude_patterns=["backups"],
            initial_token_budget=25000,
            search_queries=["architecture", "vision", "getting-started"],
            description="Full project onboarding for new contributor",
        ),
        SessionType.DEBUG: ContextStrategy(
            session_type=SessionType.DEBUG,
            tier=1,  # Balanced memory context
            load_workspace=False,
            workspace_tier=0,  # Only code dirs
            focus_areas=["errors", "bugs", "fixes", "troubleshooting"],
            exclude_patterns=["archive", "docs", "backups"],
            initial_token_budget=10000,
            search_queries=["error", "bug", "fix", "debug"],
            description="Debug mode: focus on errors and relevant code",
        ),
        SessionType.EXPLORATION: ContextStrategy(
            session_type=SessionType.EXPLORATION,
            tier=1,  # Balanced context
            load_workspace=True,
            workspace_tier=1,  # Balanced workspace view
            focus_areas=["ideas", "research", "exploration"],
            exclude_patterns=["backups"],
            initial_token_budget=15000,
            search_queries=["research", "exploration", "ideas"],
            description="Exploration mode: broad context for discovery",
        ),
        SessionType.OPTIMIZATION: ContextStrategy(
            session_type=SessionType.OPTIMIZATION,
            tier=1,
            load_workspace=False,
            workspace_tier=0,
            focus_areas=["performance", "optimization", "metrics"],
            exclude_patterns=["archive", "backups", "docs"],
            initial_token_budget=12000,
            search_queries=["optimization", "performance", "metrics"],
            description="Optimization: focus on performance and metrics",
        ),
        SessionType.DOCUMENTATION: ContextStrategy(
            session_type=SessionType.DOCUMENTATION,
            tier=1,
            load_workspace=True,
            workspace_tier=1,
            focus_areas=["docs", "guides", "readme"],
            exclude_patterns=["backups", "tests"],
            initial_token_budget=15000,
            search_queries=["documentation", "guide", "readme"],
            description="Documentation: focus on docs and guides",
        ),
        SessionType.TESTING: ContextStrategy(
            session_type=SessionType.TESTING,
            tier=1,
            load_workspace=False,
            workspace_tier=0,
            focus_areas=["tests", "testing", "validation"],
            exclude_patterns=["archive", "backups", "docs"],
            initial_token_budget=10000,
            search_queries=["test", "testing", "validation"],
            description="Testing: focus on tests and validation",
        ),
        SessionType.RELEASE: ContextStrategy(
            session_type=SessionType.RELEASE,
            tier=1,
            load_workspace=True,
            workspace_tier=1,
            focus_areas=["changelog", "version", "release"],
            exclude_patterns=["backups", "archive"],
            initial_token_budget=15000,
            search_queries=["release", "version", "changelog"],
            description="Release: prepare for version release",
        ),
    }

    # Keywords that signal session type
    TYPE_KEYWORDS = {
        SessionType.CONTINUATION: ["continue", "resume", "pick up", "where left off", "keep going"],
        SessionType.NEW_CONTRIBUTOR: [
            "new",
            "onboard",
            "getting started",
            "introduction",
            "overview",
            "explain",
            "how does",
            "what is",
        ],
        SessionType.DEBUG: [
            "debug",
            "fix",
            "error",
            "bug",
            "broken",
            "not working",
            "fails",
            "crash",
            "issue",
        ],
        SessionType.EXPLORATION: [
            "explore",
            "research",
            "investigate",
            "look into",
            "discover",
            "what if",
            "brainstorm",
            "ideas",
        ],
        SessionType.OPTIMIZATION: [
            "optimize",
            "improve",
            "performance",
            "faster",
            "efficiency",
            "reduce",
            "speed up",
        ],
        SessionType.DOCUMENTATION: [
            "document",
            "docs",
            "write guide",
            "readme",
            "explain",
            "documentation",
        ],
        SessionType.TESTING: ["test", "verify", "validate", "check", "ensure"],
        SessionType.RELEASE: ["release", "ship", "deploy", "publish", "version"],
    }

    def __init__(self, memory_dir: Optional[Path] = None):
        """
        Initialize session type detector.

        Args:
            memory_dir: Path to memory directory for checking recent activity
        """
        self.memory_dir = memory_dir

    def detect(
        self,
        task_description: Optional[str] = None,
        last_session_time: Optional[datetime] = None,
        explicit_type: Optional[SessionType] = None,
    ) -> SessionType:
        """
        Detect session type from available signals.

        Args:
            task_description: Description of what user wants to do
            last_session_time: When was the last session
            explicit_type: Explicit override of session type

        Returns:
            Detected SessionType
        """
        # Explicit type always wins
        if explicit_type:
            return explicit_type

        # Check task description for keywords
        if task_description:
            detected_type = self._detect_from_description(task_description)
            if detected_type:
                return detected_type

        # Check timing patterns
        if last_session_time:
            detected_type = self._detect_from_timing(last_session_time)
            if detected_type:
                return detected_type

        # Check memory patterns
        if self.memory_dir:
            detected_type = self._detect_from_memory_patterns()
            if detected_type:
                return detected_type

        # Default: continuation (most common)
        return SessionType.CONTINUATION

    def _detect_from_description(self, description: str) -> Optional[SessionType]:
        """Detect session type from task description."""
        desc_lower = description.lower()

        # Count keyword matches for each type
        matches: Dict[SessionType, int] = {}

        for session_type, keywords in self.TYPE_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in desc_lower)
            if count > 0:
                matches[session_type] = count

        # Return type with most matches
        if matches:
            return max(matches.items(), key=lambda x: x[1])[0]

        return None

    def _detect_from_timing(self, last_session_time: datetime) -> Optional[SessionType]:
        """Detect session type from timing patterns."""
        now = datetime.now()
        time_since = now - last_session_time

        # Less than 1 hour: definitely continuation
        if time_since < timedelta(hours=1):
            return SessionType.CONTINUATION

        # Less than 24 hours: probably continuation
        elif time_since < timedelta(hours=24):
            return SessionType.CONTINUATION

        # More than a week: might need more context
        elif time_since > timedelta(days=7):
            return SessionType.EXPLORATION

        return None

    def _detect_from_memory_patterns(self) -> Optional[SessionType]:
        """Detect session type from recent memory patterns."""
        if not self.memory_dir or not self.memory_dir.exists():
            return None

        # Check for "start-here" memories
        short_term = self.memory_dir / "short_term"
        if short_term.exists():
            recent_files = sorted(
                short_term.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
            )[:5]

            for file in recent_files:
                content = file.read_text(encoding="utf-8").lower()

                # Check for session markers
                if "start-here" in content or "start here" in content:
                    return SessionType.CONTINUATION

                if "in-progress" in content or "in progress" in content:
                    return SessionType.CONTINUATION

        return None

    def get_strategy(self, session_type: SessionType) -> ContextStrategy:
        """
        Get the context loading strategy for a session type.

        Args:
            session_type: The type of session

        Returns:
            ContextStrategy for this session type
        """
        return self.STRATEGIES[session_type]

    def get_recommended_actions(self, session_type: SessionType) -> List[str]:
        """
        Get recommended actions for starting a session.

        Args:
            session_type: The type of session

        Returns:
            List of recommended actions
        """
        strategy = self.get_strategy(session_type)

        actions = []

        # Memory loading
        if strategy.tier == 0:
            actions.append("Load minimal memory context: mcp3_get_context(tier=0)")
        elif strategy.tier == 1:
            actions.append("Load balanced memory context: mcp3_get_context(tier=1)")
        elif strategy.tier == 2:
            actions.append("Load full memory context: mcp3_get_context(tier=2)")

        # Search queries
        if strategy.search_queries:
            for query in strategy.search_queries[:3]:
                actions.append(f'Search memories: mcp3_search_memories(query="{query}")')

        # Workspace loading
        if strategy.load_workspace:
            actions.append(
                f"Load workspace structure: "
                f"load_workspace_for_task(tier={strategy.workspace_tier})"
            )

        # Focus areas
        if strategy.focus_areas:
            actions.append(f"Focus on: {', '.join(strategy.focus_areas)}")

        return actions


@dataclass
class SessionConfig:
    """Complete session configuration based on detected type."""

    session_type: SessionType
    strategy: ContextStrategy
    recommended_actions: List[str]
    estimated_initial_tokens: int
    auto_detected: bool
    detection_confidence: float  # 0.0 to 1.0


class SessionConfigurator:
    """
    High-level configurator that combines detection and strategy.
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        """
        Initialize session configurator.

        Args:
            memory_dir: Path to memory directory
        """
        self.detector = SessionTypeDetector(memory_dir)

    def configure(
        self,
        task_description: Optional[str] = None,
        last_session_time: Optional[datetime] = None,
        explicit_type: Optional[SessionType] = None,
    ) -> SessionConfig:
        """
        Configure a session based on available information.

        Args:
            task_description: What the user wants to do
            last_session_time: When was last session
            explicit_type: Explicit session type override

        Returns:
            Complete SessionConfig
        """
        # Detect session type
        auto_detected = explicit_type is None
        session_type = self.detector.detect(task_description, last_session_time, explicit_type)

        # Get strategy
        strategy = self.detector.get_strategy(session_type)

        # Get recommended actions
        actions = self.detector.get_recommended_actions(session_type)

        # Estimate confidence
        confidence = self._estimate_confidence(session_type, task_description, auto_detected)

        return SessionConfig(
            session_type=session_type,
            strategy=strategy,
            recommended_actions=actions,
            estimated_initial_tokens=strategy.initial_token_budget,
            auto_detected=auto_detected,
            detection_confidence=confidence,
        )

    def _estimate_confidence(
        self, session_type: SessionType, task_description: Optional[str], auto_detected: bool
    ) -> float:
        """Estimate confidence in detection."""
        if not auto_detected:
            return 1.0  # Explicit type = 100% confident

        if not task_description:
            return 0.5  # No info = low confidence

        # Check how many keywords matched
        desc_lower = task_description.lower()
        keywords = self.detector.TYPE_KEYWORDS[session_type]
        matches = sum(1 for kw in keywords if kw in desc_lower)

        if matches >= 3:
            return 0.95
        elif matches == 2:
            return 0.80
        elif matches == 1:
            return 0.60
        else:
            return 0.40


def configure_session(
    task_description: Optional[str] = None,
    memory_dir: Optional[Path] = None,
    explicit_type: Optional[str] = None,
    last_session_time: Optional[datetime] = None,
) -> SessionConfig:
    """
    Convenience function to configure a session.

    Args:
        task_description: Description of task
        memory_dir: Memory directory path
        explicit_type: Explicit session type (string)
        last_session_time: When was last session

    Returns:
        SessionConfig

    Example:
        >>> config = configure_session(
        ...     task_description="Continue implementing symbolic reasoning",
        ...     memory_dir=Path("memory")
        ... )
        >>> print(config.session_type)
        SessionType.CONTINUATION
        >>> print(config.estimated_initial_tokens)
        8000
    """
    configurator = SessionConfigurator(memory_dir)

    # Convert string type to enum if provided
    explicit_enum = None
    if explicit_type:
        try:
            explicit_enum = SessionType(explicit_type.lower())
        except ValueError:
            pass

    return configurator.configure(
        task_description=task_description,
        last_session_time=last_session_time,
        explicit_type=explicit_enum,
    )


def print_session_config(config: SessionConfig) -> str:
    """
    Format session configuration as human-readable string.

    Args:
        config: Session configuration

    Returns:
        Formatted string
    """
    lines = []

    lines.append("# Session Configuration")
    lines.append("")
    lines.append(f"**Type**: {config.session_type.value}")
    lines.append(f"**Detection**: {'Auto-detected' if config.auto_detected else 'Explicit'}")
    lines.append(f"**Confidence**: {config.detection_confidence*100:.0f}%")
    lines.append("")
    lines.append("## Strategy")
    lines.append("")
    lines.append(f"- **Memory tier**: {config.strategy.tier}")
    lines.append(f"- **Workspace loading**: {'Yes' if config.strategy.load_workspace else 'No'}")
    if config.strategy.load_workspace:
        lines.append(f"- **Workspace tier**: {config.strategy.workspace_tier}")
    lines.append(f"- **Focus areas**: {', '.join(config.strategy.focus_areas)}")
    lines.append(f"- **Estimated tokens**: ~{config.estimated_initial_tokens:,}")
    lines.append("")
    lines.append("## Recommended Actions")
    lines.append("")
    for i, action in enumerate(config.recommended_actions, 1):
        lines.append(f"{i}. {action}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*{config.strategy.description}*")

    return "\n".join(lines)
