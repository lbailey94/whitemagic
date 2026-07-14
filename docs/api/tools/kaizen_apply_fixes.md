# kaizen_apply_fixes

**Category**: synthesis | **Safety**: write
**Gana**: `gana_three_stars`

## Description

Apply recommended fixes from Kaizen analysis

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "fix_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "IDs of fixes to apply",
      "default": []
    },
    "dry_run": {
      "type": "boolean",
      "default": true
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
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
    "kaizen_apply_fixes",
    {"fix_ids": [], "dry_run": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
