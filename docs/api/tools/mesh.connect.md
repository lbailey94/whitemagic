# mesh.connect

**Category**: broker | **Safety**: write
**Gana**: `gana_wings`

## Description

Connect or reconnect the local mesh client. Optionally provide an address and node_id to override the current mesh endpoint before reporting connection status.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "address": {
      "type": "string",
      "description": "Optional mesh address, e.g. localhost:50051"
    },
    "node_id": {
      "type": "string",
      "description": "Optional node identifier"
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
    "mesh.connect",
    {"address": "Optional mesh address, e.g. localhost:50051", "node_id": "Optional node identifier", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
