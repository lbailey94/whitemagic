# galaxy.restore

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Restore a galaxy from a snapshot created by galaxy.snapshot. Can restore into the original galaxy or a different target galaxy, enabling trajectory branching. Memories, coordinates, and associations are all restored.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "snapshot": {
      "type": "object",
      "description": "Snapshot dict from galaxy.snapshot"
    },
    "target_galaxy": {
      "type": "string",
      "description": "Galaxy to restore into (default: snapshot's galaxy)"
    },
    "merge": {
      "type": "boolean",
      "description": "Merge with existing memories (default: true)"
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
    "snapshot"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "galaxy.restore",
    {"target_galaxy": "Galaxy to restore into (default: snapshot's galaxy", "merge": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
