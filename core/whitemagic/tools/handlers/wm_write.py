# ruff: noqa: BLE001
"""wm_write — Unified Write Interface to the WhiteMagic Cognitive Stack.

Single entry point for all write operations. Auto-selects the best backend
and ensures full enrichment pipeline (holographic coords, embeddings, entity
extraction, surprise gate, galactic lifecycle) is applied.

Modes:
  auto          — Auto-detect best strategy (default)
  memory        — Store as a memory in UnifiedMemory (with full enrichment)
  scratchpad    — Write to ephemeral scratchpad (session-local)
  file          — Atomic file write (via fileio.atomic_write)
  neural        — Persist to neural memory store
  dream         — Write a dream artifact (low-confidence creative capture)
  oms           — Export as .mem package (OMS)

Usage via dispatch:
    dispatch("wm_write", content="Important finding", title="Key insight", mode="auto")
    dispatch("wm_write", content="Session notes", mode="scratchpad", scratchpad_id="s1")
    dispatch("wm_write", content="config data", mode="file", path="/tmp/config.json")
    dispatch("wm_write", content="creative idea", mode="dream", dream_type="bridge")
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _detect_mode(**kwargs: Any) -> str:
    """Auto-detect the best write strategy based on arguments."""
    # File write: path provided
    if kwargs.get("path") and not kwargs.get("title"):
        return "file"

    # Scratchpad: scratchpad_id provided
    if kwargs.get("scratchpad_id"):
        return "scratchpad"

    # Dream artifact: dream_type or low_confidence flag
    if kwargs.get("dream_type") or kwargs.get("low_confidence"):
        return "dream"

    # OMS export: oms_export flag
    if kwargs.get("oms_export"):
        return "oms"

    # Neural: neural_store flag
    if kwargs.get("neural_store"):
        return "neural"

    # Default: standard memory storage
    return "memory"


def handle_wm_write(**kwargs: Any) -> dict[str, Any]:
    """Unified write interface — auto-selects best strategy or uses explicit mode.

    Args (via kwargs):
        content: Content to write (required)
        title: Title for the content
        mode: Write strategy (auto, memory, scratchpad, file, neural, dream, oms)
        tags: List of tags for memory mode
        memory_type: Memory type string (short_term, long_term, emotional, etc.)
        importance: Importance score 0.0-1.0 (default 0.5)
        emotional_valence: Emotional valence -1.0 to 1.0 (default 0.0)
        metadata: Additional metadata dict
        auto_embed: Auto-generate embedding (default True)
        enable_surprise_gate: Enable surprise-gated ingestion (default True)
        enable_entity_extraction: Auto-extract entities (default True)
        enable_holographic_index: Auto-compute 5D coords (default True)
        is_private: Mark as private (excluded from MCP responses)
        model_exclude: Exclude from AI model context windows

        # Mode-specific:
        path: File path for file mode
        scratchpad_id: Scratchpad ID for scratchpad mode
        dream_type: Dream artifact type for dream mode
        oms_export: Flag for OMS export mode

    Returns:
        Standard dispatch envelope with write result and metadata.
    """
    content = kwargs.get("content")
    if content is None:
        return {"status": "error", "error": "content is required"}

    mode = kwargs.get("mode", "auto")
    if mode == "auto":
        mode = _detect_mode(**kwargs)

    try:
        if mode == "memory":
            result = _write_memory(kwargs)
        elif mode == "scratchpad":
            result = _write_scratchpad(kwargs)
        elif mode == "file":
            result = _write_file(kwargs)
        elif mode == "neural":
            result = _write_neural(kwargs)
        elif mode == "dream":
            result = _write_dream(kwargs)
        elif mode == "oms":
            result = _write_oms(kwargs)
        else:
            return {
                "status": "error",
                "error": f"Unknown write mode: {mode}",
                "available_modes": [
                    "auto",
                    "memory",
                    "scratchpad",
                    "file",
                    "neural",
                    "dream",
                    "oms",
                ],
            }

        # v23.1 Harmonic: ensure consolidation daemon is running after writes
        if isinstance(result, dict) and result.get("status") == "success":
            try:
                from whitemagic.core.memory.consolidation import (
                    get_consolidation_daemon,
                )

                daemon = get_consolidation_daemon()
                if not daemon._started:
                    daemon.start()
            except Exception:
                pass  # Consolidation daemon unavailable

        return result
    except Exception as exc:
        logger.error("wm_write failed (mode=%s): %s", mode, exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "mode": mode,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Mode Implementations
# ═══════════════════════════════════════════════════════════════════════════════


def _write_memory(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Store as a memory in UnifiedMemory with full enrichment pipeline."""
    from whitemagic.core.memory.unified import remember
    from whitemagic.core.memory.unified_types import MemoryType

    content = kwargs["content"]
    title = kwargs.get("title")
    tags = kwargs.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tag_set = {str(t).lower() for t in (tags or []) if str(t).strip()}

    memory_type_str = kwargs.get("memory_type") or kwargs.get("type") or "short_term"
    try:
        memory_type = MemoryType[memory_type_str.upper()]
    except (KeyError, ValueError):
        memory_type = MemoryType.SHORT_TERM

    metadata = dict(kwargs.get("metadata") or {})
    is_private = bool(kwargs.get("is_private", False))
    model_exclude = bool(kwargs.get("model_exclude", False))
    if is_private:
        metadata["is_private"] = True
    if model_exclude:
        metadata["model_exclude"] = True

    # Full enrichment pipeline — this is the key difference from handle_create_memory
    # which disables surprise gate, entity extraction, and holographic index
    store_kwargs: dict[str, Any] = {
        "content": content,
        "title": title.strip() if title else None,
        "tags": tag_set,
        "memory_type": memory_type,
        "importance": float(kwargs.get("importance", 0.5)),
        "emotional_valence": float(kwargs.get("emotional_valence", 0.0)),
        "metadata": metadata,
        "auto_embed": bool(kwargs.get("auto_embed", True)),
        "enable_surprise_gate": bool(kwargs.get("enable_surprise_gate", True)),
        "enable_entity_extraction": bool(kwargs.get("enable_entity_extraction", True)),
        "enable_holographic_index": bool(kwargs.get("enable_holographic_index", True)),
    }

    mem = remember(**store_kwargs)

    coords_populated = False
    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        coords = um.get_coords(mem.id)
        if coords and any(c is not None for c in coords):
            coords_populated = True
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)

    return {
        "status": "success",
        "mode": "memory",
        "memory_id": str(mem.id),
        "title": mem.title,
        "memory_type": mem.memory_type.name
        if hasattr(mem.memory_type, "name")
        else str(mem.memory_type),
        "tags": list(mem.tags) if mem.tags else [],
        "importance": mem.importance,
        "holographic_coords_populated": coords_populated,
        "enrichment": {
            "surprise_gate": store_kwargs["enable_surprise_gate"],
            "entity_extraction": store_kwargs["enable_entity_extraction"],
            "holographic_index": store_kwargs["enable_holographic_index"],
            "auto_embed": store_kwargs["auto_embed"],
        },
    }


