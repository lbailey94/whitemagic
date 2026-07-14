# workspace.propose

**Category**: synthesis | **Safety**: write
**Gana**: `gana_three_stars`

## Description

Submit a proposal to the global workspace for broadcast. High-salience proposals win the competition.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "source": {
      "type": "string",
      "description": "Source module name"
    },
    "content": {
      "type": "object",
      "description": "Proposal content payload"
    },
    "salience": {
      "type": "number",
      "description": "Salience score 0-1 (default 0.5)",
      "default": 0.5
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
    "source",
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "workspace.propose",
    {"source": "Source module name", "salience": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
