# possibility.explore

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Run Monte Carlo possibility space exploration on system parameters (guna balance, coherence, emergence thresholds, health setpoints). Returns best parameters and sensitivity analysis.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "space": {
      "type": "string",
      "default": "guna_balance",
      "description": "Possibility space: guna_balance, coherence_optimization, emergence_thresholds, health_setpoints, or all"
    },
    "n_trials": {
      "type": "integer",
      "default": 100,
      "description": "Number of Monte Carlo trials"
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
    "possibility.explore",
    {"space": "Possibility space: guna_balance, coherence_optimiz", "n_trials": 100, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
