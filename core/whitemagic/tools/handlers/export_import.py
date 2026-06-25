"""MCP handlers for memory export/import."""

from typing import Any


def handle_export_memories(**kwargs: Any) -> dict[str, Any]:
    """Export memories in JSON, CSV, Markdown, or ZIP format."""
    from whitemagic.core.memory.unified import get_unified_memory
    from whitemagic.tools.export.manager import (
        ExportImportManager,
        ExportRequest,
        MemoryExport,
    )

    fmt = kwargs.get("format", "json")
    tags = kwargs.get("tags")
    memory_type = kwargs.get("memory_type")
    search = kwargs.get("search")
    limit = int(kwargs.get("limit", 100))
    include_metadata = kwargs.get("include_metadata", True)

    # Build filters
    filters = {}
    if tags:
        filters["tags"] = tags if isinstance(tags, list) else [tags]
    if memory_type:
        filters["memory_type"] = memory_type.upper()
    if search:
        filters["search"] = search

    # Load memories
    um = get_unified_memory()
    raw = um.list_recent(limit=limit)
    memories = [
        MemoryExport(
            id=m.id,
            title=m.title or "",
            content=str(m.content),
            memory_type=m.memory_type.name,
            tags=list(m.tags),
            metadata=m.metadata,
            created_at=m.created_at.isoformat(),
            updated_at=m.accessed_at.isoformat(),
        )
        for m in raw
    ]

    mgr = ExportImportManager()
    request = ExportRequest(
        format=fmt,
        filters=filters or None,
        include_metadata=include_metadata,
        compress=bool(kwargs.get("compress", False)),
    )
    result = mgr.export_memories(memories, request)
    return {"status": "success", **result}


def handle_import_memories(**kwargs: Any) -> dict[str, Any]:
    """Import memories from JSON, CSV, or Markdown data."""
    from whitemagic.tools.export.manager import ExportImportManager, ImportRequest

    fmt = kwargs.get("format", "json")
    data = kwargs.get("data", "")
    merge_strategy = kwargs.get("merge_strategy", "skip")
    validate_only = kwargs.get("validate_only", False)

    if not data:
        return {"status": "error", "message": "data is required"}

    mgr = ExportImportManager()
    request = ImportRequest(
        format=fmt,
        data=data,
        merge_strategy=merge_strategy,
        validate_only=validate_only,
    )
    result = mgr.import_memories(request)
    return {"status": "success" if result.get("success") else "error", **result}


# ---------------------------------------------------------------------------
# CodeGenome facade (fused from CodeGenomeEngine)
# ---------------------------------------------------------------------------

def handle_codegenome_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate code from a named template."""
    from whitemagic.codegenome.engine import CodeGenomeEngine
    template_name = kwargs.get("template_name", "")
    if not template_name:
        return {"status": "error", "message": "template_name is required"}
    tier = kwargs.get("tier")
    variables = {k: v for k, v in kwargs.items() if k not in ("template_name", "tier")}
    engine = CodeGenomeEngine()
    rendered = engine.render(template_name, tier=tier, **variables)
    return {"status": "success", "template": template_name, "code": rendered}


def handle_codegenome_list(**kwargs: Any) -> dict[str, Any]:
    """List available code templates."""
    from whitemagic.codegenome.engine import CodeGenomeEngine
    tag = kwargs.get("tag")
    engine = CodeGenomeEngine()
    templates = engine.list_templates(tag=tag)
    return {"status": "success", "templates": templates, "count": len(templates)}


def handle_codegenome_status(**kwargs: Any) -> dict[str, Any]:
    """Get CodeGenome engine status."""
    from whitemagic.codegenome.engine import CodeGenomeEngine
    engine = CodeGenomeEngine()
    return {"status": "success", **engine.status()}


# ---------------------------------------------------------------------------
# PromptEngine facade (fused from PromptEngine)
# ---------------------------------------------------------------------------

def handle_prompt_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate a prompt from a named template."""
    from whitemagic.prompts.engine import PromptEngine
    template_name = kwargs.get("template_name", "")
    if not template_name:
        return {"status": "error", "message": "template_name is required"}
    wu_xing = kwargs.get("wu_xing")
    variables = {k: v for k, v in kwargs.items() if k not in ("template_name", "wu_xing")}
    engine = PromptEngine()
    rendered = engine.render(template_name, wu_xing=wu_xing, **variables)
    return {"status": "success", "template": template_name, "prompt": rendered}


def handle_prompt_list(**kwargs: Any) -> dict[str, Any]:
    """List available prompt templates."""
    from whitemagic.prompts.engine import PromptEngine
    tag = kwargs.get("tag")
    engine = PromptEngine()
    templates = engine.list_templates(tag=tag)
    return {"status": "success", "templates": templates, "count": len(templates)}


def handle_prompt_status(**kwargs: Any) -> dict[str, Any]:
    """Get PromptEngine status."""
    from whitemagic.prompts.engine import PromptEngine
    engine = PromptEngine()
    return {"status": "success", **engine.status()}
