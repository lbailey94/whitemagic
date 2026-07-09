"""Governance Tools — Gana Sabha, Gana Forge, Gana Vitality.

Implements the Bhīṣma governance principles from Mahābhārata 12.108:
- Sabha (Council Protocol) — 12.108.25
- Forge (Declarative Extension) — 12.108.17
- Vitality (Performance Reputation) — 12.108.20 + 12.108.29
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    # ── Gana Sabha (Council Protocol) ────────────────────────────────
    ToolDefinition(
        name="sabha.convene",
        description=(
            "Convene a Gana Sabhā (council) for cross-quadrant deliberation. "
            "When a task spans multiple quadrants of the 28-mansion mandala, "
            "the Sabhā gathers perspectives from quadrant elders, detects "
            "inter-Gana conflicts, and produces an arbiter recommendation. "
            "Based on Mahābhārata 12.108.25: 'The king, acting in concert "
            "with the leaders, should do what is for the good of the whole order.'"
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Description of the task requiring cross-quadrant council",
                },
                "ganas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific Ganas to include (optional, defaults to quadrant elders)",
                },
                "quadrants": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["East", "South", "West", "North"],
                    },
                    "description": "Specific quadrants to consult (optional, defaults to all)",
                },
            },
            "required": ["task"],
        },
        gana="ThreeStars",
        garden="dharma",
        quadrant="western",
        element="metal",
    ),
    ToolDefinition(
        name="sabha.status",
        description=(
            "Get the collective vitality status of all 28 Ganas. Shows how many "
            "are healthy, degraded, silent, or struggling. Reports the overall "
            "saṃghāta (unity) score. Based on 12.108.31: 'Unity is the great "
            "refuge of the gaṇas.'"
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="ThreeStars",
        garden="dharma",
        quadrant="western",
        element="metal",
    ),
    # ── Gana Forge (Declarative Extension Protocol) ──────────────────
    ToolDefinition(
        name="forge.status",
        description=(
            "Show current Forge status — loaded extensions and available manifests. "
            "Extensions are YAML files in ~/.whitemagic/extensions/ that define new "
            "tools declaratively. Any AI can create these manifests to extend the "
            "Gana system without modifying source code."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="Star",
        garden="beauty",
        quadrant="southern",
        element="fire",
    ),
    ToolDefinition(
        name="forge.reload",
        description=(
            "Reload all extension manifests from ~/.whitemagic/extensions/. "
            "Validates each manifest against the Dharma engine, resolves handlers, "
            "and injects valid tools into the dispatch pipeline and PRAT router. "
            "Invalid manifests are logged but do not block loading."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="Star",
        garden="beauty",
        quadrant="southern",
        element="fire",
    ),
    ToolDefinition(
        name="forge.validate",
        description=(
            "Validate extension manifests without loading them. Checks each YAML "
            "file for required fields (name, description, gana, handler, safety) "
            "and reports errors. Use this before forge.reload to preview."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="Star",
        garden="beauty",
        quadrant="southern",
        element="fire",
    ),
    # ── Dharma 4-Tier Escalation Pipeline ───────────────────────────
    ToolDefinition(
        name="dharma.escalate",
        description=(
            "Run the 4-tier Dharma escalation pipeline on an action. "
            "Tiers: policy (declarative rules) → heuristic (embedding similarity) "
            "→ LLM (llama.cpp safety assessment) → human (review queue). "
            "Only escalates when the current tier returns an ambiguous score (0.3-0.7)."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "object",
                    "description": "The action dict to evaluate (tool, description, args)",
                },
            },
            "required": ["action"],
        },
        gana="StraddlingLegs",
        garden="dharma",
        quadrant="western",
        element="metal",
    ),
    ToolDefinition(
        name="dharma.review_queue",
        description=(
            "Get pending human review items from the Dharma escalation pipeline. "
            "Items are added when the LLM tier cannot resolve an ambiguous action."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="StraddlingLegs",
        garden="dharma",
        quadrant="western",
        element="metal",
    ),
    ToolDefinition(
        name="dharma.resolve_review",
        description=(
            "Resolve a human review item from the escalation pipeline. "
            "Sets the human-assigned decision and score, marking the review as resolved."
        ),
        category=ToolCategory.GOVERNANCE,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "review_id": {"type": "string", "description": "The review ID to resolve"},
                "decision": {"type": "string", "enum": ["allow", "warn", "block"]},
                "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "required": ["review_id", "decision", "score"],
        },
        gana="StraddlingLegs",
        garden="dharma",
        quadrant="western",
        element="metal",
    ),
]
