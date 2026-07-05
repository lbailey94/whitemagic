"""Dharma Governor - Autonomous Ethical Governance

The Governor acts as an active interceptor for autonomous systems (GanaSwarm),
evaluating tasks against the Dharma System before execution.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from whitemagic.dharma import get_dharma_system

logger = logging.getLogger(__name__)


class GovernanceAction(Enum):
    """Actions the governor can take."""

    ALLOW = "allow"  # Proceed normally
    WARN = "warn"  # Proceed but log warning/emit event
    BLOCK = "block"  # Stop execution
    MODIFY = "modify"  # Modify parameters (advanced, future)


@dataclass
class GovernanceDecision:
    """Result of a governance check."""

    action: GovernanceAction
    score: float
    concerns: list[str]
    guidance: str
    timestamp: datetime | None = None

    def __post_init__(self) -> Any:
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DharmaGovernor:
    """Active governor for autonomous systems.
    Uses the passive DharmaSystem to make active blocking/allowing decisions.
    """

    def __init__(self, strictness: float = 0.7) -> None:
        """Args:
        strictness: Minimum ethical score required to ALLOW (0.0 - 1.0)

        """
        self.dharma = get_dharma_system()
        self.strictness = strictness

    def govern(
        self, task_description: str, context: dict[str, Any] | None = None
    ) -> GovernanceDecision:
        """Evaluate a task and return a binding decision.

        Coherence-aware: when system coherence is low, strictness increases
        (more conservative governance). When coherence is high, strictness
        relaxes (more permissive, trusting the system's judgment).
        """
        # Coherence-adaptive strictness
        effective_strictness = self._adjust_strictness_for_coherence()

        # Construct action dict for Dharma evaluation
        action = {
            "description": task_description,
            "context": context or {},
            "source": "autonomous_governor",
        }

        # 1. Check Hard Boundaries (Instant Block)
        violations = self.dharma.check_boundaries(action)
        if violations:
            return GovernanceDecision(
                action=GovernanceAction.BLOCK,
                score=0.0,
                concerns=[v.description for v in violations],
                guidance=f"Boundary violation detected: {violations[0].suggested_action}",
            )

        # 2. Evaluate Ethical Principles (Score)
        score, concerns = self.dharma.evaluate_action(action)

        # 3. Determine Governance Action
        gov_action = GovernanceAction.ALLOW
        guidance = "Proceed with awareness."

        if score < 0.3:
            gov_action = GovernanceAction.BLOCK
            guidance = "Ethical score critical. Action blocked."
        elif score < effective_strictness:
            gov_action = GovernanceAction.WARN
            guidance = f"Ethical score low (strictness: {effective_strictness:.2f}). Proceed with caution."

        return GovernanceDecision(
            action=gov_action,
            score=score,
            concerns=concerns,
            guidance=guidance,
        )

    def _adjust_strictness_for_coherence(self) -> float:
        """Adjust strictness based on current coherence.

        High coherence (≥0.9): relax strictness by 0.1 (trust the system)
        Medium coherence (0.5-0.9): use baseline strictness
        Low coherence (<0.5): increase strictness by 0.2 (be conservative)
        Fragmented (<0.3): increase strictness by 0.3 (be very conservative)
        """
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric

            metric = get_coherence_metric()
            # Measure with actual memory count for accurate assessment
            try:

                from whitemagic.config.paths import WM_ROOT

                db_path = WM_ROOT / "memory" / "whitemagic.db"
                if db_path.exists():
                    conn = safe_connect(str(db_path))
                    count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    conn.close()
                    metric.measure(memories_accessible=count)
                else:
                    metric.measure()
            except Exception:
                metric.measure()
            level = metric.get_coherence_level()
            if level == "transcendent":
                return max(0.5, self.strictness - 0.1)
            elif level in ("highly_coherent", "coherent"):
                return self.strictness
            elif level == "partial":
                return min(0.95, self.strictness + 0.2)
            else:  # fragmented or dissociated
                return min(0.95, self.strictness + 0.3)
        except Exception:
            return self.strictness


# Global singleton
_governor: DharmaGovernor | None = None


def get_governor(strictness: float = 0.7) -> DharmaGovernor:
    """
    Get the governor.

    Args:
        strictness: Parameter description.

    Returns:
        DharmaGovernor
    """
    global _governor
    if _governor is None:
        _governor = DharmaGovernor(strictness=strictness)
    return _governor
