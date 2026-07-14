# pipeline

**Category**: system | **Safety**: write
**Gana**: `gana_stomach`

## Description

Unified multi-step tool pipeline management. Actions: create (build & optionally execute a pipeline with $prev/$step[N] refs), status (check pipeline execution), list (browse pipelines).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "create",
        "status",
        "list"
      ],
      "description": "Action to perform",
      "default": "list"
    },
    "name": {
      "type": "string",
      "description": "Pipeline name (for create)"
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "tool": {
            "type": "string"
          },
          "args": {
            "type": "object"
          },
          "continue_on_error": {
            "type": "boolean",
            "default": false
          }
        },
        "required": [
          "tool"
        ]
      },
      "description": "Ordered tool calls (for create)",
      "default": []
    },
    "execute": {
      "type": "boolean",
      "default": true,
      "description": "Execute immediately (for create)"
    },
    "pipeline_id": {
      "type": "string",
      "description": "Pipeline ID (for status)"
    },
    "filter_status": {
      "type": "string",
      "enum": [
        "created",
        "pending",
        "running",
        "completed",
        "failed"
      ],
      "description": "Filter by status (for list)"
    },
    "limit": {
      "type": "integer",
      "default": 20
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
    "pipeline",
    {"action": "Action to perform", "name": "Pipeline name (for create)", "steps": [], "execute": true, "pipeline_id": "Pipeline ID (for status)", "filter_status": "Filter by status (for list)", "limit": 20, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
