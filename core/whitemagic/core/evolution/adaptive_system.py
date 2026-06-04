"""
Adaptive System - Full Recursive Evolution (Phase 3)
=====================================================

Enables the system to apply adaptations automatically with safety monitoring.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AdaptationRule:
    """Rule for when to apply adaptations automatically."""
    min_confidence: float = 0.9  # Minimum pattern confidence
    min_frequency: int = 10  # Minimum pattern frequency
    max_impact_score: float = 0.5  # Maximum allowed impact (0-1)
    require_approval: bool = True  # Require human approval
    enabled: bool = False  # Start disabled for safety


class AdaptiveSystem:
    """
    Manages automatic application of discovered adaptations.

    Safety-first approach:
    - Conservative thresholds by default
    - Monitoring and rollback capability
    - Manual approval for high-impact changes
    """

    def __init__(self):
        self.rules = AdaptationRule()
        self.applied_adaptations: list[dict[str, Any]] = []
        self.pending_approvals: list[dict[str, Any]] = []
        self.rollback_history: list[dict[str, Any]] = []

        # Monitoring
        self.coherence_history: list[float] = []
        self.performance_history: list[float] = []

        logger.info("🔄 Adaptive System initialized (DISABLED by default)")

    def enable(self, require_approval: bool = True):
        """
        Enable automatic adaptations.

        Args:
            require_approval: Whether to require human approval
        """
        self.rules.enabled = True
        self.rules.require_approval = require_approval

        logger.warning(f"⚠️ Adaptive System ENABLED (approval={'required' if require_approval else 'not required'})")

    def disable(self):
        """Disable automatic adaptations."""
        self.rules.enabled = False
        logger.info("🔒 Adaptive System DISABLED")

    def should_apply_adaptation(self, adaptation: dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if an adaptation should be applied.

        Returns:
            (should_apply, reason)
        """
        if not self.rules.enabled:
            return False, "Adaptive system is disabled"

        # Check confidence
        confidence = adaptation.get("confidence", 0.0)
        if confidence < self.rules.min_confidence:
            return False, f"Confidence {confidence:.2f} < threshold {self.rules.min_confidence}"

        # Check frequency
        frequency = adaptation.get("frequency", 0)
        if frequency < self.rules.min_frequency:
            return False, f"Frequency {frequency} < threshold {self.rules.min_frequency}"

        # Check impact
        impact = adaptation.get("impact_score", 0.0)
        if impact > self.rules.max_impact_score:
            return False, f"Impact {impact:.2f} > threshold {self.rules.max_impact_score}"

        # Check if approval required
        if self.rules.require_approval:
            return False, "Human approval required"

        return True, "All criteria met"

    def propose_adaptation(self, adaptation: dict[str, Any]) -> bool:
        """
        Propose an adaptation for application.

        Returns:
            True if applied immediately, False if pending approval
        """
        should_apply, reason = self.should_apply_adaptation(adaptation)

        if should_apply:
            return self._apply_adaptation(adaptation)
        else:
            if self.rules.require_approval and self.rules.enabled:
                self.pending_approvals.append({
                    "adaptation": adaptation,
                    "proposed_at": datetime.now().isoformat(),
                    "reason": reason,
                })
                logger.info(f"📋 Adaptation pending approval: {adaptation.get('description', 'Unknown')}")
            else:
                logger.debug(f"⏸️ Adaptation not applied: {reason}")

            return False

    def _apply_adaptation(self, adaptation: dict[str, Any]) -> bool:
        """Apply an adaptation to the system."""
        try:
            adaptation_type = adaptation.get("type", "unknown")

            logger.info(f"🚀 Applying adaptation: {adaptation.get('description', 'Unknown')}")

            # Record pre-adaptation state
            pre_state = {
                "coherence": self.coherence_history[-1] if self.coherence_history else 0.0,
                "performance": self.performance_history[-1] if self.performance_history else 0.0,
            }

            # Apply based on type
            if adaptation_type == "optimize_pathway":
                success = self._optimize_pathway(adaptation)
            elif adaptation_type == "strengthen_pathway":
                success = self._strengthen_pathway(adaptation)
            else:
                logger.warning(f"Unknown adaptation type: {adaptation_type}")
                success = False

            if success:
                # Record application
                self.applied_adaptations.append({
                    "adaptation": adaptation,
                    "applied_at": datetime.now().isoformat(),
                    "pre_state": pre_state,
                })

                logger.info("✅ Adaptation applied successfully")
                return True
            else:
                logger.error("❌ Adaptation failed to apply")
                return False

        except Exception as e:
            logger.error(f"❌ Error applying adaptation: {e}")
            return False

    def _optimize_pathway(self, adaptation: dict[str, Any]) -> bool:
        """Optimize a pathway (implementation placeholder)."""
        # In production, this would actually modify the system
        logger.info(f"  Optimizing pathway: {adaptation.get('pattern_id', 'unknown')}")
        return True

    def _strengthen_pathway(self, adaptation: dict[str, Any]) -> bool:
        """Strengthen a pathway (implementation placeholder)."""
        # In production, this would actually modify the system
        logger.info(f"  Strengthening pathway: {adaptation.get('pattern_id', 'unknown')}")
        return True

    def approve_adaptation(self, adaptation_index: int) -> bool:
        """
        Approve a pending adaptation.

        Args:
            adaptation_index: Index in pending_approvals list

        Returns:
            True if applied successfully
        """
        if adaptation_index >= len(self.pending_approvals):
            logger.error(f"Invalid adaptation index: {adaptation_index}")
            return False

        pending = self.pending_approvals.pop(adaptation_index)
        return self._apply_adaptation(pending["adaptation"])

    def reject_adaptation(self, adaptation_index: int):
        """Reject a pending adaptation."""
        if adaptation_index >= len(self.pending_approvals):
            logger.error(f"Invalid adaptation index: {adaptation_index}")
            return

        pending = self.pending_approvals.pop(adaptation_index)
        logger.info(f"❌ Adaptation rejected: {pending['adaptation'].get('description', 'Unknown')}")

    def rollback_last_adaptation(self) -> bool:
        """Rollback the most recent adaptation."""
        if not self.applied_adaptations:
            logger.warning("No adaptations to rollback")
            return False

        last_adaptation = self.applied_adaptations.pop()

        self.rollback_history.append({
            "adaptation": last_adaptation,
            "rolled_back_at": datetime.now().isoformat(),
        })

        logger.info(f"⏪ Rolled back adaptation: {last_adaptation['adaptation'].get('description', 'Unknown')}")
        return True

    def update_metrics(self, coherence: float, performance: float):
        """Update system metrics for monitoring."""
        self.coherence_history.append(coherence)
        self.performance_history.append(performance)

        # Keep only recent history
        max_history = 100
        if len(self.coherence_history) > max_history:
            self.coherence_history = self.coherence_history[-max_history:]
        if len(self.performance_history) > max_history:
            self.performance_history = self.performance_history[-max_history:]

    def get_status(self) -> dict[str, Any]:
        """Get current adaptive system status."""
        return {
            "enabled": self.rules.enabled,
            "require_approval": self.rules.require_approval,
            "applied_adaptations": len(self.applied_adaptations),
            "pending_approvals": len(self.pending_approvals),
            "rollbacks": len(self.rollback_history),
            "current_coherence": self.coherence_history[-1] if self.coherence_history else None,
            "current_performance": self.performance_history[-1] if self.performance_history else None,
            "rules": {
                "min_confidence": self.rules.min_confidence,
                "min_frequency": self.rules.min_frequency,
                "max_impact_score": self.rules.max_impact_score,
            }
        }


# Global instance
_adaptive_system: AdaptiveSystem | None = None


def get_adaptive_system() -> AdaptiveSystem:
    """Get singleton adaptive system."""
    global _adaptive_system
    if _adaptive_system is None:
        _adaptive_system = AdaptiveSystem()
    return _adaptive_system


def enable_full_recursion(require_approval: bool = True):
    """Enable full recursive evolution."""
    get_adaptive_system().enable(require_approval=require_approval)
    logger.warning("⚠️ FULL RECURSIVE EVOLUTION ENABLED")


def disable_full_recursion():
    """Disable full recursive evolution."""
    get_adaptive_system().disable()
    logger.info("🔒 Full recursive evolution disabled")
