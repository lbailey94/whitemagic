"""Violet Security Tools — engagement tokens, model signing, MCP integrity, security monitor."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    # ── Engagement Tokens ──
    ToolDefinition(
        name="engagement.issue",
        description="Issue a scope-of-engagement token for offensive security operations",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target patterns (e.g., ['10.0.0.*', '*.internal.corp'])",
                    "default": [],
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tool name patterns (fnmatch, e.g., ['nmap_*', 'fuzz_*'])",
                    "default": [],
                },
                "issuer": {
                    "type": "string",
                    "description": "Identity of the person/system authorizing the engagement",
                },
                "duration_minutes": {
                    "type": "number",
                    "description": "Token validity in minutes (0.5 = 30 seconds for high-risk ops)",
                    "default": 60,
                },
                "max_uses": {
                    "type": "integer",
                    "description": "Maximum uses (0 = unlimited, 1 = single-use)",
                    "default": 0,
                },
                "roe_hash": {
                    "type": "string",
                    "description": "SHA-256 hash of active Dharma profile rules at issue time",
                    "default": "",
                },
            },
            "required": ["issuer"],
        },
    ),
    ToolDefinition(
        name="engagement.validate",
        description="Validate an engagement token for a tool/target combination",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Token ID to validate",
                },
                "tool": {
                    "type": "string",
                    "description": "Tool name to check authorization for",
                    "default": "",
                },
                "target": {
                    "type": "string",
                    "description": "Target to check scope against",
                    "default": "",
                },
            },
            "required": ["token_id"],
        },
    ),
    ToolDefinition(
        name="engagement.revoke",
        description="Revoke an engagement token before its expiry",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Token ID to revoke",
                },
            },
            "required": ["token_id"],
        },
    ),
    ToolDefinition(
        name="engagement.list",
        description="List all engagement tokens",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "include_expired": {
                    "type": "boolean",
                    "description": "Include expired tokens in the list",
                    "default": False,
                },
            },
        },
    ),
    ToolDefinition(
        name="engagement.status",
        description="Return engagement token subsystem status",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    # ── MCP Integrity ──
    ToolDefinition(
        name="mcp_integrity.snapshot",
        description="Take a snapshot of MCP tool definitions for tamper detection",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="mcp_integrity.verify",
        description="Verify MCP tool definitions against a stored snapshot",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="mcp_integrity.status",
        description="Return MCP integrity subsystem status",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    # ── Model Signing ──
    ToolDefinition(
        name="model.register",
        description="Register a model manifest for OpenSSF Model Signing verification",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Name of the model",
                },
                "sha256": {
                    "type": "string",
                    "description": "SHA-256 hash of the model file",
                    "default": "",
                },
                "trust": {
                    "type": "string",
                    "description": "Trust level (verified, unverified, blocked)",
                    "default": "unverified",
                },
                "signer": {
                    "type": "string",
                    "description": "Identity of the signer",
                    "default": "",
                },
            },
            "required": ["model_name"],
        },
    ),
    ToolDefinition(
        name="model.verify",
        description="Verify a model against its registered manifest",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Name of the model to verify",
                },
                "current_sha256": {
                    "type": "string",
                    "description": "Current SHA-256 hash to verify against manifest",
                    "default": "",
                },
            },
            "required": ["model_name"],
        },
    ),
    ToolDefinition(
        name="model.list",
        description="List all registered model manifests",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="model.hash",
        description="Compute SHA-256 hash of a model file",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "model_path": {
                    "type": "string",
                    "description": "Path to the model file",
                },
            },
            "required": ["model_path"],
        },
    ),
    ToolDefinition(
        name="model.signing_status",
        description="Return model signing subsystem status",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    # ── Security Monitor ──
    ToolDefinition(
        name="security.alerts",
        description="Return recent security alerts from the anomaly monitor",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of alerts to return",
                    "default": 50,
                },
            },
        },
    ),
    ToolDefinition(
        name="security.monitor_status",
        description="Return security monitor subsystem status",
        category=ToolCategory.SECURITY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
]
