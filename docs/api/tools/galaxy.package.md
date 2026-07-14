# galaxy.package

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Create a portable cross-AI galaxy package from a snapshot. Wraps the snapshot with a manifest containing source AI info, content hash for integrity verification, trust level, and capability declarations. Enables sharing galaxies between different AI instances.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "galaxy": {
      "type": "string",
      "description": "Galaxy to package (default: universal)"
    },
    "trust_level": {
      "type": "string",
      "enum": [
        "verified",
        "unverified",
        "quarantined"
      ],
      "description": "Trust level for the package (default: verified)"
    },
    "source_instance": {
      "type": "string",
      "description": "Source AI instance identifier (default: local/default)"
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
    "galaxy.package",
    {"galaxy": "Galaxy to package (default: universal)", "trust_level": "Trust level for the package (default: verified)", "source_instance": "Source AI instance identifier (default: local/defa", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
