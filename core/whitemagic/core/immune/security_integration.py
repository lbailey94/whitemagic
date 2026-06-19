# ruff: noqa: BLE001
"""Security integration layer for the immune system.

Resurfaced from whitemagic-archive-aux SD-card archive (v0.1).
This module provides threat reporting and security event tracking,
building on the existing core.immune primitives.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def report_threat(
    threat_type: str,
    description: str = "",
    severity: str = "medium",
    source: str | None = None,
    context: dict[str, Any] | None = None,
    tool: str | None = None,
    params: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Report a security threat to the immune system.

    Args:
        threat_type: Category of threat (e.g. "injection", "unauthorized_access")
        description: Human-readable description
        severity: One of "low", "medium", "high", "critical"
        source: Optional source identifier
        context: Optional additional context
        tool: Optional tool name (for tool-gated threats)
        params: Optional tool parameters (for tool-gated threats)
        reason: Optional reason string (for tool-gated threats)

    Returns:
        dict with status, threat_id, and recorded info
    """
    import uuid

    from whitemagic.core.immune import ThreatDetector

    threat_id = str(uuid.uuid4())
    event: dict[str, Any] = {
        "threat_id": threat_id,
        "threat_type": threat_type,
        "description": description,
        "severity": severity,
        "source": source,
        "tool": tool,
        "params": params or {},
        "reason": reason,
        "context": context or {},
    }

    # Record via ThreatDetector if available
    if ThreatDetector is not None:
        try:
            detector = ThreatDetector()
            level_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            level = level_map.get(severity, 2)
            detector.record_event(event, level=level)
        except Exception as exc:
            logger.warning("Failed to record threat with ThreatDetector: %s", exc, exc_info=True)

    # Log always
    if severity in ("high", "critical"):
        logger.warning("Threat reported: %s", event)
    else:
        logger.info("Threat reported: %s", event)

    return {"status": "recorded", "threat_id": threat_id, "event": event}
