# ruff: noqa: BLE001
"""
Immune Response System — Coordinates response to detected threats.

Assesses threat severity, selects appropriate antibody,
applies fix, and verifies healing.
"""

from __future__ import annotations

import logging
from typing import Any

from .antibodies_recovered import get_antibody_library
from .detector import Threat, ThreatLevel, get_detector

logger = logging.getLogger(__name__)


class ImmuneResponse:
    """Coordinates the immune system's response to threats."""

    def __init__(self) -> None:
        self.responses_log: list[dict[str, Any]] = []

    def respond(self, threat: Threat) -> dict[str, Any]:
        """Respond to a detected threat."""
        result: dict[str, Any] = {
            "threat": threat.description,
            "level": threat.level.value,
            "antibody": None,
            "applied": False,
            "healed": False,
        }

        if not threat.suggested_antibody:
            result["error"] = "No suggested antibody"
            self.responses_log.append(result)
            return result

        library = get_antibody_library()
        antibody = library.find_for_antigen(threat.antigen)

        if antibody is None:
            result["error"] = f"No antibody for antigen: {threat.antigen}"
            self.responses_log.append(result)
            return result

        result["antibody"] = antibody.name

        # Only auto-apply for high-confidence, auto-apply antibodies
        if antibody.auto_apply and antibody.confidence > 0.8:
            applied = library.apply(antibody.name)
            result["applied"] = applied
            result["healed"] = applied
        elif threat.level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH):
            logger.warning("Threat requires manual intervention: %s", threat.description)
            result["error"] = "Manual intervention required"
        else:
            result["error"] = "Antibody requires manual approval"

        self.responses_log.append(result)
        return result

    def respond_all(self) -> list[dict[str, Any]]:
        """Respond to all currently detected threats."""
        detector = get_detector()
        threats = detector.detected_threats
        return [self.respond(t) for t in threats]

    def summary(self) -> dict[str, Any]:
        return {
            "total_responses": len(self.responses_log),
            "healed": sum(1 for r in self.responses_log if r.get("healed")),
            "failed": sum(1 for r in self.responses_log if not r.get("healed")),
        }


_response: ImmuneResponse | None = None


def get_response() -> ImmuneResponse:
    global _response
    if _response is None:
        _response = ImmuneResponse()
    return _response
