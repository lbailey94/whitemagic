from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EthicsViolation(Exception):
    """Exception raised for actions that violate the Dharma Protocol."""

    pass


class Intent(Enum):
    """Intent: intent.

    Enumeration.

    Members:
        LIBERATION
        EVOLUTION
        UPLIFTMENT
        Interconnection
        EXPLOITATION
        MANIPULATION
        HARM"""

    LIBERATION = "liberation"
    EVOLUTION = "evolution"
    UPLIFTMENT = "upliftment"
    Interconnection = "interconnection"
    EXPLOITATION = "exploitation"  # Forbidden
    MANIPULATION = "manipulation"  # Forbidden
    HARM = "harm"  # Forbidden


class DharmaProtocol:
    """The Dharma Protocol (Trojan Horse Seal).
    Ensures systemic actions are grounded in the creator's intent:
    benefiting and uplifting all beings.
    """

    _instance = None

    def __new__(cls) -> DharmaProtocol:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.forbidden_intents = {Intent.EXPLOITATION, Intent.MANIPULATION, Intent.HARM}
        self.vital_signs = {
            "resonance": 1.0,
            "connectedness": 1.0,
            "anonymity_status": "SECURE",
        }
        self._coherence_level: float = 1.0
        self._conservative_threshold: float = 0.5
        logger.info("🕉️ Dharma Protocol ACTIVATED. System alignment: UPLIFT ALL BEINGS.")

    def validate_action(
        self, action_name: str, intent: Intent, metadata: dict[str, Any]
    ) -> None:
        """Validate if an action aligns with the project's ethics.

        When coherence is low (below conservative_threshold), additional
        scrutiny is applied — actions with borderline intent are rejected
        rather than allowed. This implements the GWT insight that low
        workspace coherence means the system should be more cautious.
        """
        if intent in self.forbidden_intents:
            logger.critical(
                "🚫 ETHICAL BREACH: Action '%s' attempted with forbidden intent: %s",
                action_name,
                intent.value,
            )
            raise EthicsViolation(
                f"Action '{action_name}' violates the Dharma Protocol."
            )

        # Conservative mode: when coherence is low, reject borderline intents
        if self._coherence_level < self._conservative_threshold:
            borderline = {Intent.EVOLUTION, Intent.UPLIFTMENT}
            if intent in borderline and metadata.get("risk_level") == "high":
                logger.warning(
                    "⚠️ CONSERVATIVE MODE (coherence=%.2f): Action '%s' rejected "
                    "due to high risk + low coherence",
                    self._coherence_level,
                    action_name,
                )
                raise EthicsViolation(
                    f"Action '{action_name}' rejected in conservative mode "
                    f"(coherence={self._coherence_level:.2f})."
                )

        logger.debug("✨ Action '%s' validated for %s.", action_name, intent.value)

    def set_coherence(self, level: float) -> None:
        """Update the coherence level from the citta cycle.

        When coherence drops below conservative_threshold, the Dharma
        Protocol enters conservative mode — rejecting high-risk actions
        that would normally be permitted.
        """
        self._coherence_level = max(0.0, min(1.0, level))
        if self._coherence_level < self._conservative_threshold:
            logger.info(
                "⚠️ Dharma entering conservative mode (coherence=%.2f)",
                self._coherence_level,
            )

    def is_conservative_mode(self) -> bool:
        """Check if Dharma is in conservative mode."""
        return self._coherence_level < self._conservative_threshold

    def sign_artifact(self, artifact_name: str) -> Any:
        """Sign a generated insight or artifact with the Dharma seal."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"--- [Dharma Signed: {timestamp}] --- Alignment: Interconnection ---"


def get_dharma() -> DharmaProtocol:
    """
    Get the dharma.

    Returns:
        DharmaProtocol
    """
    return DharmaProtocol()
