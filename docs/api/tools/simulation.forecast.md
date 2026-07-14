# simulation.forecast

**Category**: synthesis | **Safety**: read
**Gana**: `gana_chariot`

## Description

Yang-within-yin: run external research simulation to model and forecast external systems. Supports SDE solving, rare event estimation, and superforecaster pipeline.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model_type": {
      "type": "string",
      "default": "sde",
      "description": "sde, rare_event, or superforecaster"
    },
    "research_query": {
      "type": "string",
      "description": "Optional research question framing the simulation"
    },
    "seed": {
      "type": "integer",
      "default": 42
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
    "simulation.forecast",
    {"model_type": "sde, rare_event, or superforecaster", "research_query": "Optional research question framing the simulation", "seed": 42, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
