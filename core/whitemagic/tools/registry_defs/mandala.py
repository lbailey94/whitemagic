"""MandalaOS Phase B — Mandala compartment tool definitions."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="mandala.create",
        description=(
            "Create a new mandala compartment from a template or explicit config "
            "(MandalaOS Phase B). Templates: research (network read, creative Dharma), "
            "sandbox (no network, default Dharma), production (read-only, secure Dharma), "
            "secure (no network/fs, minimal resources). Each mandala gets its own "
            "dharma_profile, capabilities, and resource limits."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique mandala compartment name.",
                },
                "template": {
                    "type": "string",
                    "enum": ["research", "sandbox", "production", "secure"],
                    "description": "Template to use (optional — overrides capabilities/limits/dharma_profile).",
                },
                "tier": {
                    "type": "string",
                    "enum": ["auto", "thread", "namespace", "container", "wasm"],
                    "description": "Isolation tier override.",
                },
                "dharma_profile": {
                    "type": "string",
                    "description": "Dharma rules profile (default, creative, secure).",
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Capability grants (e.g., network_read, fs_write:/tmp).",
                },
                "limits": {
                    "type": "object",
                    "description": "Resource limits (timeout_s, max_memory_mb, max_cpu_s, max_disk_mb).",
                },
                "ephemeral": {
                    "type": "boolean",
                    "default": True,
                    "description": "Auto-destroy on completion.",
                },
            },
        },
    ),
    ToolDefinition(
        name="mandala.status",
        description=(
            "List active mandala compartments and available templates (MandalaOS Phase B). "
            "Shows shelter status, isolation tiers, dharma profiles, and template descriptions."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="mandala.destroy",
        description=(
            "Destroy a mandala compartment and clean up resources (MandalaOS Phase B). "
            "Removes the shelter, its work directory, and all associated state."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.DELETE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the mandala compartment to destroy.",
                },
            },
        },
    ),
    ToolDefinition(
        name="mandala.templates",
        description=(
            "List available mandala templates with their capabilities, limits, and "
            "Dharma profiles (MandalaOS Phase B). Templates: research, sandbox, "
            "production, secure."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
]
