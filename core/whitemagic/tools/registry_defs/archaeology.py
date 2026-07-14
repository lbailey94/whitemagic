"""Archaeology Tools — unified file tracking, dig, analysis, timeline."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

_TOOLS_ARCHAELOGY: list[ToolDefinition] = [
    ToolDefinition(
        name="archaeology",
        description=(
            "Unified file archaeology — track reads/writes, find unread/changed files, "
            "search history, generate reports. Actions: mark_read, mark_written, have_read, "
            "find_unread, find_changed, recent_reads, stats, scan, report, search, "
            "process_wisdom, daily_digest."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "mark_read",
                        "mark_written",
                        "have_read",
                        "find_unread",
                        "find_changed",
                        "recent_reads",
                        "stats",
                        "scan",
                        "report",
                        "search",
                        "process_wisdom",
                        "daily_digest",
                    ],
                    "description": "Action to perform",
                    "default": "stats",
                },
                "path": {
                    "type": "string",
                    "description": "File path (for mark_read/written/have_read)",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to scan (for find_*/scan)",
                },
                "context": {"type": "string", "description": "Read/write context"},
                "note": {"type": "string", "description": "Optional note"},
                "insight": {
                    "type": "string",
                    "description": "Key insight (for mark_read)",
                },
                "query": {"type": "string", "description": "Search query (for search)"},
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns (for find_unread/scan)",
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Result limit",
                },
            },
        },
    ),
]

_TOOLS_WINDSURF_RIPS: list[ToolDefinition] = [
    ToolDefinition(
        name="windsurf.export_all",
        description=(
            "Bulk export all Windsurf/Cascade conversations via the language server gRPC API. "
            "Falls back to .pb file parsing if the API is unavailable. "
            "Outputs markdown transcripts + JSON metadata to a dated directory."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Custom output directory (default: ~/Desktop/WindsurfRips/api_export_YYYY-MM-DD)",
                },
                "full_steps": {
                    "type": "boolean",
                    "default": False,
                    "description": "Also fetch complete step-by-step data (bypasses 200K truncation)",
                },
            },
        },
    ),
    ToolDefinition(
        name="windsurf.ingest",
        description=(
            "Parse exported Windsurf transcripts and ingest into the sessions galaxy. "
            "Classifies turns by type (decision, breakthrough, error, code_change, etc.) "
            "and scores importance. Deduplicates — skips sessions already ingested."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "export_dir": {
                    "type": "string",
                    "description": "Directory containing .md transcript files (default: most recent export)",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Parse and report stats without ingesting",
                },
                "limit": {
                    "type": "integer",
                    "description": "Only ingest first N sessions (for testing)",
                },
            },
        },
    ),
    ToolDefinition(
        name="windsurf.sync",
        description=(
            "Full incremental pipeline: export all sessions → compare with previous exports "
            "→ ingest only new/changed sessions → report. This is the recommended way to "
            "keep the sessions galaxy up to date."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.WRITE,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="windsurf.mine",
        description=(
            "Cross-session pattern mining — extracts decisions, breakthroughs, errors, "
            "topics, and user directives from an export directory. Returns structured "
            "results suitable for codex galaxy ingestion."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "export_dir": {
                    "type": "string",
                    "description": "Directory containing exported .md transcript files",
                },
            },
            "required": ["export_dir"],
        },
    ),
    ToolDefinition(
        name="windsurf.categorize",
        description=(
            "Auto-categorize sessions by topic (whitemagic, ai_research, system_maintenance, "
            "hardware, games, devin_windsurf, other) and suggest galaxy routing for each."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "export_dir": {
                    "type": "string",
                    "description": "Directory containing exported .json metadata files",
                },
            },
            "required": ["export_dir"],
        },
    ),
    ToolDefinition(
        name="windsurf.full_steps",
        description=(
            "Fetch complete step-by-step data for a single session via the language server API. "
            "Bypasses the 200K character transcript truncation. Requires Windsurf/Devin Desktop running."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "cascade_id": {
                    "type": "string",
                    "description": "The cascade trajectory ID to fetch steps for",
                },
            },
            "required": ["cascade_id"],
        },
    ),
    ToolDefinition(
        name="windsurf.compare",
        description=(
            "Compare exports across dates to find new, changed, and missing sessions. "
            "Uses cascade ID, transcript length, step count, and content hash for comparison."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "new_dir": {
                    "type": "string",
                    "description": "New export directory to compare",
                },
                "old_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Old export directories to compare against",
                },
            },
            "required": ["new_dir"],
        },
    ),
    ToolDefinition(
        name="windsurf.semantic_search",
        description=(
            "Semantic search across all conversations using HNSW embeddings and FTS5. "
            "Searches the sessions galaxy first, falls back to keyword search on .pb files."
        ),
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum results",
                },
            },
            "required": ["query"],
        },
    ),
]

TOOLS = _TOOLS_ARCHAELOGY + _TOOLS_WINDSURF_RIPS
