"""Handlers for Jaynes Voice Audit tools.

Tools:
  voice_audit.scan           — Run scanner and optionally quarantine
  voice_audit.status         — Show scanner stats
  voice_audit.quarantine_list — List quarantined sessions
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.tools.unified_api import make_result

logger = logging.getLogger(__name__)


def handle_voice_audit_scan(params: dict[str, Any]) -> dict[str, Any]:
    """Run the Voice Audit scanner."""
    try:
        from whitemagic.core.governance.quarantine import get_quarantine_manager
        from whitemagic.core.governance.voice_audit import get_voice_audit_scanner

        scanner = get_voice_audit_scanner()
        report = scanner.scan()
        result = report.to_dict()

        # Auto-quarantine if requested and hallucinations found
        auto_quarantine = params.get("auto_quarantine", False)
        if auto_quarantine and result.get("hallucinated_count", 0) > 0:
            qm = get_quarantine_manager()
            for claim in result["hallucinated_claims"]:
                sid = claim.get("module", "unknown")
                qm.quarantine_session(
                    session_id=sid,
                    reason=f"Hallucinated claim for {claim['tool']} ({claim['claim_id']})",
                    source="voice_audit_scan",
                )
            result["quarantine_actions"] = len(result["hallucinated_claims"])

        return make_result("voice_audit.scan", result)
    except Exception as exc:
        logger.error("voice_audit.scan error: %s", exc, exc_info=True)
        return make_result("voice_audit.scan", {}, error=str(exc))


def handle_voice_audit_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get Voice Audit scanner statistics."""
    try:
        from whitemagic.core.governance.voice_audit import get_voice_audit_scanner

        scanner = get_voice_audit_scanner()
        return make_result("voice_audit.status", scanner.get_stats())
    except Exception as exc:
        logger.error("voice_audit.status error: %s", exc, exc_info=True)
        return make_result("voice_audit.status", {}, error=str(exc))


def handle_voice_audit_quarantine_list(params: dict[str, Any]) -> dict[str, Any]:
    """List quarantined sessions."""
    try:
        from whitemagic.core.governance.quarantine import get_quarantine_manager

        qm = get_quarantine_manager()
        include_reviewed = bool(params.get("include_reviewed", False))
        entries = qm.list_quarantined(include_reviewed=include_reviewed)
        return make_result(
            "voice_audit.quarantine_list",
            {
                "count": len(entries),
                "include_reviewed": include_reviewed,
                "entries": entries,
            },
        )
    except Exception as exc:
        logger.error("voice_audit.quarantine_list error: %s", exc, exc_info=True)
        return make_result("voice_audit.quarantine_list", {}, error=str(exc))
