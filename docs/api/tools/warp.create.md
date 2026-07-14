# warp.create

**Category**: agent | **Safety**: write
**Gana**: `gana_dipper`

## Description

Create a custom warp preset

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Warp name"
    },
    "description": {
      "type": "string"
    },
    "tools_allowed": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "tools_denied": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "dharma_profile": {
      "type": "string"
    },
    "inference_tier": {
      "type": "string",
      "enum": [
        "edge",
        "local_small",
        "local_large",
        "cloud"
      ]
    },
    "galaxies_accessible": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "execution_mode": {
      "type": "string",
      "enum": [
        "interactive",
        "autonomous",
        "dream"
      ]
    },
    "research_domains": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "shelter_template": {
      "type": "string",
      "enum": [
        "research",
        "sandbox",
        "production",
        "secure"
      ]
    },
    "max_iterations": {
      "type": "integer"
    },
    "timeout_seconds": {
      "type": "integer"
    },
    "metadata": {
      "type": "object"
    },
    "persist": {
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
  },
  "required": [
    "name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "warp.create",
    {"name": "Warp name", "description": "example", "tools_allowed": [], "tools_denied": [], "dharma_profile": "example", "inference_tier": "example", "galaxies_accessible": [], "execution_mode": "example", "research_domains": [], "shelter_template": "example", "max_iterations": 10, "timeout_seconds": 10, "persist": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
