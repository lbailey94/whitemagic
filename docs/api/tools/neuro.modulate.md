# neuro.modulate

**Category**: memory | **Safety**: write
**Gana**: `gana_dipper`

## Description

Apply neuromodulation to a list of memories, adjusting their neuro_score based on modulator levels.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memories": {
      "type": "array",
      "items": {
        "type": "object"
      },
      "description": "List of memory dicts to modulate"
    },
    "da": {
      "type": "number",
      "description": "Dopamine level override 0-1"
    },
    "sht": {
      "type": "number",
      "description": "Serotonin level override 0-1"
    },
    "ach": {
      "type": "number",
      "description": "Acetylcholine level override 0-1"
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
    "memories"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "neuro.modulate",
    {"memories": [], "da": 1.0, "sht": 1.0, "ach": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
