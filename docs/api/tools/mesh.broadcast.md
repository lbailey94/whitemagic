# mesh.broadcast

**Category**: broker | **Safety**: write
**Gana**: `gana_wings`

## Description

Broadcast a signal to all mesh peers via gRPC (if connected) or Redis pub/sub fallback. Used for cross-node coordination.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "signal_type": {
      "type": "string",
      "description": "Type of signal to broadcast",
      "default": "ping"
    },
    "payload": {
      "type": "string",
      "description": "Signal payload (JSON string or text)",
      "default": "{}"
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
    "mesh.broadcast",
    {"signal_type": "Type of signal to broadcast", "payload": "Signal payload (JSON string or text)", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
