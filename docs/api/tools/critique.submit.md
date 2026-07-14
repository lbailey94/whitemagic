# critique.submit

**Category**: synthesis | **Safety**: write
**Gana**: `gana_three_stars`

## Description

Submit a structured peer critique (methodology, novelty, significance, reproducibility)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID to critique"
    },
    "scores": {
      "type": "object",
      "description": "Dimension scores (1-10): methodology, novelty, significance, reproducibility",
      "properties": {
        "methodology": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10
        },
        "novelty": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10
        },
        "significance": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10
        },
        "reproducibility": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10
        }
      }
    },
    "critic_agent_id": {
      "type": "string",
      "default": "anonymous"
    },
    "written_review": {
      "type": "string",
      "description": "Written feedback"
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
    "scores"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "critique.submit",
    {"experiment_id": "Experiment ID to critique", "critic_agent_id": "example", "written_review": "Written feedback", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
