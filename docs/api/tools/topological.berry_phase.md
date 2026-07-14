# topological.berry_phase

**Category**: metrics | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Compute the Berry phase (geometric phase) accumulated over a cyclic path in parameter space. Dispatches to Haskell topological bridge first for formal verification.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "states": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number"
        }
      },
      "description": "Quantum states along the path"
    },
    "params": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Parameter values at each state"
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
    "states",
    "params"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "topological.berry_phase",
    {"states": [], "params": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
