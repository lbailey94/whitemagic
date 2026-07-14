# autoswarm.campaign

**Category**: agent | **Safety**: write
**Gana**: `gana_chariot`

## Description

Launch an evolutionary campaign (hypothesis → trial → result → share)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "campaign_name": {
      "type": "string",
      "default": "manual_campaign"
    },
    "domain": {
      "type": "string",
      "default": "cognitive"
    },
    "hypothesis_space": {
      "type": "string",
      "default": "guna_balance"
    },
    "n_trials": {
      "type": "integer",
      "default": 50
    },
    "max_iterations": {
      "type": "integer",
      "default": 10
    },
    "share_results": {
      "type": "boolean",
      "default": true
    },
    "dream_integration": {
      "type": "boolean",
      "default": true
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
    "autoswarm.campaign",
    {"campaign_name": "example", "domain": "example", "hypothesis_space": "example", "n_trials": 50, "max_iterations": 10, "share_results": true, "dream_integration": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
