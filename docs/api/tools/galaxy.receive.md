# galaxy.receive

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Receive and import a cross-AI galaxy package. Verifies package integrity (content hash, format version), then imports the snapshot into a target or quarantined galaxy. Supports quarantine mode for inspecting untrusted packages.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "package": {
      "type": "object",
      "description": "Galaxy package from galaxy.package"
    },
    "target_galaxy": {
      "type": "string",
      "description": "Galaxy to import into (default: package's galaxy)"
    },
    "quarantine": {
      "type": "boolean",
      "description": "Import to quarantined galaxy for inspection (default: false)"
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
    "package"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "galaxy.receive",
    {"target_galaxy": "Galaxy to import into (default: package's galaxy)", "quarantine": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
