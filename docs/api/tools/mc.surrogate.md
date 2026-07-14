# mc.surrogate

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Fit and evaluate a Gaussian Process surrogate model for Bayesian optimization or response surface modeling.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "x_train": {
      "type": "array",
      "description": "Training inputs (list of lists)"
    },
    "y_train": {
      "type": "array",
      "description": "Training outputs (list of floats)"
    },
    "x_predict": {
      "type": "array",
      "description": "Optional points to predict at"
    },
    "length_scale": {
      "type": "number",
      "default": 1.0
    },
    "sigma_f": {
      "type": "number",
      "default": 1.0
    },
    "sigma_n": {
      "type": "number",
      "default": 0.01
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
    "mc.surrogate",
    {"x_train": [], "y_train": [], "x_predict": [], "length_scale": 1.0, "sigma_f": 1.0, "sigma_n": 0.01, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
