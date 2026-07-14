# dharma.escalate

**Category**: governance | **Safety**: read
**Gana**: `gana_straddling_legs`

## Description

Run the 4-tier Dharma escalation pipeline on an action. Tiers: policy (declarative rules) → heuristic (embedding similarity) → LLM (llama.cpp safety assessment) → human (review queue). Only escalates when the current tier returns an ambiguous score (0.3-0.7).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "object",
      "description": "The action dict to evaluate (tool, description, args)"
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
    "dharma.escalate",
    {"request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
