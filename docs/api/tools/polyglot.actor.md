# polyglot.actor

**Category**: agent | **Safety**: read
**Gana**: `gana_tail`

## Description

Execute actor-based hypothesis tracking through the Elixir actor backend. Manages Bayesian belief updating across concurrent hypothesis actors. Supports start_actor, send_outcome, broadcast_outcome, transfer_belief, get_posteriors, get_stats.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": [
        "start_actor",
        "send_outcome",
        "broadcast_outcome",
        "transfer_belief",
        "get_posteriors",
        "get_stats"
      ],
      "description": "Actor operation to execute"
    },
    "hypothesis_id": {
      "type": "string"
    },
    "prior": {
      "type": "number",
      "default": 0.5
    },
    "success": {
      "type": "boolean"
    },
    "gain": {
      "type": "number"
    },
    "from_id": {
      "type": "string"
    },
    "to_id": {
      "type": "string"
    },
    "weight": {
      "type": "number",
      "default": 0.5
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
    "operation"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "polyglot.actor",
    {"operation": "Actor operation to execute", "hypothesis_id": "example", "prior": 0.5, "success": false, "gain": 1.0, "from_id": "example", "to_id": "example", "weight": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
