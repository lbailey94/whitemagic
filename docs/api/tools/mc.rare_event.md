# mc.rare_event

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Estimate rare event probabilities using subset simulation, multilevel splitting, or importance sampling.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "method": {
      "type": "string",
      "default": "subset",
      "description": "subset, splitting, or importance"
    },
    "dim": {
      "type": "integer",
      "default": 2
    },
    "n_samples": {
      "type": "integer",
      "default": 1000
    },
    "threshold": {
      "type": "number",
      "default": 2.0
    },
    "g_expr": {
      "type": "string",
      "default": "threshold - sum_sq"
    },
    "seed": {
      "type": "integer",
      "default": 42
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
    "mc.rare_event",
    {"method": "subset, splitting, or importance", "dim": 2, "n_samples": 1000, "threshold": 2.0, "g_expr": "example", "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
