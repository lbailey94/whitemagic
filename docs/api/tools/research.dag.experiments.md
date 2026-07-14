# research.dag.experiments

**Category**: synthesis | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Query experiments with optional domain and stage filters

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "domain": {
      "type": "string",
      "description": "Filter by domain"
    },
    "stage": {
      "type": "string",
      "description": "Filter by stage (hypothesis, trial, result, critique, breakthrough, failed)"
    },
    "limit": {
      "type": "integer",
      "default": 50
    },
    "offset": {
      "type": "integer",
      "default": 0
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
    "research.dag.experiments",
    {"domain": "Filter by domain", "stage": "Filter by stage (hypothesis, trial, result, critiq", "limit": 50, "offset": 0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
