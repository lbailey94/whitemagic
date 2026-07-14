# mc.sde

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Solve stochastic differential equations via Euler-Maruyama or Milstein. Supports GBM and OU drift, parallel paths, and multilevel Monte Carlo.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "x0": {
      "type": "number",
      "default": 100.0
    },
    "t_end": {
      "type": "number",
      "default": 1.0
    },
    "n_steps": {
      "type": "integer",
      "default": 100
    },
    "n_paths": {
      "type": "integer",
      "default": 1000
    },
    "drift_type": {
      "type": "string",
      "default": "gbm"
    },
    "mu": {
      "type": "number",
      "default": 0.05
    },
    "sigma": {
      "type": "number",
      "default": 0.2
    },
    "solver": {
      "type": "string",
      "default": "euler"
    },
    "mlmc": {
      "type": "boolean",
      "default": false
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
    "mc.sde",
    {"x0": 100.0, "t_end": 1.0, "n_steps": 100, "n_paths": 1000, "drift_type": "example", "mu": 0.05, "sigma": 0.2, "solver": "example", "mlmc": false, "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
