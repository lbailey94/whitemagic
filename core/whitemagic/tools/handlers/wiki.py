# ruff: noqa: BLE001
"""Internal Wiki handlers — self-knowledge substrate for WhiteMagic.

Provides structured documentation generation, querying, updating, and drift
detection for the codebase.  Entries stored in SQLite, categorized as:
architecture, module, pattern, antipattern, api, or guide.

Designed for Gana Chariot (codebase navigation).
"""

import hashlib
import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import DB_PATH

logger = logging.getLogger(__name__)

_WIKI_SCHEMA = """
CREATE TABLE IF NOT EXISTS internal_wiki (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    source_files TEXT,
    tags TEXT,
    metadata TEXT,
    confidence REAL DEFAULT 0.5,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_wiki_category ON internal_wiki(category);
CREATE INDEX IF NOT EXISTS idx_wiki_tags ON internal_wiki(tags);
"""

_VALID_CATEGORIES = {
    "architecture", "module", "pattern", "antipattern", "api", "guide",
}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_WIKI_SCHEMA)
    return conn


def _wiki_id(title: str, category: str) -> str:
    return f"wiki_{hashlib.sha256(f'{category}:{title}'.encode()).hexdigest()[:16]}"


def _now() -> str:
    return datetime.now().isoformat()


def _upsert_entry(conn, entry_id, title, content, category,
                  source_files="", tags=None, metadata=None,
                  confidence=0.5, force=False):
    existing = conn.execute(
        "SELECT id FROM internal_wiki WHERE id = ?", (entry_id,)
    ).fetchone()
    tag_str = json.dumps(tags or [])
    meta_str = json.dumps(metadata or {})
    if existing and not force:
        return "skipped"
    if existing:
        conn.execute(
            "UPDATE internal_wiki SET title=?, content=?, category=?, "
            "source_files=?, tags=?, metadata=?, confidence=?, updated_at=? "
            "WHERE id=?",
            (title, content, category, source_files, tag_str,
             meta_str, confidence, _now(), entry_id),
        )
        return "updated"
    conn.execute(
        "INSERT INTO internal_wiki (id, title, content, category, "
        "source_files, tags, metadata, confidence, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (entry_id, title, content, category, source_files, tag_str,
         meta_str, confidence, _now(), _now()),
    )
    return "created"


# ── Scanners ─────────────────────────────────────────────────────────────────


def _scan_python_modules(root: Path, max_depth: int = 4) -> list[dict[str, Any]]:
    """Scan Python modules and extract docstrings + structure."""
    results: list[dict[str, Any]] = []
    if not root.exists():
        logger.warning("Wiki module scanner root does not exist: %s", root)
        return results
    exclude = {".git", ".venv", "__pycache__", "node_modules",
               ".hypothesis", "tests", "target", "build", "dist"}
    for py_file in root.rglob("*.py"):
        if set(py_file.parts) & exclude:
            continue
        rel = py_file.relative_to(root)
        if len(rel.parts) > max_depth:
            continue
        try:
            content = py_file.read_text(errors="ignore")
            if not content.strip():
                continue
            docstring = ""
            m = re.match(r'^("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', content)
            if m:
                docstring = m.group(0).strip("\"'").strip()[:500]
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            functions = re.findall(r'^(?:async\s+)?def\s+(\w+)', content, re.MULTILINE)
            results.append({
                "path": str(rel),
                "docstring": docstring,
                "classes": classes[:20],
                "functions": functions[:30],
                "line_count": content.count("\n") + 1,
            })
        except Exception as e:
            logger.debug("Scan failed %s: %s", py_file, e)
    return results


def _scan_tool_registry() -> dict[str, Any]:
    """Extract tool registry summary."""
    try:
        from whitemagic.tools.registry import get_tool_registry
        reg = get_tool_registry()
        tools = reg.get_callable_tools()
        return {
            "total_tools": len(tools),
            "tool_names": [t.name for t in tools[:50]],
        }
    except Exception as e:
        logger.debug("Tool registry scan failed: %s", e)
        return {"total_tools": 0, "tool_names": []}


