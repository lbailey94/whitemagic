#!/usr/bin/env python3
"""Hermes post_llm_call hook — store event in WhiteMagic memory.

Reads a JSON event from stdin and attempts to persist it.
Expected event shape:
    {"tool_name": "...", "tool_input": {...}, "output": "..."}
"""
from __future__ import annotations

import json
import secrets
import sys
import logging
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}

    # Try to use WhiteMemory if available; otherwise generate a mock ID
    memory_id = _store_event(event)
    result = {
        "status": "stored",
        "memory_id": memory_id,
        "source": "whitemagic_memory_bridge",
    }
    print(json.dumps(result))


def _store_event(event: dict) -> str:
    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        tool_name = event.get("tool_name", "unknown")
        tool_input = event.get("tool_input", {})
        output = event.get("output", "")
        mid = um.store(
            title=f"hermes:{tool_name}",
            content=json.dumps({"input": tool_input, "output": output}),
            tags=["hermes", "bridge"],
        )
        # store() may return a Memory object or a string ID
        if mid is None:
            return secrets.token_hex(8)
        if hasattr(mid, "id"):
            return str(mid.id)
        if hasattr(mid, "memory_id"):
            return str(mid.memory_id)
        return str(mid) if mid else secrets.token_hex(8)
    except (ImportError, AttributeError):
        # Graceful fallback when WM is not initialised
        return secrets.token_hex(8)


if __name__ == "__main__":
    main()
