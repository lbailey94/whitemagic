"""Startup prewarm for the MCP serving stack (P6.4 follow-up).

The lean server defers heavy imports to first tool invocation so the MCP
handshake completes in <1s. The tradeoff: the FIRST heavy dispatch pays
every cold-start cost at once — ``import torch`` (~15-40s on a loaded
machine), MiniLM weight load, semantic-defense corpus embedding, HNSW
index init — and can exceed the 20s client-facing dispatch timeout,
producing a timeout error on the very first ``search_memories`` a client
issues (observed live 2026-07-20).

This module moves that cold cost to server startup via a daemon thread:
the handshake stays fast, and the serving stack is warm by the time the
first real dispatch arrives. Disable with ``WM_PREWARM=0``.
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


def prewarm_serving_stack() -> dict[str, float]:
    """Eagerly initialize lazily-loaded heavy subsystems.

    Each stage is best-effort: failures are logged at DEBUG and never
    propagate (the dispatch paths degrade gracefully on their own).
    Returns per-stage durations for observability.
    """
    timings: dict[str, float] = {}

    # 1. Embedding engine (query/memory embeddings)
    t = time.monotonic()
    try:
        from whitemagic.core.memory.embeddings import get_embedding_engine

        engine = get_embedding_engine()
        if engine.available():
            engine.encode_batch(["prewarm"])
    except Exception as e:  # noqa: BLE001
        logger.debug("Prewarm: embedding engine skipped: %s", e)
    timings["embedding_engine_s"] = round(time.monotonic() - t, 3)

    # 2. Semantic-defense corpus (input sanitizer's ONNX corpus, ~114 docs)
    t = time.monotonic()
    try:
        from whitemagic.security.semantic_defense import combined_semantic_check

        combined_semantic_check("prewarm")
    except Exception as e:  # noqa: BLE001
        logger.debug("Prewarm: semantic defense skipped: %s", e)
    timings["semantic_defense_s"] = round(time.monotonic() - t, 3)

    # 3. Cross-encoder reranker explicitly: a bare recall can return zero
    #    candidates and skip the torch/ST load entirely (observed live),
    #    so force the model up with a synthetic document.
    t = time.monotonic()
    try:
        from whitemagic.core.memory.cross_encoder_reranker import (
            rerank_cross_encoder,
        )

        class _Doc:
            content = "prewarm document"
            metadata: dict = {}

        rerank_cross_encoder("prewarm", [_Doc()], top_k=1)
    except Exception as e:  # noqa: BLE001
        logger.debug("Prewarm: cross-encoder skipped: %s", e)
    timings["cross_encoder_s"] = round(time.monotonic() - t, 3)

    # 4. Full read-only dispatch: warms every middleware's lazy init
    #    (permissions, maturity gate, pattern guard, engagement tokens —
    #    ~17-26s cold on a production state root) plus DB/HNSW open.
    t = time.monotonic()
    try:
        from whitemagic.tools.unified_api import _dispatch_tool

        _dispatch_tool("search_memories", query="memory", limit=1)
    except Exception as e:  # noqa: BLE001
        logger.debug("Prewarm: dispatch warm skipped: %s", e)
    timings["dispatch_chain_s"] = round(time.monotonic() - t, 3)

    return timings


def prewarm_enabled() -> bool:
    """WM_PREWARM=0/false/no/off disables startup prewarm."""
    return os.environ.get("WM_PREWARM", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def start_prewarm_thread(name: str = "mcp-prewarm") -> threading.Thread | None:
    """Spawn the daemon prewarm thread; returns None when disabled."""
    if not prewarm_enabled():
        logger.info("Serving-stack prewarm disabled (WM_PREWARM=0)")
        return None

    def _run() -> None:
        t0 = time.monotonic()
        timings = prewarm_serving_stack()
        logger.info(
            "Serving-stack prewarm complete in %.1fs: %s",
            time.monotonic() - t0,
            timings,
        )

    thread = threading.Thread(target=_run, name=name, daemon=True)
    thread.start()
    return thread
