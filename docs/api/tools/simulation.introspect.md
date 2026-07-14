# simulation.introspect

**Category**: synthesis | **Safety**: write
**Gana**: `gana_ghost`

## Description

Yin-within-yang: run introspective simulation to optimize internal system parameters (guna balance, coherence, emergence thresholds, health setpoints) via the superforecaster pipeline.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "space": {
      "type": "string",
      "default": "guna_balance",
      "description": "guna_balance, coherence_optimization, emergence_thresholds, health_setpoints"
    },
    "n_trials": {
      "type": "integer",
      "default": 100
    },
    "n_bo_iterations": {
      "type": "integer",
      "default": 20
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
    "simulation.introspect",
    {"space": "guna_balance, coherence_optimization, emergence_th", "n_trials": 100, "n_bo_iterations": 20, "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
