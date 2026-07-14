# galaxy.stats

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Get statistics for a specific cognitive galaxy — memory count, average importance, average galactic distance, zone distribution.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "galaxy": {
      "type": "string",
      "description": "Galaxy name (e.g. 'universal', 'self_learning', 'oracle')",
      "default": "universal"
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
    "galaxy.stats",
    {"galaxy": "Galaxy name (e.g. 'universal', 'self_learning', 'o", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
