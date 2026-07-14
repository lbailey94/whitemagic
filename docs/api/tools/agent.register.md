# agent.register

**Category**: agent | **Safety**: write
**Gana**: `gana_girl`

## Description

Register a new agent or update an existing one with name, capabilities, and metadata

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Human-readable agent name"
    },
    "agent_id": {
      "type": "string",
      "description": "Explicit ID (auto-generated if omitted)"
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of capabilities (e.g. code_review, testing, inference)"
    },
    "metadata": {
      "type": "object",
      "description": "Arbitrary metadata (model, version, etc.)"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
    },
    "dry_run": {
      "type": "boolean",
      "description": "If true, do not perform writes; return an execution preview when possible.",
      "default": false
    },
    "now": {
      "type": "string",
      "description": "Optional ISO timestamp override for deterministic evaluation/replay (best-effort)."
    }
  },
  "required": [
    "name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "agent.register",
    {"name": "Human-readable agent name", "agent_id": "Explicit ID (auto-generated if omitted)", "capabilities": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
