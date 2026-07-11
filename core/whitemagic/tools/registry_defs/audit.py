"""Audit & Observability — Merkle chain, anomaly detection, OpenTelemetry."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="karma.verify_chain",
        description="Verify the Merkle hash chain integrity of the Karma Ledger — detects tampering",
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="karmic.effects",
        description=(
            "Query declared effect signatures for tools (MandalaOS Phase A). "
            "Pass a tool name to get its declared effects, or omit to get all. "
            "Shows effect_type (pure/local/network/destructive/observation), target, and declared status."
        ),
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Tool name to query. Omit for all tools.",
                },
            },
        },
    ),
    ToolDefinition(
        name="karmic.debt",
        description=(
            "Per-tool karma debt reports (MandalaOS Phase A). "
            "Pass a tool name for per-tool stats, or omit for system-wide debt summary. "
            "Shows debt, calls, mismatches, and effect mismatch counts."
        ),
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Tool name to filter debt. Omit for summary.",
                },
                "shelter_id": {
                    "type": "string",
                    "description": "Shelter ID to filter debt (Phase B).",
                },
            },
        },
    ),
    ToolDefinition(
        name="karmic.verify",
        description=(
            "Verify Merkle chain + effect signature integrity of the Karma Ledger (MandalaOS Phase A). "
            "Combines hash chain verification with effect mismatch audit."
        ),
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="effect.trace",
        description=(
            "Get effect trace for a tool call (MandalaOS Phase C). "
            "Returns declared effects, karma debt, mismatch counts, and optionally "
            "Koka karmic comparison results when use_koka=true."
        ),
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Tool name to trace.",
                },
                "use_koka": {
                    "type": "boolean",
                    "default": False,
                    "description": "If True, attempt Koka karmic comparison.",
                },
            },
        },
    ),
    ToolDefinition(
        name="effect.visualize",
        description=(
            "Export effect flow visualization (MandalaOS Phase C). "
            "Generates DOT (Graphviz), Mermaid, or JSON visualization of effect "
            "relationships. Pass a tool name for per-tool view, or omit for system-wide summary."
        ),
        category=ToolCategory.DHARMA,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Tool name to visualize. Omit for system-wide view.",
                },
                "format": {
                    "type": "string",
                    "enum": ["dot", "mermaid", "json"],
                    "default": "dot",
                    "description": "Output format.",
                },
            },
        },
    ),
    ToolDefinition(
        name="anomaly",
        description=(
            "Unified anomaly detection on Harmony Vector dimensions. "
            "Actions: check (active anomalies), history (recent alerts), status (detector stats)."
        ),
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check", "history", "status"],
                    "description": "Action to perform",
                    "default": "check",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max alerts to return (for history)",
                },
            },
        },
    ),
    ToolDefinition(
        name="otel",
        description=(
            "Unified OpenTelemetry observability. "
            "Actions: spans (recent trace records), metrics (aggregated per-tool stats), status (exporter state)."
        ),
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["spans", "metrics", "status"],
                    "description": "Action to perform",
                    "default": "metrics",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max spans to return (for spans)",
                },
            },
        },
    ),
]
