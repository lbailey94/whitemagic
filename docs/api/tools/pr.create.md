# pr.create

**Category**: security | **Safety**: write
**Gana**: `gana_wall`

## Description

Create a GitHub PR with security fix

## Input Schema

```json
{
  "repo_dir": {
    "type": "string"
  },
  "branch_name": {
    "type": "string"
  },
  "title": {
    "type": "string"
  },
  "body": {
    "type": "string"
  },
  "labels": {
    "type": "array"
  },
  "bounty_ref": {
    "type": "string"
  },
  "properties": {
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
  }
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "pr.create",
    {"request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
