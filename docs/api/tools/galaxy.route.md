# galaxy.route

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Determine which cognitive galaxy a memory belongs to based on the source subsystem. Returns the galaxy name for routing.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "subsystem": {
      "type": "string",
      "description": "Name of the cognitive subsystem (e.g. 'dream_cycle', 'emergence_engine')"
    },
    "metadata": {
      "type": "object",
      "description": "Optional metadata with explicit galaxy override"
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
    "subsystem"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "galaxy.route",
    {"subsystem": "Name of the cognitive subsystem (e.g. 'dream_cycle", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
