"""Scratchpad tool handlers."""

# ruff: noqa: BLE001
import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


ScratchpadHandler = Callable[..., dict[str, Any]]


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying

    _emit_gan_ying(event_type, data)


def _resolve_base_path(kwargs: dict[str, Any]) -> Path:
    from whitemagic.tools.unified_api import _resolve_base_path as _rbp

    return cast("Path", _rbp(kwargs))


def handle_scratchpad(**kwargs: Any) -> dict[str, Any]:
    """Unified scratchpad handler — routes by action parameter."""
    action = kwargs.get("action", "create")
    dispatch: dict[str, ScratchpadHandler] = {
        "create": handle_scratchpad_create,
        "update": handle_scratchpad_update,
        "finalize": handle_scratchpad_finalize,
    }
    handler = dispatch.get(action)
    if not handler:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Valid: {sorted(dispatch.keys())}",
        }
    return handler(**kwargs)


def handle_scratchpad_create(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a scratchpad create event.

    Returns:
        dict[str, Any]
    """
    from uuid import uuid4

    from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager
    from whitemagic.utils import slugify

    base_path = _resolve_base_path(kwargs)
    name = kwargs.get("name", "scratchpad")
    scratchpad_id = slugify(name) or f"scratch-{uuid4().hex[:6]}"
    focus = kwargs.get("session_id")
    manager = ScratchpadManager(scratch_dir=base_path / "scratchpads")
    pad = manager.create(scratchpad_id, focus=focus)
    _emit(
        "WORKING_MEMORY_UPDATED",
        {"action": "create", "scratchpad_id": scratchpad_id, "focus": focus},
    )
    return {
        "status": "success",
        "scratchpad": {
            "id": scratchpad_id,
            "name": pad.name,
            "focus": pad.focus,
            "created": pad.created.isoformat(),
        },
    }


def handle_scratchpad_update(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a scratchpad update event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

    base_path = _resolve_base_path(kwargs)
    manager = ScratchpadManager(scratch_dir=base_path / "scratchpads")

    scratchpad_id = kwargs.get("scratchpad_id")
    if not scratchpad_id:
        if manager.scratchpads:
            sorted_pads = sorted(
                manager.scratchpads.values(), key=lambda p: p.created, reverse=True
            )
            scratchpad_id = sorted_pads[0].name
        else:
            # Auto-create one if none exist
            return handle_scratchpad_create(**kwargs)

    content = kwargs.get("content", "Continuing thought...")
    section = kwargs.get("section", "current_focus")
    if scratchpad_id not in manager.scratchpads:
        pad = manager.create(scratchpad_id)
        scratchpad_id = pad.name

    # Chain state params (sequential-thinking compatibility)
    thought_number = kwargs.get("thought_number")
    total_thoughts = kwargs.get("total_thoughts")
    branch_id = kwargs.get("branch_id")
    branch_from = kwargs.get("branch_from")
    is_revision = kwargs.get("is_revision", False)
    revises_entry = kwargs.get("revises_entry")

    entry = manager.write_to(
        scratchpad_id,
        content,
        tag=section,
        thought_number=thought_number,
        total_thoughts=total_thoughts,
        branch_id=branch_id,
        branch_from=branch_from,
        is_revision=is_revision,
        revises_entry=revises_entry,
    )

    # v23.1: Bridge scratchpad writes into WorkingMemory
    try:
        from whitemagic.core.intelligence.working_memory import get_working_memory

        wm = get_working_memory()
        wm.attend(
            memory_id=f"scratchpad:{scratchpad_id}:{section}",
            content=content,
            title=f"Scratchpad {scratchpad_id} / {section}",
            importance=0.6,
            tags=["scratchpad", section or "notes"],
        )
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)

    chain_status = manager.get_chain_status(scratchpad_id)
    _emit(
        "WORKING_MEMORY_UPDATED",
        {"action": "update", "scratchpad_id": scratchpad_id, "section": section},
    )
    return {
        "status": "success",
        "scratchpad_id": scratchpad_id,
        "section": section,
        "thought_number": entry.get("thought_number"),
        "total_thoughts": entry.get("total_thoughts"),
        "thought_history_length": chain_status.get("thought_history_length", 0),
        "branches": chain_status.get("branches", []),
        "branch_count": chain_status.get("branch_count", 0),
        "is_revision": entry.get("is_revision", False),
    }


def handle_analyze_scratchpad(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a analyze scratchpad event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.intelligence.multi_spectral_scratchpad import (
        analyze_scratchpad,
    )
    from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

    base_path = _resolve_base_path(kwargs)
    scratchpad_id = kwargs.get("scratchpad_id")
    if not scratchpad_id:
        return {"status": "error", "error_code": "invalid_params", "message": "scratchpad_id is required"}
    manager = ScratchpadManager(scratch_dir=base_path / "scratchpads")
    pad = manager.scratchpads.get(scratchpad_id)
    if not pad:
        return {"status": "error", "error_code": "not_found", "message": f"Scratchpad not found: {scratchpad_id}"}
    sections = defaultdict(list)
    for entry in pad.entries:
        sections[entry.get("tag") or "notes"].append(entry.get("content", ""))
    content_dict = {name: "\n".join(items) for name, items in sections.items()}
    analysis = analyze_scratchpad(content_dict)
    return {
        "status": "success",
        "scratchpad_id": scratchpad_id,
        "analysis": {
            "synthesis": analysis.synthesis,
            "wisdom": analysis.wisdom,
            "confidence": analysis.confidence,
            "perspectives": analysis.perspectives,
            "patterns_matched": analysis.patterns_matched,
            "reasoning_chain": analysis.reasoning_chain,
        },
    }


def handle_scratchpad_finalize(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a scratchpad finalize event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.memory.manager import MemoryManager
    from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

    base_path = _resolve_base_path(kwargs)
    manager = ScratchpadManager(scratch_dir=base_path / "scratchpads")

    scratchpad_id = kwargs.get("scratchpad_id")
    if not scratchpad_id:
        if manager.scratchpads:
            sorted_pads = sorted(
                manager.scratchpads.values(), key=lambda p: p.created, reverse=True
            )
            scratchpad_id = sorted_pads[0].name
        else:
            return {"status": "error", "message": "No active scratchpad to finalize"}

    memory_type = kwargs.get("memory_type", "long_term")
    auto_analyze = kwargs.get("auto_analyze", True)
    pad = manager.scratchpads.get(scratchpad_id)
    if not pad:
        return {"status": "error", "message": f"Scratchpad not found: {scratchpad_id}"}
    sections = defaultdict(list)
    for entry in pad.entries:
        sections[entry.get("tag") or "notes"].append(entry.get("content", ""))
    content_dict = {name: "\n".join(items) for name, items in sections.items()}
    analysis_result = None
    if auto_analyze:
        try:
            from whitemagic.core.intelligence.multi_spectral_scratchpad import (
                analyze_scratchpad,
                serialize_scratchpad_with_analysis,
            )

            analysis = analyze_scratchpad(content_dict)
            content = serialize_scratchpad_with_analysis(
                content_dict, analysis, title=f"Scratchpad: {pad.name}"
            )
            analysis_result = {
                "confidence": analysis.confidence,
                "patterns_matched": analysis.patterns_matched,
                "perspectives_used": len(analysis.perspectives),
            }
        except Exception as e:
            logger.warning("Multi-spectral analysis failed: %s", e, exc_info=True)
            lines = [f"# Scratchpad: {pad.name}"]
            if pad.focus:
                lines.append(f"Focus: {pad.focus}")
            for section_name, items in sections.items():
                lines.append(f"\n## {section_name.title()}")
                for item in items:
                    lines.append(item)
            content = "\n".join(lines).strip()
    else:
        lines = [f"# Scratchpad: {pad.name}"]
        if pad.focus:
            lines.append(f"Focus: {pad.focus}")
        for section_name, items in sections.items():
            lines.append(f"\n## {section_name.title()}")
            for item in items:
                lines.append(item)
        content = "\n".join(lines).strip()
    memory_manager = MemoryManager(base_dir=str(base_path))
    tags = ["scratchpad", "auto-finalized"]
    if analysis_result:
        tags.append("multi-spectral")
        tags.append(f"confidence-{int(analysis_result['confidence'] * 100)}")
    memory_path = memory_manager.create_memory(
        title=f"Scratchpad: {pad.name}",
        content=content,
        memory_type=memory_type,
        tags=tags,
    )
    scratchpad_file = manager.scratch_dir / f"{pad.name}.json"
    if scratchpad_file.exists():
        scratchpad_file.unlink()
    if pad.name in manager.scratchpads:
        del manager.scratchpads[pad.name]
    event_data = {
        "action": "finalize",
        "scratchpad_id": scratchpad_id,
        "memory_path": str(memory_path),
        "analyzed": auto_analyze,
    }
    if analysis_result:
        event_data.update(analysis_result)
    _emit("SCRATCHPAD_FINALIZED", event_data)
    result = {
        "status": "success",
        "scratchpad_id": scratchpad_id,
        "memory_path": str(memory_path),
        "analyzed": auto_analyze,
    }
    if analysis_result:
        result["analysis"] = analysis_result

    # Wire finalized scratchpad insights into working memory (v23.2)
    try:
        from whitemagic.core.intelligence.working_memory import get_working_memory

        wm = get_working_memory()
        # Attend to the finalized memory with importance based on analysis confidence
        importance = 0.5
        if analysis_result and "confidence" in analysis_result:
            importance = min(0.9, max(0.3, analysis_result["confidence"]))
        wm.attend(
            memory_id=f"scratchpad:{scratchpad_id}",
            content=content[:500],
            title=f"Scratchpad: {pad.name}",
            importance=importance,
            tags=tags,
        )
        result["working_memory_attended"] = True
    except Exception:
        result["working_memory_attended"] = False

    # v23.3: VSA context compression — pack scratchpad entries into HRR vector
    try:
        from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor

        compressor = get_vsa_context_compressor()
        vsa_items = [
            {
                "content": e.get("content", ""),
                "source": "scratchpad",
                "id": e.get("tag", ""),
            }
            for e in pad.entries
            if e.get("content")
        ]
        if vsa_items:
            vsa_result = compressor.compress(vsa_items, max_text_items=3)
            result["vsa_compression"] = {
                "item_count": vsa_result.item_count,
                "original_tokens": vsa_result.original_tokens,
                "compressed_tokens": vsa_result.compressed_tokens,
                "compression_ratio": vsa_result.compression_ratio,
                "method": vsa_result.method,
                "summary": vsa_result.summary,
                "latency_ms": round(vsa_result.latency_ms, 2),
            }
    except Exception:
        pass  # VSA compression is best-effort

    return result
