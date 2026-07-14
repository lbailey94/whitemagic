# quantum.fubini_study

**Category**: metrics | **Safety**: read
**Gana**: `gana_tail`

## Description

Compute the Fubini-Study metric tensor for quantum state parameter space. Used in natural gradient optimization.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "state": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Quantum state vector"
    },
    "jacobian": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number"
        }
      },
      "description": "Jacobian matrix of the parameterization"
    },
    "n_params": {
      "type": "integer",
      "description": "Number of parameters"
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
    "state"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "quantum.fubini_study",
    {"state": [], "jacobian": [], "n_params": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
