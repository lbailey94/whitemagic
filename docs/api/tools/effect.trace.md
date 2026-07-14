# effect.trace

**Category**: dharma | **Safety**: read
**Gana**: `gana_ghost`

## Description

Get effect trace for a tool call (MandalaOS Phase C). Returns declared effects, karma debt, mismatch counts, and optionally Koka karmic comparison results when use_koka=true.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "description": "Tool name to trace."
    },
    "use_koka": {
      "type": "boolean",
      "default": false,
      "description": "If True, attempt Koka karmic comparison."
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
    "effect.trace",
    {"tool": "Tool name to trace.", "use_koka": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
