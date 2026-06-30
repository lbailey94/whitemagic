"""Tools Copy Integration — Ensemble, Handoff, Routing, Drives, Self-Model, Worker.
================================================================================
Tool definitions for modules integrated from Tools(copy) and CyberBrain projects.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="ensemble",
        description=(
            "Unified multi-LLM ensemble voting. "
            "Actions: query (send prompt to multiple models, synthesize consensus), "
            "status (get past query result by ID), history (list past queries)."
        ),
        category=ToolCategory.AGENT,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["query", "status", "history"],
                    "description": "Action to perform.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question/task for all models (for query).",
                },
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ollama model names (for query, auto-detect if omitted).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Per-model timeout seconds (for query).",
                    "default": 120,
                },
                "ensemble_id": {
                    "type": "string",
                    "description": "Ensemble query ID (for status).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (for history).",
                    "default": 20,
                },
            },
            "required": ["action"],
        },
    ),
    ToolDefinition(
        name="session.handoff",
        description=(
            "Unified cross-device session handoff. "
            "Actions: transfer (send session to another device), accept (receive handoff), list (browse handoffs)."
        ),
        category=ToolCategory.SESSION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["transfer", "accept", "list"],
                    "description": "Action to perform.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session to hand off (for transfer).",
                },
                "target_device": {
                    "type": "string",
                    "description": "Target hostname or 'any' (for transfer).",
                    "default": "any",
                },
                "message": {
                    "type": "string",
                    "description": "Message for receiver (for transfer).",
                },
                "handoff_id": {
                    "type": "string",
                    "description": "Handoff package ID (for accept).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (for list).",
                    "default": 20,
                },
                "filter_status": {
                    "type": "string",
                    "description": "Filter by status (for list).",
                },
            },
            "required": ["action"],
        },
    ),
    ToolDefinition(
        name="task.route_smart",
        description="Determine the optimal host for a task based on current system load across local and remote machines.",
        category=ToolCategory.AGENT,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Type of task (compilation, ai_inference, etc.).",
                    "default": "general",
                },
                "prefer_local": {
                    "type": "boolean",
                    "description": "Prefer local unless overloaded.",
                    "default": True,
                },
            },
        },
    ),
    ToolDefinition(
        name="drive.snapshot",
        description="Get current intrinsic motivation state — curiosity, satisfaction, caution, energy, social drives with composite score and trend.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "include_bias": {
                    "type": "boolean",
                    "description": "Include motivation bias vector for tool selection.",
                    "default": False,
                },
            },
        },
    ),
    ToolDefinition(
        name="drive.event",
        description="Feed an event into the Emotion & Drive Core to update drive levels (e.g. tool_success, novelty_detected, dharma_violation).",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Event type (tool_success, tool_error, novelty_detected, dharma_violation, etc.).",
                },
                "data": {
                    "type": "object",
                    "description": "Optional event data. Include 'score' (0-1) to scale the effect.",
                },
            },
            "required": ["event_type"],
        },
    ),
    ToolDefinition(
        name="selfmodel.forecast",
        description="Forecast system metric trends using linear regression. Predicts threshold crossings for energy, karma_debt, error_rate, etc.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Specific metric to forecast (omit for all).",
                },
                "steps_ahead": {
                    "type": "integer",
                    "description": "How many steps to forecast.",
                    "default": 10,
                },
            },
        },
    ),
    ToolDefinition(
        name="selfmodel.alerts",
        description="Get only forecasts with active threshold alerts — early warnings about upcoming issues.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="worker.status",
        description="Check if any worker daemons are running and get their stats (heartbeat, tasks completed).",
        category=ToolCategory.AGENT,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
]
