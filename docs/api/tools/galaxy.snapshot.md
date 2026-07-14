# galaxy.snapshot

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Create a full snapshot of a galaxy — memories, 6D coordinates, associations, and metadata. Unlike galaxy.export, this includes associations and full metadata, enabling trajectory branching for simulation. Returns a snapshot dict that can be passed to galaxy.restore.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "galaxy": {
      "type": "string",
      "description": "Galaxy to snapshot (default: universal)"
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
    "galaxy.snapshot",
    {"galaxy": "Galaxy to snapshot (default: universal)", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
