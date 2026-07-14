# sandbox.set_limits

**Category**: governor | **Safety**: write
**Gana**: `gana_room`

## Description

Set custom resource limits for a specific tool (timeout, memory, CPU)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "target_tool": {
      "type": "string",
      "description": "Name of the tool to set limits for"
    },
    "timeout_s": {
      "type": "number",
      "default": 30
    },
    "max_memory_mb": {
      "type": "integer",
      "default": 512
    },
    "max_cpu_s": {
      "type": "number",
      "default": 10
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
    "target_tool"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "sandbox.set_limits",
    {"target_tool": "Name of the tool to set limits for", "timeout_s": 30, "max_memory_mb": 512, "max_cpu_s": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
