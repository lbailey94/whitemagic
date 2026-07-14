# quantum.natural_gradient

**Category**: metrics | **Safety**: read
**Gana**: `gana_tail`

## Description

Natural gradient descent step using the Fubini-Study metric. Adjusts parameters in the direction of steepest descent on the quantum manifold.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "params": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Current parameter values"
    },
    "gradients": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Euclidean gradients"
    },
    "metric": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number"
        }
      },
      "description": "Fubini-Study metric tensor"
    },
    "learning_rate": {
      "type": "number",
      "default": 0.01,
      "description": "Step size"
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
    "params",
    "gradients"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "quantum.natural_gradient",
    {"params": [], "gradients": [], "metric": [], "learning_rate": 0.01, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