def _write_scratchpad(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Write to ephemeral scratchpad (session-local)."""
    content = kwargs["content"]
    scratchpad_id = kwargs.get("scratchpad_id", "default")
    title = kwargs.get("title", "")

    try:
        from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

        mgr = ScratchpadManager()
        sp = mgr.get_or_create(scratchpad_id)
        sp.add_entry(content, title=title)
        return {
            "status": "success",
            "mode": "scratchpad",
            "scratchpad_id": scratchpad_id,
            "entry_count": len(sp.entries),
        }
    except Exception as exc:
        logger.debug("Scratchpad write failed, using inline: %s", exc)
        # Fallback: store as short-term memory with scratchpad tag
        from whitemagic.core.memory.unified import remember

        mem = remember(
            content=content,
            title=title,
            tags={"scratchpad", "ephemeral"},
            memory_type="short_term",
            auto_embed=False,
            enable_surprise_gate=False,
            enable_entity_extraction=False,
            enable_holographic_index=False,
        )
        return {
            "status": "success",
            "mode": "scratchpad",
            "memory_id": str(mem.id),
            "note": "Scratchpad unavailable, stored as short-term memory",
        }


def _write_file(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Atomic file write via fileio.atomic_write."""
    from pathlib import Path

    from whitemagic.utils.fileio import atomic_write

    path = kwargs.get("path")
    if not path:
        return {"status": "error", "error": "file mode requires a 'path' parameter"}

    content = str(kwargs["content"])
    atomic_write(Path(path), content)

    return {
        "status": "success",
        "mode": "file",
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
    }


def _write_neural(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Persist to neural memory store."""
    from whitemagic.core.memory.neural.persistence import NeuralMemoryStore

    content = kwargs["content"]
    title = kwargs.get("title", "")
    metadata = kwargs.get("metadata", {})

    store = NeuralMemoryStore()
    neural_id = store.save(
        content=str(content),
        title=title,
        metadata=metadata,
    )

    return {
        "status": "success",
        "mode": "neural",
        "neural_id": neural_id,
        "title": title,
    }


def _write_dream(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Write a dream artifact (low-confidence creative capture)."""
    from whitemagic.core.dreaming.dream_artifacts import DreamArtifactWriter

    content = kwargs["content"]
    title = kwargs.get("title", "")
    dream_type = kwargs.get("dream_type", "bridge")

    writer = DreamArtifactWriter()
    artifact = writer.capture(
        content=str(content),
        title=title,
        artifact_type=dream_type,
    )

    if artifact:
        return {
            "status": "success",
            "mode": "dream",
            "artifact_id": artifact.id,
            "artifact_path": str(artifact.path) if hasattr(artifact, "path") else None,
            "dream_type": dream_type,
        }
    else:
        # Fallback: store as emotional memory with dream tag
        from whitemagic.core.memory.unified import remember

        mem = remember(
            content=content,
            title=title,
            tags={"dream", "creative", dream_type},
            memory_type="emotional",
            auto_embed=True,
            enable_surprise_gate=True,
        )
        return {
            "status": "success",
            "mode": "dream",
            "memory_id": str(mem.id),
            "note": "DreamArtifactWriter unavailable, stored as emotional memory",
        }


def _write_oms(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Export as .mem package (OMS)."""
    from whitemagic.oms.manager import OMSManager

    content = kwargs["content"]
    title = kwargs.get("title", "Untitled")
    metadata = kwargs.get("metadata", {})

    manager = OMSManager()
    package = manager.export(
        content=str(content),
        title=title,
        metadata=metadata,
    )

    return {
        "status": "success",
        "mode": "oms",
        "package_id": package.id if hasattr(package, "id") else None,
        "package_path": str(package.path) if hasattr(package, "path") else None,
        "title": title,
    }


def handle_wm_write_status(**kwargs: Any) -> dict[str, Any]:
    """Get wm_write system status — available modes, backend availability."""
    status: dict[str, Any] = {
        "status": "success",
        "modes": ["auto", "memory", "scratchpad", "file", "neural", "dream", "oms"],
        "backends": {},
    }

    try:
        from whitemagic.core.memory.unified import get_unified_memory

        get_unified_memory()
        status["backends"]["unified_memory"] = "available"
    except Exception:
        status["backends"]["unified_memory"] = "unavailable"

    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        holographic = um.holographic
        status["backends"]["holographic_index"] = "available" if holographic else "lazy"
    except Exception:
        status["backends"]["holographic_index"] = "unavailable"

    try:
        from whitemagic.core.memory.embeddings import get_embedding_engine

        engine = get_embedding_engine()
        status["backends"]["embedding_engine"] = (
            "available" if engine.available() else "unavailable"
        )
    except Exception:
        status["backends"]["embedding_engine"] = "unavailable"

    try:
        from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

        ScratchpadManager()
        status["backends"]["scratchpad"] = "available"
    except Exception:
        status["backends"]["scratchpad"] = "unavailable"

    try:
        from whitemagic.core.memory.neural.persistence import NeuralMemoryStore

        NeuralMemoryStore()
        status["backends"]["neural_store"] = "available"
    except Exception:
        status["backends"]["neural_store"] = "unavailable"

    try:
        from whitemagic.core.dreaming.dream_artifacts import DreamArtifactWriter

        DreamArtifactWriter()
        status["backends"]["dream_artifact_writer"] = "available"
    except Exception:
        status["backends"]["dream_artifact_writer"] = "unavailable"

    try:
        from whitemagic.oms.manager import OMSManager

        OMSManager()
        status["backends"]["oms_manager"] = "available"
    except Exception:
        status["backends"]["oms_manager"] = "unavailable"

    try:
        status["backends"]["atomic_write"] = "available"
    except Exception:
        status["backends"]["atomic_write"] = "unavailable"

    return status
