"""Handlers for Corpus Callosum Bus tools.

Tools:
  corpus_callosum.debate — Initiate a bicameral debate on a topic
  corpus_callosum.status — Show debate statistics
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.tools.unified_api import make_result

logger = logging.getLogger(__name__)


def handle_corpus_callosum_debate(params: dict[str, Any]) -> dict[str, Any]:
    """Initiate a Corpus Callosum debate between hemispheres."""
    try:
        from whitemagic.core.intelligence.corpus_callosum import get_corpus_callosum_bus

        topic = params.get("topic", "")
        if not topic:
            return make_result(
                "corpus_callosum.debate", {}, error="Missing 'topic' parameter"
            )

        bus = get_corpus_callosum_bus()
        result = bus.debate(topic)
        data = result.to_dict()

        # If escalated, emit a warning in the response
        if result.escalated:
            data["warning"] = (
                "Tension exceeded safe threshold. Wisdom Council review recommended."
            )

        return make_result("corpus_callosum.debate", data)
    except Exception as exc:
        logger.error("corpus_callosum.debate error: %s", exc, exc_info=True)
        return make_result("corpus_callosum.debate", {}, error=str(exc))


def handle_corpus_callosum_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get Corpus Callosum Bus statistics."""
    try:
        from whitemagic.core.intelligence.corpus_callosum import get_corpus_callosum_bus

        bus = get_corpus_callosum_bus()
        return make_result("corpus_callosum.status", bus.status())
    except Exception as exc:
        logger.error("corpus_callosum.status error: %s", exc, exc_info=True)
        return make_result("corpus_callosum.status", {}, error=str(exc))
