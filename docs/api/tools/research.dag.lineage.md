# research.dag.lineage

**Category**: synthesis | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Get lineage tree for an experiment (ancestors + descendants)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID"
    },
    "max_depth": {
      "type": "integer",
      "default": 10,
      "description": "Maximum traversal depth"
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
    "experiment_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "research.dag.lineage",
    {"experiment_id": "Experiment ID", "max_depth": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
