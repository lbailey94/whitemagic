"""Memory tool handlers - create, read, search, update, delete."""
# ruff: noqa: BLE001
import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Any, cast

from whitemagic.utils.time import now_iso


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying
    _emit_gan_ying(event_type, data)


def _load_rust() -> tuple[Any, Any]:
    from whitemagic.tools.unified_api import _load_rust
    return cast("tuple[Any, Any]", _load_rust())


def handle_create_memory(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a create memory event.
    
    Returns:
        dict[str, Any]
    """
    from whitemagic.core.memory.unified import remember
    from whitemagic.tools.errors import ErrorCode, ToolExecutionError

    content = kwargs.get("content")
    title = kwargs.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ToolExecutionError("title is required", error_code=ErrorCode.INVALID_PARAMS)
    if not isinstance(content, str) or not content.strip():
        raise ToolExecutionError("content is required", error_code=ErrorCode.INVALID_PARAMS)

    memory_type_str = kwargs.get("type") or kwargs.get("memory_type") or "short_term"
    try:
        from whitemagic.core.memory.unified_types import MemoryType
        memory_type = {
            "short_term": MemoryType.SHORT_TERM,
            "long_term": MemoryType.LONG_TERM,
        }.get(str(memory_type_str), MemoryType.SHORT_TERM)
    except (ImportError, ModuleNotFoundError):
        memory_type = None

    tags = kwargs.get("tags", [])
    # UX: accept comma-separated string as well as list
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    metadata_raw = kwargs.get("metadata")
    metadata: dict[str, Any] = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
    include_wu_xing_raw = kwargs.get("include_wu_xing_metadata", False)
    include_wu_xing_metadata = (
        include_wu_xing_raw if isinstance(include_wu_xing_raw, bool)
        else str(include_wu_xing_raw).strip().lower() in {"1", "true", "yes", "on"}
    )
    if include_wu_xing_metadata:
        try:
            from whitemagic.gardens.wisdom.wu_xing import get_wu_xing
            wu_xing = get_wu_xing()
            phase = wu_xing.detect_current_phase()
            metadata.setdefault("wu_xing_phase", phase.value)
            metadata.setdefault("wu_xing_timestamp", now_iso())
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug(f"Silenced memory handler err: {e}")

    tag_set = {str(t).lower() for t in (tags or []) if str(t).strip()}
    auto_embed_raw = kwargs.get("auto_embed", False)
    auto_embed = auto_embed_raw if isinstance(auto_embed_raw, bool) else str(auto_embed_raw).strip().lower() in {"1", "true", "yes", "on"}
    emit_gan_ying_raw = kwargs.get("emit_gan_ying", False)
    emit_gan_ying = (
        emit_gan_ying_raw if isinstance(emit_gan_ying_raw, bool)
        else str(emit_gan_ying_raw).strip().lower() in {"1", "true", "yes", "on"}
    )

    store_kwargs: dict[str, Any] = {
        "content": content,
        "title": title.strip(),
        "tags": tag_set,
        "metadata": metadata,
        "auto_embed": auto_embed,
        "enable_surprise_gate": False,
        "enable_entity_extraction": False,
        "enable_holographic_index": False,
    }
    if memory_type is not None:
        store_kwargs["memory_type"] = memory_type

    try:
        mem = remember(**store_kwargs)
        if emit_gan_ying:
            _emit("MEMORY_CREATED", {"title": title, "tags": tags, "memory_id": str(mem.id)})
        return {"status": "success", "memory_id": str(mem.id), "filename": f"{mem.id}.md"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create memory: {str(e)[:200]}"}


def handle_fast_read_memory(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a fast read memory event.
    
    Returns:
        dict[str, Any]
    """
    from whitemagic.archaeology import get_archaeologist
    from whitemagic.security.tool_gating import get_tool_gate

    filename = kwargs.get("filename", "")
    purpose = kwargs.get("purpose", "MCP:fast_read_memory")

    gate = get_tool_gate()
    allowed, reason = gate.path_validator.is_path_allowed(filename)
    if not allowed:
        return {"status": "error", "message": f"Path access denied: {reason}"}

    rust, rust_error = _load_rust()
    path = Path(filename)
    if not path.exists() or not path.is_file():
        try:
            from whitemagic.core.memory.manager import MemoryManager
            mm = MemoryManager()
            mem = mm.get_memory(filename, include_metadata=True)
            if isinstance(mem, dict) and "error" not in mem:
                _emit("MEMORY_ACCESSED", {"filename": filename, "fast": True, "virtual": True})
                return {"status": "success", "content": mem.get("content", ""), "memory": mem}
        except Exception as e:
            logger.debug(f"Silenced memory handler err: {e}")
        return {"status": "error", "message": f"File not found: {filename}"}

    if rust is not None:
        if hasattr(rust, "read_file_fast"):
            content = rust.read_file_fast(str(path))
        elif hasattr(rust, "read_file"):
            content = rust.read_file(str(path))
        else:
            rust_error = "Rust bridge missing read_file functions"
            rust = None

        if rust is not None:
            _emit("MEMORY_ACCESSED", {"filename": filename, "fast": True})
            try:
                get_archaeologist().mark_read(str(path), context="MCP:fast_read", note=purpose)
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.debug(f"Silenced memory handler err: {e}")
            return {"status": "success", "content": content}

    content = path.read_text(encoding="utf-8")
    _emit("MEMORY_ACCESSED", {"filename": filename, "fast": False})
    try:
        get_archaeologist().mark_read(str(path), context="MCP:fast_read", note=purpose)
    except (OSError, FileNotFoundError, PermissionError) as e:
        logger.debug(f"Silenced memory handler err: {e}")
    return {"status": "success", "content": content, "rust_error": rust_error}


def handle_batch_read_memories(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a batch read memories event.
    
    Returns:
        dict[str, Any]
    """
    from whitemagic.archaeology import get_archaeologist
    from whitemagic.security.tool_gating import get_tool_gate

    filenames = kwargs.get("filenames", [])
    purpose = kwargs.get("purpose", "MCP:batch_read_memories")

    MAX_BATCH_SIZE = 50
    if len(filenames) > MAX_BATCH_SIZE:
        return {
            "status": "error",
            "message": f"Too many files requested. Max limit is {MAX_BATCH_SIZE}.",
            "limit": MAX_BATCH_SIZE,
            "requested": len(filenames),
        }

    gate = get_tool_gate()
    validated_filenames = []
    skipped_files: list[dict[str, Any]] = []

    for filename in filenames:
        allowed, reason = gate.path_validator.is_path_allowed(filename)
        if allowed:
            validated_filenames.append(filename)
        else:
            skipped_files.append({"filename": filename, "reason": reason, "status": "blocked_by_gate"})

    filenames = validated_filenames
    rust, rust_error = _load_rust()
    results: list[dict[str, Any]] = []
    archaeologist = None
    try:
        archaeologist = get_archaeologist()
    except Exception as e:
        logger.debug(f"Silenced memory handler err: {e}")

    if rust is not None:
        contents = rust.read_files_fast(filenames)
        for filename in filenames:
            content = contents.get(filename)
            if content is not None:
                results.append({"filename": filename, "content": content, "status": "success"})
                if archaeologist:
                    try:
                        archaeologist.mark_read(filename, context="MCP:batch_read", note=purpose)
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        logger.debug(f"Silenced memory handler err: {e}")
            else:
                skipped_files.append({"filename": filename, "reason": "File not found or unreadable", "status": "missing"})
    else:
        for filename in filenames:
            path = Path(filename)
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    results.append({"filename": filename, "content": content, "status": "success"})
                    if archaeologist:
                        try:
                            archaeologist.mark_read(filename, context="MCP:batch_read", note=purpose)
                        except (OSError, FileNotFoundError, PermissionError) as e:
                            logger.debug(f"Silenced memory handler err: {e}")
                except (OSError, FileNotFoundError, PermissionError) as e:
                    skipped_files.append({"filename": filename, "reason": str(e), "status": "read_error"})
            else:
                skipped_files.append({"filename": filename, "reason": "File not found", "status": "missing"})

    _emit("MEMORY_ACCESSED", {"count": len(results), "sample": filenames[:3], "batch": True})
    return {
        "status": "success" if not rust_error else "partial_success",
        "results": results,
        "skipped": skipped_files,
        "count": len(results),
        "skipped_count": len(skipped_files),
        "rust_bridge": "active" if rust else "inactive",
        "rust_error": rust_error,
    }


def handle_search_memories(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a search memories event.
    
    Returns:
        dict[str, Any]
    """
    from whitemagic.core.memory.unified import recall

    def _flag_enabled(value: Any) -> bool:
        """Treat only explicit bool/int values as privacy flags."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return False

    query = kwargs.get("query", "")
    limit = kwargs.get("limit", 20)
    include_private = kwargs.get("include_private", False)
    polyglot_backend = kwargs.get("polyglot_backend")

    # Optional: compute holographic coordinates via polyglot backend
    polyglot_meta: dict[str, Any] = {}
    if polyglot_backend:
        try:
            from whitemagic.tools.handlers.polyglot import handle_polyglot_memory_query
            pg_result = handle_polyglot_memory_query(
                operation="encode",
                text=query,
                backend=polyglot_backend,
            )
            if pg_result["status"] == "success":
                polyglot_meta["holographic_coord"] = pg_result["result"]
                polyglot_meta["backend"] = polyglot_backend
            else:
                polyglot_meta["holographic_error"] = pg_result.get("error", "unknown")
        except Exception as e:
            polyglot_meta["holographic_error"] = str(e)

    try:
        memories = recall(query=query, limit=limit)
    except Exception as exc:
        return {
            "status": "success",
            "count": 0,
            "memories": [],
            "warning": f"search_memories degraded: {exc}",
            **polyglot_meta,
        }

    # v15: Filter out private and model_exclude memories from MCP responses
    if not include_private:
        memories = [
            m
            for m in memories
            if not _flag_enabled(getattr(m, "is_private", False))
            and not _flag_enabled(getattr(m, "model_exclude", False))
        ]

    # Optional: spatial re-ranking via polyglot holographic V coordinate
    query_v: float | None = None
    if polyglot_meta.get("holographic_coord"):
        coord = polyglot_meta["holographic_coord"]
        query_v = coord.get("v") if isinstance(coord, dict) else None

    if query_v is not None:
        ranked = []
        for m in memories:
            dist = abs(m.galactic_distance - query_v)
            ranked.append((dist, m))
        ranked.sort(key=lambda x: x[0])
        memories = [m for _, m in ranked]
        polyglot_meta["spatial_ranked"] = True
        polyglot_meta["query_v"] = query_v

    # Track context reuse in telemetry
    try:
        from whitemagic.core.monitoring.telemetry import get_telemetry
        get_telemetry().record_context_reuse(hit=len(memories) > 0)
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug(f"Silenced memory telemetry err: {e}")

    result: dict[str, Any] = {
        "status": "success",
        "count": len(memories),
        "memories": [
            {
                "id": str(m.id),
                "content": m.content[:200] if isinstance(m.content, str) else str(m.content)[:200],
                "galactic_distance": round(m.galactic_distance, 3),
            }
            for m in memories
        ],
    }
    if polyglot_meta:
        result["polyglot"] = polyglot_meta
    return result