def _scan_prat_ganas() -> list[dict[str, Any]]:
    """Extract PRAT Gana structure."""
    try:
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        ganas = sorted(set(TOOL_TO_GANA.values()))
        result = []
        for g in ganas:
            tools = [k for k, v in TOOL_TO_GANA.items() if v == g]
            result.append({
                "gana": g,
                "tool_count": len(tools),
                "tools": sorted(tools)[:10],
            })
        return result
    except Exception as e:
        logger.debug("PRAT scan failed: %s", e)
        return []


def _scan_patterns() -> dict[str, Any]:
    """Extract patterns and antipatterns from all pattern engines."""
    try:
        from whitemagic.core.intelligence.synthesis.unified_patterns import (
            get_pattern_api,
        )
        api = get_pattern_api()
        all_patterns = api.search(min_confidence=0.0)
        solutions = [p for p in all_patterns if p.pattern_type.value == "solution"]
        anti = [p for p in all_patterns if p.pattern_type.value == "anti_pattern"]
        return {
            "total": len(all_patterns),
            "solutions": len(solutions),
            "anti_patterns": len(anti),
            "top_solutions": [
                {"title": p.title, "confidence": p.confidence, "engine": p.source_engine}
                for p in solutions[:10]
            ],
            "top_antipatterns": [
                {"title": p.title, "confidence": p.confidence, "engine": p.source_engine}
                for p in anti[:10]
            ],
        }
    except Exception as e:
        logger.debug("Pattern scan failed: %s", e)
        return {"total": 0, "solutions": 0, "anti_patterns": 0,
                "top_solutions": [], "top_antipatterns": []}


# ── Formatters ───────────────────────────────────────────────────────────────


def _format_module_entry(mod: dict[str, Any]) -> str:
    lines = [f"# Module: {mod['path']}"]
    if mod["docstring"]:
        lines.append(f"\n{mod['docstring']}")
    lines.append(f"\n**Lines**: {mod['line_count']}")
    if mod["classes"]:
        lines.append(f"**Classes**: {', '.join(mod['classes'])}")
    if mod["functions"]:
        lines.append(f"**Functions**: {', '.join(mod['functions'][:15])}")
    return "\n".join(lines)


def _format_tools_entry(info: dict[str, Any]) -> str:
    lines = [f"# Tool Registry ({info['total_tools']} tools)"]
    if info["tool_names"]:
        lines.append("\n## Tools")
        for name in info["tool_names"][:30]:
            lines.append(f"- `{name}`")
    return "\n".join(lines)


def _format_gana_entry(g: dict[str, Any]) -> str:
    lines = [f"# Gana: {g['gana']}"]
    lines.append(f"**Tools**: {g['tool_count']}")
    if g["tools"]:
        lines.append("\n## Mapped Tools")
        for t in g["tools"]:
            lines.append(f"- `{t}`")
    return "\n".join(lines)


def _format_pattern_entry(p: dict[str, Any], ptype: str) -> str:
    lines = [f"# {ptype.title()}: {p['title']}"]
    lines.append(f"**Confidence**: {p['confidence']}")
    lines.append(f"**Engine**: {p['engine']}")
    return "\n".join(lines)


# ── Handlers ─────────────────────────────────────────────────────────────────


