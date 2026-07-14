# dilo_co.init

**Category**: agent | **Safety**: write
**Gana**: `gana_ox`

## Description

Initialize DiLoCo distributed training coordinator with parameters

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "params": {
      "type": "object",
      "description": "Initial model parameters"
    },
    "h": {
      "type": "integer",
      "default": 16,
      "description": "Local steps between syncs"
    },
    "k_ratio": {
      "type": "number",
      "default": 0.01,
      "description": "SparseLoCo sparsity ratio"
    },
    "lr": {
      "type": "number",
      "default": 0.01
    },
    "lr_outer": {
      "type": "number",
      "default": 1.0
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
    "params"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "dilo_co.init",
    {"h": 16, "k_ratio": 0.01, "lr": 0.01, "lr_outer": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
