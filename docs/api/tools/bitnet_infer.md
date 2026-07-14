# bitnet_infer

**Category**: inference | **Safety**: read
**Gana**: `gana_turtle_beak`

## Description

Run local inference via BitNet 1-bit LLM (requires WHITEMAGIC_ENABLE_BITNET=1)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "description": "Input prompt for inference"
    },
    "n_predict": {
      "type": "integer",
      "description": "Max tokens to generate",
      "default": 128
    },
    "temp": {
      "type": "number",
      "description": "Sampling temperature",
      "default": 0.8
    },
    "mode": {
      "type": "string",
      "enum": [
        "auto",
        "redis",
        "direct"
      ],
      "description": "Inference mode: redis (Gan Ying bus), direct (subprocess), or auto",
      "default": "auto"
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
    "prompt"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "bitnet_infer",
    {"prompt": "Input prompt for inference", "n_predict": 128, "temp": 0.8, "mode": "Inference mode: redis (Gan Ying bus), direct (subp", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
