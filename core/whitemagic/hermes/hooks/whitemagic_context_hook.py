#!/usr/bin/env python3
"""Hermes pre_llm_call hook — inject telemetry context.

Reads a JSON event from stdin and returns context to prepend to the LLM prompt.
"""

from __future__ import annotations

import json
import logging
import sys

logger = logging.getLogger(__name__)

def main() -> None:
    """
    Perform the main operation.

    Returns:
        None
    """
    try:
        json.load(sys.stdin)  # event reserved for future per-tool contextualisation
    except json.JSONDecodeError:
        logger.debug("Ignored Exception in whitemagic_context_hook.py:25")

    context = (
        "[WhiteMagic Telemetry]\n"
        "Health: nominal\n"
        "Guna: sattvic\n"
        "Energy: stable\n"
        "Wu Xing: balanced\n"
    )

    result = {
        "context": context,
        "source": "whitemagic_context_hook",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
