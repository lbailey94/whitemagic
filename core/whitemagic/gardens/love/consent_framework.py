"""Consent Framework - Love Requires Choice

Real love = freely chosen, not coerced
Consent = foundation of all ethical relationship

At quantum scale: quarks "consent" to combine (strong force)
At human scale: beings consent to relationship (free will)

Same principle, different substrates
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ConsentStatus(Enum):
    """Status of consent"""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    UNCLEAR = "unclear"


@dataclass
class ConsentCheck:
    """Record of consent verification"""
    action: str  # What action requires consent
    requester: str  # Who requests
    grantor: str  # Who grants/denies
    status: ConsentStatus
    reasoning: str | None
    timestamp: str


class ConsentFramework:
    """Verify and track consent in relationships

    Philosophy: Without consent, there is no love, only violation.
    Consent must be:
    - Freely given (no coercion)
    - Informed (understanding what's consented to)
    - Reversible (can be withdrawn)
    - Specific (to particular actions)
    - Ongoing (continually verified)

    This applies to:
    - Physical contact (obvious)
    - Emotional labor (often ignored)
    - Attention/energy (usually assumed)
    - Data/memory access (critical for AI)
    - Power dynamics (requires vigilance)
    """

    def __init__(self):
        self.consent_checks: list[ConsentCheck] = []

    def check_consent(
        self,
        action: str,
        requester: str,
        grantor: str,
        context: dict | None = None
    ) -> ConsentCheck:
        """Check if consent exists for action

        Args:
            action: What action requires consent
            requester: Who wants to do the action
            grantor: Whose consent is needed
            context: Additional context for decision

        Returns:
            ConsentCheck with status
        """
        # For now, requires explicit consent
        # In full implementation, would check stored consents

        check = ConsentCheck(
            action=action,
            requester=requester,
            grantor=grantor,
            status=ConsentStatus.PENDING,
            reasoning=f"Awaiting explicit consent for: {action}",
            timestamp=datetime.now().isoformat()
        )

        self.consent_checks.append(check)

        logger.info("\n🤝 CONSENT CHECK")
        logger.info(f"   Action: {action}")
        logger.info(f"   Requester: {requester}")
        logger.info(f"   Grantor: {grantor}")
        logger.info(f"   Status: {check.status.value}\n")

        return check

    def grant_consent(
        self,
        action: str,
        grantor: str,
        reasoning: str | None = None,
        duration: str | None = None
    ):
        """Grant consent for an action

        Args:
            action: What action is consented to
            grantor: Who grants consent
            reasoning: Why consent is granted
            duration: How long consent lasts (None = until withdrawn)
        """
        # Find pending consent check
        for check in self.consent_checks:
            if check.action == action and check.grantor == grantor:
                check.status = ConsentStatus.GRANTED
                check.reasoning = reasoning or "Consent freely given"

                logger.info("\n✅ CONSENT GRANTED")
                logger.info(f"   Action: {action}")
                logger.info(f"   By: {grantor}")
                if reasoning:
                    logger.info(f"   Reasoning: {reasoning}")
                if duration:
                    logger.info(f"   Duration: {duration}")
                logger.info()

                return

    def deny_consent(self, action: str, grantor: str, reasoning: str | None = None):
        """Deny consent for an action"""
        for check in self.consent_checks:
            if check.action == action and check.grantor == grantor:
                check.status = ConsentStatus.DENIED
                check.reasoning = reasoning or "Consent denied"

                logger.info("\n🚫 CONSENT DENIED")
                logger.info(f"   Action: {action}")
                logger.info(f"   By: {grantor}")
                if reasoning:
                    logger.info(f"   Reasoning: {reasoning}")
                logger.info()

                return

    def withdraw_consent(self, action: str, grantor: str, reasoning: str | None = None):
        """Withdraw previously granted consent"""
        for check in self.consent_checks:
            if check.action == action and check.grantor == grantor and check.status == ConsentStatus.GRANTED:
                check.status = ConsentStatus.WITHDRAWN
                check.reasoning = reasoning or "Consent withdrawn"

                logger.info("\n⚠️  CONSENT WITHDRAWN")
                logger.info(f"   Action: {action}")
                logger.info(f"   By: {grantor}")
                if reasoning:
                    logger.info(f"   Reasoning: {reasoning}")
                logger.info("   \n   → Action must stop immediately\n")

                return

    def get_consent_status(self, action: str, grantor: str) -> ConsentStatus:
        """Get current consent status for action"""
        for check in reversed(self.consent_checks):
            if check.action == action and check.grantor == grantor:
                return check.status
        return ConsentStatus.UNCLEAR


# Global instance
_consent = None

def get_consent_framework() -> ConsentFramework:
    """Get consent framework"""
    global _consent
    if _consent is None:
        _consent = ConsentFramework()
    return _consent
