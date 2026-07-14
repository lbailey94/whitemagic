# research.dag.result

**Category**: synthesis | **Safety**: write
**Gana**: `gana_winnowing_basket`

## Description

Record an experiment result with fitness score

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID"
    },
    "fitness_score": {
      "type": "number",
      "description": "Fitness score (0.0-1.0)"
    },
    "outcome": {
      "type": "object",
      "description": "Outcome details"
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
    "experiment_id",
    "fitness_score"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "research.dag.result",
    {"experiment_id": "Experiment ID", "fitness_score": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
