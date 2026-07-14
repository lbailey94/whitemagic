# grimoire_cast

**Category**: system | **Safety**: write
**Gana**: `gana_willow`

## Description

Cast a specific Grimoire spell by name

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "spell_name": {
      "type": "string",
      "description": "Name of the spell to cast",
      "default": "centering"
    },
    "task": {
      "type": "string",
      "default": "manual cast"
    },
    "emotional_state": {
      "type": "string",
      "default": "neutral"
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
  }
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "grimoire_cast",
    {"spell_name": "Name of the spell to cast", "task": "example", "emotional_state": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
