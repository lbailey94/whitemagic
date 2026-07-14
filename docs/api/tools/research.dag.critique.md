# research.dag.critique

**Category**: synthesis | **Safety**: write
**Gana**: `gana_three_stars`

## Description

Submit a peer critique of an experiment (score 1-10)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID"
    },
    "score": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "description": "Critique score (1-10, 8+ = breakthrough)"
    },
    "critic_agent_id": {
      "type": "string",
      "description": "Critic agent ID"
    },
    "notes": {
      "type": "string",
      "description": "Critique notes"
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
    "score"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "research.dag.critique",
    {"experiment_id": "Experiment ID", "score": 10, "critic_agent_id": "Critic agent ID", "notes": "Critique notes", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
