# model.register

**Category**: security | **Safety**: write
**Gana**: `gana_roof`

## Description

Register a model manifest for OpenSSF Model Signing verification

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model_name": {
      "type": "string",
      "description": "Name of the model"
    },
    "sha256": {
      "type": "string",
      "description": "SHA-256 hash of the model file",
      "default": ""
    },
    "trust": {
      "type": "string",
      "description": "Trust level (verified, unverified, blocked)",
      "default": "unverified"
    },
    "signer": {
      "type": "string",
      "description": "Identity of the signer",
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
    "model_name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "model.register",
    {"model_name": "Name of the model", "sha256": "SHA-256 hash of the model file", "trust": "Trust level (verified, unverified, blocked)", "signer": "Identity of the signer", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
