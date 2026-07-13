"""Session Tools — create, checkpoint, resume, bootstrap, scratchpad."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="create_session",
        description="Create new work session with automatic state management",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Session name",
                    "default": "Default Session",
                },
                "goals": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "auto_checkpoint": {"type": "boolean", "default": True},
                "context_tier": {"type": "integer", "enum": [0, 1, 2], "default": 1},
            },
        },
    ),
    ToolDefinition(
        name="checkpoint_session",
        description="Create a checkpoint in the current session",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "checkpoint_name": {"type": "string", "description": "Checkpoint name"},
            },
        },
    ),
    ToolDefinition(
        name="resume_session",
        description="Resume a previous session with context restoration",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to resume"},
                "load_tier": {"type": "integer", "enum": [0, 1, 2], "default": 1},
            },
            "required": ["session_id"],
        },
    ),
    ToolDefinition(
        name="session_bootstrap",
        description="Initialize session context for a new AI session",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="Horn",
        garden="courage",
        quadrant="eastern",
        element="wood",
    ),
    ToolDefinition(
        name="scratchpad",
        description=(
            "Unified scratchpad management for active work. "
            "Actions: create (new scratchpad), update (modify section), finalize (convert to permanent memory)."
        ),
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "finalize"],
                    "description": "Action to perform",
                    "default": "create",
                },
                "name": {
                    "type": "string",
                    "description": "Scratchpad name (for create)",
                },
                "session_id": {
                    "type": "string",
                    "description": "Associated session ID (for create)",
                },
                "scratchpad_id": {
                    "type": "string",
                    "description": "Scratchpad ID (for update/finalize)",
                },
                "section": {
                    "type": "string",
                    "enum": [
                        "current_focus",
                        "decisions",
                        "questions",
                        "next_steps",
                        "ideas",
                    ],
                    "description": "Section to update (for update)",
                },
                "content": {"type": "string", "description": "Content (for update)"},
                "memory_type": {
                    "type": "string",
                    "enum": ["short_term", "long_term"],
                    "default": "long_term",
                    "description": "Target memory type (for finalize)",
                },
                "auto_analyze": {
                    "type": "boolean",
                    "default": True,
                    "description": "Multi-spectral analysis (for finalize)",
                },
            },
        },
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Session Memory — Chronological conversation recording & recall
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="session.record",
        description="Record a conversation turn (user message or AI response) as a persistent session memory with sequence number for chronological recall.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "role": {"type": "string", "enum": ["user", "ai"], "description": "Who said this turn"},
                "content": {"type": "string", "description": "The message content"},
                "turn_type": {"type": "string", "enum": ["message", "decision", "breakthrough", "question", "answer", "code_change", "error", "summary", "context"], "default": "message"},
                "importance": {"type": "number", "default": 0.5, "description": "0.0-1.0 importance score"},
                "emotional_valence": {"type": "number", "default": 0.0, "description": "-1.0 to 1.0 emotional tone"},
                "session_id": {"type": "string", "description": "Session ID (auto-generated if omitted)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Additional tags"},
            },
            "required": ["role", "content"],
        },
    ),
    ToolDefinition(
        name="session.recall",
        description="Recall recent session turns in chronological order (oldest to newest).",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 10, "description": "Number of recent turns to recall"},
                "session_id": {"type": "string", "description": "Session ID (uses active session if omitted)"},
                "full": {"type": "boolean", "default": False, "description": "Include full content vs compact preview"},
            },
        },
    ),
    ToolDefinition(
        name="session.replay",
        description="Replay session turns — full chronological, selective (important turns only), or progressive (token-budgeted compact previews).",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["full", "selective", "progressive"], "default": "full"},
                "n": {"type": "integer", "default": 50, "description": "Max turns (full mode)"},
                "turn_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by turn type (selective mode)"},
                "min_importance": {"type": "number", "default": 0.7, "description": "Min importance (selective mode)"},
                "token_budget": {"type": "integer", "default": 2000, "description": "Token budget (progressive mode)"},
                "session_id": {"type": "string", "description": "Session ID"},
            },
        },
    ),
    ToolDefinition(
        name="session.search",
        description="Semantic search within session memories using FTS5.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10},
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="session.memory_stats",
        description="Get session memory statistics (turn count, role distribution, turn types, elapsed time).",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
        },
    ),
    ToolDefinition(
        name="session.backfill",
        description="Backfill sequence numbers for existing session memories that lack them. Sorts by created_at and assigns incrementing sequence numbers.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
        },
    ),
    ToolDefinition(
        name="session.continuity",
        description="Get cross-session continuity — recent turns from the previous session for context injection on reconnect.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 10, "description": "Number of turns from previous session"},
                "session_id": {"type": "string", "description": "Current session ID (to exclude from search)"},
            },
        },
    ),
    ToolDefinition(
        name="session.consolidate",
        description="Sleep consolidation — promote important session turns (decisions, breakthroughs, errors) to the codex galaxy as long-term semantic knowledge.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to consolidate"},
                "min_importance": {"type": "number", "default": 0.7, "description": "Minimum importance threshold for promotion"},
                "dry_run": {"type": "boolean", "default": False, "description": "If true, only report what would be promoted"},
            },
        },
    ),
    ToolDefinition(
        name="state.current",
        description="Get the current work state snapshot — current task, active tasks, next steps, recent file modifications, and context. This is the primary tool to call on connecting to understand what to work on next.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="state.update",
        description="Update the current work state. Set current task, add/complete tasks, add next steps, record file modifications, decisions, or errors. Replaces reliance on static .md docs for short-term context.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "current_task": {"type": "string", "description": "Set what's being worked on now"},
                "add_active_task": {"type": "string", "description": "Add an active task"},
                "complete_task": {"type": "string", "description": "Mark a task as completed"},
                "add_next_step": {"type": "string", "description": "Add a next step"},
                "clear_next_steps": {"type": "boolean", "description": "Clear all next steps"},
                "context_key": {"type": "string", "description": "Context key to set"},
                "context_value": {"type": "string", "description": "Context value to set"},
                "record_file": {"type": "string", "description": "Record a file modification (path)"},
                "file_description": {"type": "string", "description": "Description of file change"},
                "record_decision": {"type": "string", "description": "Record a decision"},
                "decision_rationale": {"type": "string", "description": "Rationale for the decision"},
                "record_error": {"type": "string", "description": "Record an error"},
                "error_context": {"type": "string", "description": "Context for the error"},
                "last_session_summary": {"type": "string", "description": "Summary of last session"},
                "last_session_id": {"type": "string", "description": "ID of last session"},
            },
        },
    ),
    ToolDefinition(
        name="state.context",
        description="Get or set context values in the current work state. Without arguments, returns all context. With key+value, sets a context entry. With just key, gets a specific entry.",
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Context key"},
                "value": {"type": "string", "description": "Context value (omit to get, include to set)"},
            },
        },
    ),
]