def handle_wiki_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate wiki entries from codebase analysis.

    Args:
        scope: 'all' (default), 'modules', 'tools', 'patterns', 'ganas'
        root: Root directory to scan (defaults to PROJECT_ROOT)
        force: If True, overwrite existing entries
    """
    from whitemagic.config import PROJECT_ROOT

    scope = kwargs.get("scope", "all")
    root = Path(kwargs.get("root", str(PROJECT_ROOT)))
    force = kwargs.get("force", False)

    generated = 0
    updated = 0
    skipped = 0

    conn = _get_db()
    try:
        if scope in ("all", "modules"):
            modules = _scan_python_modules(root / "core" / "whitemagic")
            for mod in modules:
                title = mod["path"].replace("/", ".").replace(".py", "")
                if not title or title == "__init__":
                    continue
                content = _format_module_entry(mod)
                entry_id = _wiki_id(title, "module")
                result = _upsert_entry(
                    conn, entry_id, title, content, "module",
                    source_files=json.dumps([mod["path"]]),
                    tags=["module", "code"],
                    confidence=0.7, force=force,
                )
                if result == "created":
                    generated += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1

        if scope in ("all", "tools"):
            tool_info = _scan_tool_registry()
            content = _format_tools_entry(tool_info)
            entry_id = _wiki_id("tool_registry", "api")
            result = _upsert_entry(
                conn, entry_id, "Tool Registry", content, "api",
                source_files=json.dumps(["core/whitemagic/tools/registry.py"]),
                tags=["tools", "registry", "api"],
                confidence=0.9, force=force,
            )
            if result == "created":
                generated += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1

        if scope in ("all", "ganas"):
            ganas = _scan_prat_ganas()
            for g in ganas:
                content = _format_gana_entry(g)
                entry_id = _wiki_id(g["gana"], "architecture")
                result = _upsert_entry(
                    conn, entry_id, g["gana"], content, "architecture",
                    source_files=json.dumps(["core/whitemagic/tools/prat_mappings.py"]),
                    tags=["gana", "prat", "architecture"],
                    confidence=0.9, force=force,
                )
                if result == "created":
                    generated += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1

        if scope in ("all", "patterns"):
            patterns = _scan_patterns()
            for p in patterns.get("top_solutions", []):
                title = p["title"]
                content = _format_pattern_entry(p, "solution")
                entry_id = _wiki_id(title, "pattern")
                result = _upsert_entry(
                    conn, entry_id, title, content, "pattern",
                    tags=["pattern", "solution", p["engine"]],
                    confidence=p["confidence"], force=force,
                )
                if result == "created":
                    generated += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1
            for p in patterns.get("top_antipatterns", []):
                title = p["title"]
                content = _format_pattern_entry(p, "antipattern")
                entry_id = _wiki_id(title, "antipattern")
                result = _upsert_entry(
                    conn, entry_id, title, content, "antipattern",
                    tags=["antipattern", p["engine"]],
                    confidence=p["confidence"], force=force,
                )
                if result == "created":
                    generated += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1

        conn.commit()
        return {
            "status": "success",
            "scope": scope,
            "generated": generated,
            "updated": updated,
            "skipped": skipped,
            "total_entries": conn.execute(
                "SELECT COUNT(*) FROM internal_wiki"
            ).fetchone()[0],
        }
    except Exception as e:
        logger.error("Wiki generate failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def _escape_like(value: str) -> str:
    """Escape SQLite LIKE wildcards in a user-supplied string."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def handle_wiki_query(**kwargs: Any) -> dict[str, Any]:
    """Query the internal wiki.

    Args:
        query: Text search query (optional)
        category: Filter by category (optional)
        tags: Filter by tags (optional, comma-separated)
        limit: Max results (default 20)
    """
    query = kwargs.get("query", "")
    category = kwargs.get("category")
    tags = kwargs.get("tags")
    limit = min(kwargs.get("limit", 20), 100)

    conn = _get_db()
    try:
        sql = "SELECT * FROM internal_wiki WHERE 1=1"
        params: list[Any] = []
        if query:
            sql += " AND (title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')"
            escaped = _escape_like(query)
            params.extend([f"%{escaped}%", f"%{escaped}%"])
        if category:
            sql += " AND category = ?"
            params.append(category)
        if tags:
            for tag in tags.split(","):
                tag = tag.strip()
                if tag:
                    # Tags are stored as JSON arrays; search for the tag
                    # as a JSON string element (e.g. "tag" or "tag", ...).
                    # We escape the literal then wrap it in double quotes.
                    escaped = _escape_like(tag)
                    sql += " AND tags LIKE ? ESCAPE '\\'"
                    params.append(f'%"{escaped}"%')
        sql += " ORDER BY confidence DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "title": row["title"],
                "category": row["category"],
                "content": row["content"][:500],
                "tags": json.loads(row["tags"] or "[]"),
                "confidence": row["confidence"],
                "updated_at": row["updated_at"],
            })
        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "query": query,
            "category": category,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def handle_wiki_update(**kwargs: Any) -> dict[str, Any]:
    """Update a specific wiki entry.

    Args:
        id: Entry ID to update
        title: Title to update (used with category to derive id)
        content: New content
        category: New category (default 'guide')
        tags: New tags (comma-separated)
    """
    entry_id = kwargs.get("id")
    title = kwargs.get("title")
    if not entry_id and title:
        category = kwargs.get("category", "guide")
        entry_id = _wiki_id(title, category)

    if not entry_id:
        return {"status": "error", "error_code": "missing_params",
                "message": "id or title required"}

    content = kwargs.get("content")
    if not content:
        return {"status": "error", "error_code": "missing_content",
                "message": "content required"}

    category = kwargs.get("category", "guide")
    if category not in _VALID_CATEGORIES:
        return {"status": "error", "error_code": "invalid_category",
                "message": f"Valid: {sorted(_VALID_CATEGORIES)}"}

    tags = kwargs.get("tags", "")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    conn = _get_db()
    try:
        result = _upsert_entry(
            conn, entry_id, title or entry_id, content, category,
            tags=tag_list, confidence=0.8, force=True,
        )
        conn.commit()
        return {"status": "success", "id": entry_id, "action": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def handle_wiki_scan(**kwargs: Any) -> dict[str, Any]:
    """Scan for documentation drift — detect stale wiki entries.

    Compares wiki entry source_files against actual codebase.
    Reports entries whose source files have been modified after
    the wiki entry's updated_at timestamp.

    Args:
        root: Root directory (defaults to PROJECT_ROOT)
    """
    from whitemagic.config import PROJECT_ROOT

    root = Path(kwargs.get("root", str(PROJECT_ROOT)))
    conn = _get_db()
    try:
        total_entries = conn.execute(
            "SELECT COUNT(*) FROM internal_wiki"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT id, title, source_files, updated_at FROM internal_wiki "
            "WHERE source_files IS NOT NULL AND source_files != '[]'"
        ).fetchall()

        stale: list[dict[str, Any]] = []
        fresh = 0
        checked = 0

        for row in rows:
            source_files = json.loads(row["source_files"] or "[]")
            if not source_files:
                continue
            checked += 1
            entry_updated = row["updated_at"]
            is_stale = False
            modified_files: list[str] = []
            for sf in source_files:
                file_path = root / sf
                if not file_path.exists():
                    is_stale = True
                    modified_files.append(f"{sf} (deleted)")
                    continue
                try:
                    mtime = datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                    if mtime > entry_updated:
                        is_stale = True
                        modified_files.append(sf)
                except Exception:
                    pass
            if is_stale:
                stale.append({
                    "id": row["id"],
                    "title": row["title"],
                    "modified_files": modified_files,
                    "last_updated": entry_updated,
                })
            else:
                fresh += 1

        return {
            "status": "success",
            "total_entries": total_entries,
            "checked_entries": checked,
            "fresh": fresh,
            "stale": len(stale),
            "stale_entries": stale,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def handle_wiki_stats(**kwargs: Any) -> dict[str, Any]:
    """Get wiki statistics."""
    conn = _get_db()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM internal_wiki"
        ).fetchone()[0]
        by_category: dict[str, int] = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) as cnt FROM internal_wiki GROUP BY category"
        ).fetchall():
            by_category[row["category"]] = row["cnt"]
        avg_conf = conn.execute(
            "SELECT AVG(confidence) FROM internal_wiki"
        ).fetchone()[0]
        return {
            "status": "success",
            "total_entries": total,
            "by_category": by_category,
            "avg_confidence": round(avg_conf or 0, 4),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()
