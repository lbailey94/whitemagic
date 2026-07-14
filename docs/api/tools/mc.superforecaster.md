# mc.superforecaster

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Run the full superforecaster pipeline: LHS → PCE → Sobol → Bayesian optimization → rare event. Unified entry point for comprehensive possibility space exploration.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "param_ranges": {
      "type": "array",
      "description": "List of [min, max] pairs"
    },
    "fitness_expr": {
      "type": "string",
      "description": "Fitness expression"
    },
    "n_initial_samples": {
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
    "mc.superforecaster",
    {"param_ranges": [], "fitness_expr": "Fitness expression", "n_initial_samples": 100, "n_bo_iterations": 20, "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
