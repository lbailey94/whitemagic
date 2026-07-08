"""Codebase Self-Model Handlers v2 — MCP tool implementations.

Tools for scanning, recalling, and navigating the codebase via galactic memory.
All tools operate on the codex galaxy, using holographic + FTS5 + semantic recall
instead of raw grep.

v2 upgrades:
  - Chunked ingestion (no truncation data loss)
  - Semantic embedding search (EmbeddingEngine)
  - Rust BM25 search (rust_search module)
  - Progress callbacks for long scans
  - Batch processing to prevent laptop hangs
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_codebase_scan(**kwargs: Any) -> dict[str, Any]:
    """Scan the codebase and ingest into the codex galaxy.

    Walks the project tree, chunks file contents, ingests chunks + directory
    topology as memories with holographic coordinates. Supports incremental mode
    that skips unchanged files (content-hash dedup). Optionally triggers
    semantic embedding indexing after ingestion.
    """
    from whitemagic.core.memory.codebase_scanner import get_scanner

    project_root = kwargs.get("project_root")
    incremental = kwargs.get("incremental", True)
    max_files = kwargs.get("max_files", 10000)
    embed = kwargs.get("embed", True)

    try:
        scanner = get_scanner(project_root)
        result = scanner.scan(
            incremental=incremental,
            max_files=max_files,
            embed=embed,
        )
        return {"status": "success", **result.to_dict()}
    except Exception as e:
        logger.error("Codebase scan failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}


def handle_codebase_recall(**kwargs: Any) -> dict[str, Any]:
    """Semantic recall from the codex galaxy.

    Searches file/chunk content memories using semantic embedding search,
    Rust BM25, or FTS5 fallback. Returns matching files with path, content
    preview, metadata, and recall type.
    """
    from whitemagic.core.memory.codebase_scanner import get_scanner

    query = kwargs.get("query", "")
    limit = kwargs.get("limit", 20)
    tags = kwargs.get("tags", [])
    min_importance = kwargs.get("min_importance", 0.0)
    semantic = kwargs.get("semantic", True)

    if not query:
        return {"status": "error", "error": "query is required"}

    try:
        scanner = get_scanner()
        results = scanner.recall(
            query=query,
            limit=limit,
            tags=tags,
            min_importance=min_importance,
            semantic=semantic,
        )
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error("Codebase recall failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}


def handle_codebase_structure(**kwargs: Any) -> dict[str, Any]:
    """Recall directory topology from the codex galaxy.

    Returns the files and subdirectories for a given path,
    retrieved from stored directory memories (no filesystem access needed).
    """
    from whitemagic.core.memory.codebase_scanner import get_scanner

    dir_path = kwargs.get("path") or kwargs.get("dir_path")

    try:
        scanner = get_scanner()
        result = scanner.structure(dir_path)
        return {"status": "success", **result}
    except Exception as e:
        logger.error("Codebase structure failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}


def handle_codebase_status(**kwargs: Any) -> dict[str, Any]:
    """Get codebase scan status — last scan time, file counts, extension breakdown."""
    from whitemagic.core.memory.codebase_scanner import get_scanner

    try:
        scanner = get_scanner()
        result = scanner.status()
        return {"status": "success", **result}
    except Exception as e:
        logger.error("Codebase status failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}


def handle_codebase_find(**kwargs: Any) -> dict[str, Any]:
    """Find files by extension, tag, or path pattern in the codex galaxy.

    Searches memory metadata for files matching the given criteria.
    Faster than grep for "what files exist with extension X" queries.
    """
    import sqlite3

    from whitemagic.core.memory.unified import get_unified_memory

    extension = kwargs.get("extension")
    path_pattern = kwargs.get("path_pattern") or kwargs.get("path")
    tag = kwargs.get("tag")
    limit = kwargs.get("limit", 50)

    try:
        um = get_unified_memory()
        backend = um._galaxy_backend._get_galaxy_backend("codex")
        with backend.pool.connection() as conn:
            conn.row_factory = sqlite3.Row

            # Tags are in a separate table — use subqueries
            conditions = [
                "id IN (SELECT memory_id FROM tags WHERE tag = 'codex')",
                "id IN (SELECT memory_id FROM tags WHERE tag = 'file')",
            ]
            params: list[Any] = []

            if extension:
                ext = extension.lstrip(".")
                conditions.append("id IN (SELECT memory_id FROM tags WHERE tag LIKE ?)")
                params.append(f"ext:{ext}")

            if path_pattern:
                conditions.append("id IN (SELECT memory_id FROM tags WHERE tag LIKE ?)")
                params.append(f"%path:{path_pattern}%")

            if tag:
                conditions.append("id IN (SELECT memory_id FROM tags WHERE tag = ?)")
                params.append(tag)

            where = " AND ".join(conditions)
            query = (
                f"SELECT id, title, metadata, importance "
                f"FROM memories WHERE {where} "
                f"ORDER BY importance DESC LIMIT ?"
            )
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                title = row["title"] or ""
                rel_path = title[6:] if title.startswith("FILE: ") else title
                tag_rows = conn.execute(
                    "SELECT tag FROM tags WHERE memory_id = ?", (row["id"],)
                ).fetchall()
                file_tags = [r["tag"] for r in tag_rows]
                results.append({
                    "id": row["id"][:12] + "...",
                    "path": rel_path,
                    "importance": round(row["importance"] or 0, 2),
                    "tags": file_tags,
                })

            return {
                "status": "success",
                "count": len(results),
                "files": results,
            }
    except Exception as e:
        logger.error("Codebase find failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
