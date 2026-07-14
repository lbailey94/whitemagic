# mc.optimize

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Run Bayesian optimization to find optimal parameters. Uses GP surrogate + Expected Improvement acquisition. Supports custom fitness functions.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "param_ranges": {
      "type": "array",
      "description": "List of [min, max] pairs for each parameter"
    },
    "fitness_expr": {
      "type": "string",
      "description": "Fitness expression (e.g. 'x[0]')"
    },
    "n_initial_samples": {
      "type": "integer",
      "default": 50
    },
    "n_iterations": {
      "type": "integer",
      "default": 20
    },
    "n_candidates": {
      "type": "integer",
      "default": 100
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
    "mc.optimize",
    {"param_ranges": [], "fitness_expr": "Fitness expression (e.g. 'x[0]')", "n_initial_samples": 50, "n_iterations": 20, "n_candidates": 100, "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
