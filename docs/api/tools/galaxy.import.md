# galaxy.import

**Category**: system | **Safety**: write
**Gana**: `gana_void`

## Description

Import memories from Arrow IPC bytes into the local memory system. Memories are stored via the normal ingestion pipeline with dedup, surprise gate, and holographic indexing. Galaxy metadata is preserved.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "ipc_bytes_b64": {
      "type": "string",
      "description": "Base64-encoded Arrow IPC bytes"
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
    "ipc_bytes_b64"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "galaxy.import",
    {"ipc_bytes_b64": "Base64-encoded Arrow IPC bytes", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
