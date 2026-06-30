# ruff: noqa: BLE001
"""Chain Tracker — tracks wm() call sequences for SkillForge auto-forging.

Monitors sequences of wm() meta-tool calls within a time window.
When a sequence reaches the minimum length threshold, constructs an
ExecutionChain and feeds it to SkillForge for assessment/forging.

This is the bridge between the live MCP dispatch path and the SkillForge.
"""

import logging
import time
from dataclasses import dataclass

from whitemagic.core.intelligence.omni.skill_forge import ForgedSkill
from whitemagic.core.intelligence.omni.universal_router import ExecutionChain, GanaStep

logger = logging.getLogger(__name__)


@dataclass
class TrackedCall:
    """A single wm() call in a tracked sequence."""

    gana: str
    sub_tool: str | None
    thought: str
    success: bool
    timestamp: float
    duration_ms: float = 0.0


class ChainTracker:
    """Tracks sequences of wm() calls for auto-forging.

    Accumulates calls within a time window. When the sequence reaches
    MIN_CHAIN_LENGTH and either:
    - A timeout passes (CHAIN_TIMEOUT_S), or
    - An explicit flush() is called,

    it constructs an ExecutionChain and feeds it to SkillForge.
    """

    MIN_CHAIN_LENGTH = 3
    CHAIN_TIMEOUT_S = 30.0

    def __init__(self) -> None:
        self._calls: list[TrackedCall] = []
        self._last_flush = time.time()

    def record(
        self,
        gana: str,
        sub_tool: str | None,
        thought: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record a single wm() call result."""
        call = TrackedCall(
            gana=gana,
            sub_tool=sub_tool,
            thought=thought,
            success=success,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )
        self._calls.append(call)
        logger.debug(
            "ChainTracker: recorded call #%d (%s/%s, success=%s)",
            len(self._calls),
            gana,
            sub_tool,
            success,
        )

    def should_flush(self) -> bool:
        """Check if the current sequence should be flushed to SkillForge."""
        if len(self._calls) < self.MIN_CHAIN_LENGTH:
            return False
        if (time.time() - self._last_flush) > self.CHAIN_TIMEOUT_S:
            return True
        return False

    def flush(self) -> ExecutionChain | None:
        """Flush the current call sequence as an ExecutionChain.

        Returns the chain if it was forged, None if sequence too short
        or all calls failed.
        """
        if len(self._calls) < self.MIN_CHAIN_LENGTH:
            self._calls.clear()
            return None

        chain = self._build_chain()
        self._calls.clear()
        self._last_flush = time.time()
        return chain

    def _build_chain(self) -> ExecutionChain:
        """Construct an ExecutionChain from tracked calls."""
        thoughts = [c.thought for c in self._calls if c.thought]
        intent = " → ".join(thoughts[:3]) if thoughts else "tracked sequence"

        steps: list[GanaStep] = []
        for call in self._calls:
            mansion = call.gana.replace("gana_", "").upper()
            operation = self._infer_operation(call.sub_tool)
            context_key = call.sub_tool or call.thought[:50]
            steps.append(
                GanaStep(
                    mansion=mansion,
                    operation=operation,
                    context_key=context_key,
                    parameters={},
                )
            )

        return ExecutionChain(
            intent=intent,
            steps=steps,
            estimated_complexity=len(steps) * 0.8,
            required_capabilities=[],
        )

    @staticmethod
    def _infer_operation(sub_tool: str | None) -> str:
        """Infer the Gana operation type from the sub-tool name."""
        if not sub_tool:
            return "search"
        lower = sub_tool.lower()
        if any(
            w in lower
            for w in ("create", "write", "save", "store", "forge", "register")
        ):
            return "transform"
        if any(
            w in lower
            for w in ("analyze", "inspect", "check", "health", "report", "gnosis")
        ):
            return "analyze"
        if any(
            w in lower for w in ("consolidate", "merge", "sync", "export", "backup")
        ):
            return "consolidate"
        return "search"

    def try_auto_forge(self) -> ForgedSkill | None:
        """Check if the current sequence should be flushed and forged.

        Returns the forged skill if one was created, None otherwise.
        """
        if not self.should_flush():
            return None

        # Compute success ratio before flush clears _calls
        success_count = sum(1 for c in self._calls if c.success)
        total = len(self._calls)
        success_ratio = success_count / total if total > 0 else 0

        chain = self.flush()
        if chain is None:
            return None

        try:
            from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

            forge = get_skill_forge()

            if forge.assess_pattern(chain, success_ratio):
                return forge.forge(chain)
        except Exception as e:
            logger.warning("Auto-forge from ChainTracker failed: %s", e)

        return None

    def reset(self) -> None:
        """Clear all tracked calls."""
        self._calls.clear()
        self._last_flush = time.time()

    @property
    def call_count(self) -> int:
        """Number of calls currently tracked."""
        return len(self._calls)


# Singleton
_tracker: ChainTracker | None = None


def get_chain_tracker() -> ChainTracker:
    """Get the singleton ChainTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ChainTracker()
    return _tracker


def reset_chain_tracker() -> None:
    """Reset the singleton — for testing."""
    global _tracker
    _tracker = None
