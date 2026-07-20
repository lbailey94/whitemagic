"""Windsurf conversation reader tool handlers.

Includes upgraded existing tools (using SessionMiner when API is available)
and 8 new tools for export, ingest, sync, mining, categorization, and search.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

def _get_miner() -> Any:
    """Get a SessionMiner instance (cached per-call for simplicity)."""
    from whitemagic.archaeology.session_miner import SessionMiner

    return SessionMiner()


# ── Upgraded existing handlers ──────────────────────────────────────────────


def handle_windsurf_list_conversations(**kwargs: Any) -> dict[str, Any]:
    """List conversations — uses API when available, falls back to .pb files."""
    miner = _get_miner()
    if miner.api_available:
        try:
            summaries, inputs = miner._api.get_all_trajectories()
            conversations = []
            for cid, summary in summaries.items():
                conversations.append({
                    "id": cid,
                    "title": summary.get("summary", "Untitled"),
                    "step_count": summary.get("stepCount", 0),
                    "status": summary.get("status", "unknown"),
                    "modified": summary.get("lastModifiedTime", ""),
                    "method": "api",
                })
            return {"status": "success", "conversations": conversations, "method": "api"}
        except Exception:  # noqa: BLE001
            logger.debug("Ignored Exception in windsurf_conv.py:40")

    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    return {"status": "success", "conversations": reader.list_conversations(), "method": "pb"}


def handle_windsurf_read_conversation(**kwargs: Any) -> dict[str, Any]:
    """Read a conversation — uses API for transcript when available."""
    cascade_id = kwargs.get("cascade_id") or kwargs.get("id")
    path = kwargs.get("path")

    # API method: use cascade_id to get transcript
    if cascade_id:
        miner = _get_miner()
        if miner.api_available:
            try:
                transcript, num_steps = miner._api.get_transcript(cascade_id)
                from whitemagic.archaeology.session_miner import TranscriptParser
                turns = TranscriptParser.parse_transcript(transcript)
                TranscriptParser.classify_and_score(turns)
                return {
                    "status": "success",
                    "cascade_id": cascade_id,
                    "transcript": transcript,
                    "num_total_steps": num_steps,
                    "turns": [t.to_dict() for t in turns],
                    "method": "api",
                }
            except Exception:  # noqa: BLE001
                logger.debug("Ignored Exception in windsurf_conv.py:70")

    # Fallback: .pb file reading
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    if not path and not cascade_id:
        return {"status": "error", "error_code": "invalid_params", "message": "path or cascade_id is required"}
    try:
        if not path:
            # Try to find .pb file by cascade_id
            files = reader.find_conversation_files()
            for f in files:
                if cascade_id[:8] in f.stem:
                    path = str(f)
                    break
            if not path:
                return {"status": "error", "error_code": "not_found", "message": f"No conversation found for cascade_id: {cascade_id}"}
        conv = reader.read_conversation(path)
    except FileNotFoundError:
        return {"status": "error", "error_code": "not_found", "message": f"Conversation file not found: {path}"}
    return {"status": "success", **conv.to_dict(), "method": "pb"}


def handle_windsurf_export_conversation(**kwargs: Any) -> dict[str, Any]:
    """Export a single conversation to markdown or json."""
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    path = kwargs.get("path")
    if not path:
        return {"status": "error", "error_code": "invalid_params", "message": "path is required"}
    try:
        content = reader.export_conversation(path, kwargs.get("format", "markdown"))
    except FileNotFoundError:
        return {"status": "error", "error_code": "not_found", "message": f"Conversation file not found: {path}"}
    return {"status": "success", "content": content}


def handle_windsurf_search_conversations(**kwargs: Any) -> dict[str, Any]:
    """Search conversations — uses FTS5 on ingested sessions when available."""
    query = kwargs.get("query")
    if not query:
        return {"status": "error", "error": "query is required"}

    # Try FTS5 search on sessions galaxy first
    try:
        from whitemagic.core.memory.session_recorder import SessionRecorder
        results = SessionRecorder.search(query, limit=kwargs.get("limit", 20))
        if results:
            return {"status": "success", "results": results, "method": "fts5"}
    except Exception:  # noqa: BLE001
        logger.debug("Ignored Exception in windsurf_conv.py:120")

    # Fallback to in-memory keyword search
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    results = reader.search_conversations(query)
    return {"status": "success", "results": results, "method": "keyword"}


def handle_windsurf_stats(**kwargs: Any) -> dict[str, Any]:
    """Unified stats — API availability, ingestion status, galaxy memory count."""
    miner = _get_miner()
    return {"status": "success", **miner.stats()}


# ── New handlers: 8 new MCP tools ───────────────────────────────────────────


def handle_windsurf_export_all(**kwargs: Any) -> dict[str, Any]:
    """Bulk export all sessions via API or .pb fallback."""
    miner = _get_miner()
    output_dir = kwargs.get("output_dir")
    full_steps = kwargs.get("full_steps", False)
    return miner.export(output_dir=output_dir, full_steps=full_steps)


def handle_windsurf_ingest(**kwargs: Any) -> dict[str, Any]:
    """Parse + ingest sessions into sessions galaxy."""
    miner = _get_miner()
    export_dir = kwargs.get("export_dir")
    dry_run = kwargs.get("dry_run", False)
    limit = kwargs.get("limit")
    return miner.ingest(export_dir=export_dir, dry_run=dry_run, limit=limit)


def handle_windsurf_sync(**kwargs: Any) -> dict[str, Any]:
    """Incremental export + ingest of new/changed sessions only."""
    miner = _get_miner()
    return miner.sync()


def handle_windsurf_mine(**kwargs: Any) -> dict[str, Any]:
    """Cross-session pattern mining — decisions, breakthroughs, errors, topics."""
    export_dir = kwargs.get("export_dir")
    if not export_dir:
        return {"status": "error", "error": "export_dir is required"}

    from pathlib import Path
    export_dir = Path(export_dir)

    # Load sessions from export
    import json

    from whitemagic.archaeology.session_miner import TranscriptParser

    md_files = sorted(export_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name != "INDEX.md"]
    json_files = {f.stem: f for f in export_dir.glob("*.json") if f.name != "INDEX.json"}

    sessions: list[dict[str, Any]] = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        turns = TranscriptParser.parse_transcript(content)
        TranscriptParser.classify_and_score(turns)

        stem = md_file.stem
        meta: dict[str, Any] = {}
        if stem in json_files:
            meta = json.loads(json_files[stem].read_text(encoding="utf-8"))

        sessions.append({
            "session_id": meta.get("cascadeId", stem),
            "title": meta.get("title", stem),
            "turns": [t.to_dict() for t in turns],
        })

    from whitemagic.archaeology.session_miner import PatternMiner
    return {"status": "success", **PatternMiner.mine(sessions)}


def handle_windsurf_categorize(**kwargs: Any) -> dict[str, Any]:
    """Auto-categorize sessions by topic and suggest galaxy routing."""
    miner = _get_miner()
    export_dir = kwargs.get("export_dir")
    return miner.categorize(export_dir=export_dir)


def handle_windsurf_full_steps(**kwargs: Any) -> dict[str, Any]:
    """Fetch complete step data for a single session (bypasses 200K truncation)."""
    cascade_id = kwargs.get("cascade_id") or kwargs.get("id")
    if not cascade_id:
        return {"status": "error", "error": "cascade_id is required"}

    miner = _get_miner()
    if not miner.api_available:
        return {"status": "error", "error": "Language server API not available. Start Windsurf/Devin Desktop."}

    try:
        steps = miner._api.get_all_steps(cascade_id)
        return {"status": "success", "cascade_id": cascade_id, "total_steps": len(steps), "steps": steps}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)}


def handle_windsurf_compare(**kwargs: Any) -> dict[str, Any]:
    """Compare exports across dates to find new/changed sessions."""
    from pathlib import Path
    new_dir = kwargs.get("new_dir")
    old_dirs = kwargs.get("old_dirs", [])

    if not new_dir:
        return {"status": "error", "error": "new_dir is required"}

    from whitemagic.archaeology.session_miner import ExportComparator
    result = ExportComparator.compare(Path(new_dir), [Path(d) for d in old_dirs])
    return {"status": "success", **result}


def handle_windsurf_semantic_search(**kwargs: Any) -> dict[str, Any]:
    """Semantic search across all conversations using HNSW + FTS5."""
    query = kwargs.get("query")
    if not query:
        return {"status": "error", "error": "query is required"}

    limit = kwargs.get("limit", 20)

    # Try galaxy semantic search first
    try:
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory()
        results = um.search(query, galaxy="sessions", limit=limit)
        if results:
            return {"status": "success", "results": results, "method": "galaxy_semantic"}
    except Exception:  # noqa: BLE001
        logger.debug("Ignored Exception in windsurf_conv.py:253")

    # Fallback to keyword search on .pb files
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    results = reader.search_conversations(query)
    return {"status": "success", "results": results, "method": "keyword"}
