# engagement.issue

**Category**: security | **Safety**: write
**Gana**: `gana_wall`

## Description

Issue a scope-of-engagement token for offensive security operations

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "scope": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Target patterns (e.g., ['10.0.0.*', '*.internal.corp'])",
      "default": []
    },
    "tools": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Tool name patterns (fnmatch, e.g., ['nmap_*', 'fuzz_*'])",
      "default": []
    },
    "issuer": {
      "type": "string",
      "description": "Identity of the person/system authorizing the engagement"
    },
    "duration_minutes": {
      "type": "number",
      "description": "Token validity in minutes (0.5 = 30 seconds for high-risk ops)",
      "default": 60
    },
    "max_uses": {
      "type": "integer",
      "description": "Maximum uses (0 = unlimited, 1 = single-use)",
      "default": 0
    },
    "roe_hash": {
      "type": "string",
      "description": "SHA-256 hash of active Dharma profile rules at issue time",
      "default": ""
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
    "issuer"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "engagement.issue",
    {"scope": [], "tools": [], "issuer": "Identity of the person/system authorizing the enga", "duration_minutes": 60, "max_uses": 0, "roe_hash": "SHA-256 hash of active Dharma profile rules at iss", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
