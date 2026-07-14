# galaxy.export

**Category**: system | **Safety**: read
**Gana**: `gana_void`

## Description

Export memories from a galaxy as Arrow IPC bytes for cross-instance sharing. Uses zero-copy columnar format (32x faster than JSON). Filters by galaxy and optionally by memory type.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "galaxy": {
      "type": "string",
      "description": "Galaxy to export (default: universal)"
    },
    "memory_type": {
      "type": "string",
      "description": "Filter by memory type (optional)"
    },
    "limit": {
      "type": "integer",
      "description": "Max memories to export (default: 10000)"
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
    "galaxy.export",
    {"galaxy": "Galaxy to export (default: universal)", "memory_type": "Filter by memory type (optional)", "limit": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
