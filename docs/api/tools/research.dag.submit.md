# research.dag.submit

**Category**: synthesis | **Safety**: write
**Gana**: `gana_winnowing_basket`

## Description

Submit a hypothesis to the research DAG

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "hypothesis": {
      "type": "string",
      "description": "Hypothesis text"
    },
    "domain": {
      "type": "string",
      "enum": [
        "cognitive",
        "memory",
        "consciousness",
        "evolution",
        "synthesis",
        "governance",
        "inference",
        "custom"
      ],
      "default": "cognitive"
    },
    "parameters": {
      "type": "object",
      "description": "Experiment parameters"
    },
    "agent_id": {
      "type": "string",
      "description": "Submitting agent ID"
    },
    "inspiration_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Breakthrough experiment IDs that inspired this"
    },
    "parent_id": {
      "type": "string",
      "description": "Parent experiment ID"
    },
    "metadata": {
      "type": "object",
      "description": "Additional metadata"
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
    "hypothesis"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "research.dag.submit",
    {"hypothesis": "Hypothesis text", "domain": "example", "agent_id": "Submitting agent ID", "inspiration_ids": [], "parent_id": "Parent experiment ID", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
