# ensemble

**Category**: agent | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Unified multi-LLM ensemble voting. Actions: query (send prompt to multiple models, synthesize consensus), status (get past query result by ID), history (list past queries).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "query",
        "status",
        "history"
      ],
      "description": "Action to perform."
    },
    "prompt": {
      "type": "string",
      "description": "Question/task for all models (for query)."
    },
    "models": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "llama.cpp model names (for query, auto-detect if omitted)."
    },
    "timeout": {
      "type": "integer",
      "description": "Per-model timeout seconds (for query).",
      "default": 120
    },
    "ensemble_id": {
      "type": "string",
      "description": "Ensemble query ID (for status)."
    },
    "limit": {
      "type": "integer",
      "description": "Max results (for history).",
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
  },
  "required": [
    "action"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "ensemble",
    {"action": "Action to perform.", "prompt": "Question/task for all models (for query).", "models": [], "timeout": 120, "ensemble_id": "Ensemble query ID (for status).", "limit": 20, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
