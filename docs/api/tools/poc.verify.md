# poc.verify

**Category**: security | **Safety**: read
**Gana**: `gana_chariot`

## Description

Full PoC pipeline: governance → render → compile → test → verify

## Input Schema

```json
{
  "template_name": {
    "type": "string"
  },
  "variables": {
    "type": "object"
  },
  "project_dir": {
    "type": "string"
  },
  "tier": {
    "type": "string",
    "default": "huben"
  },
  "target": {
    "type": "string"
  },
  "properties": {
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
    "poc.verify",
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
