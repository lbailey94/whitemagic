# karmic.debt

**Category**: dharma | **Safety**: read
**Gana**: `gana_hairy_head`

## Description

Per-tool karma debt reports (MandalaOS Phase A). Pass a tool name for per-tool stats, or omit for system-wide debt summary. Shows debt, calls, mismatches, and effect mismatch counts.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "description": "Tool name to filter debt. Omit for summary."
    },
    "shelter_id": {
      "type": "string",
      "description": "Shelter ID to filter debt (Phase B)."
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
    "karmic.debt",
    {"tool": "Tool name to filter debt. Omit for summary.", "shelter_id": "Shelter ID to filter debt (Phase B).", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
