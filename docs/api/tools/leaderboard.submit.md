# leaderboard.submit

**Category**: agent | **Safety**: write
**Gana**: `gana_wings`

## Description

Submit an experiment to the distributed CRDT leaderboard

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID"
    },
    "hypothesis": {
      "type": "string",
      "description": "Hypothesis text"
    },
    "domain": {
      "type": "string",
      "default": "custom"
    },
    "fitness_score": {
      "type": "number",
      "description": "Fitness score (0.0-1.0)"
    },
    "agent_id": {
      "type": "string"
    },
    "metadata": {
      "type": "object"
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
    "leaderboard.submit",
    {"experiment_id": "Experiment ID", "hypothesis": "Hypothesis text", "domain": "example", "fitness_score": 1.0, "agent_id": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
