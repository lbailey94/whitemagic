# pulse.verify

**Category**: security | **Safety**: read
**Gana**: `gana_hairy_head`

## Description

Verify an experiment pulse through tiered checks (Ed25519 + Merkle + karma)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "experiment_id": {
      "type": "string",
      "description": "Experiment ID to verify"
    },
    "experiment_data": {
      "type": "object",
      "description": "Data to verify against Merkle root"
    },
    "node_reputation": {
      "type": "number",
      "default": 0.5,
      "description": "Node reputation (0.0-1.0)"
    },
    "force_tier": {
      "type": "integer",
      "description": "Force verification up to tier (0-3)"
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
    "pulse.verify",
    {"experiment_id": "Experiment ID to verify", "node_reputation": 0.5, "force_tier": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
