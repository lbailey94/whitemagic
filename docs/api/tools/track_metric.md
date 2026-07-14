# track_metric

**Category**: metrics | **Safety**: write
**Gana**: `gana_mound`

## Description

Record a quantitative metric

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "description": "Metric category",
      "default": "general"
    },
    "metric": {
      "type": "string",
      "description": "Metric name",
      "default": "ping"
    },
    "value": {
      "type": "number",
      "description": "Metric value",
      "default": 1.0
    },
    "context": {
      "type": "string",
      "description": "Optional context"
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
    "track_metric",
    {"category": "Metric category", "metric": "Metric name", "value": 1.0, "context": "Optional context", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
