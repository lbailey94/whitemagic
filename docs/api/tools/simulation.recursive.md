# simulation.recursive

**Category**: synthesis | **Safety**: write
**Gana**: `gana_ghost`

## Description

Run a recursive yin/yang simulation cycle: alternates introspective (yin-within-yang) and external (yang-within-yin) simulation, feeding results forward across cycles.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "n_cycles": {
      "type": "integer",
      "default": 3,
      "description": "Number of yin/yang cycles"
    },
    "introspective_space": {
      "type": "string",
      "default": "guna_balance",
      "description": "Internal space to optimize"
    },
    "external_model": {
      "type": "string",
      "default": "sde",
      "description": "External model type (sde, rare_event, superforecaster)"
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
    "simulation.recursive",
    {"n_cycles": 3, "introspective_space": "Internal space to optimize", "external_model": "External model type (sde, rare_event, superforecas", "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
