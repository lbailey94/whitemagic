# explain_this

**Category**: introspection | **Safety**: read
**Gana**: `gana_ghost`

## Description

Pre-execution impact preview. Before running a tool, call explain_this to see: Dharma evaluation, resource estimate, dependency chain, risk assessment, karma forecast, maturity gate, and circuit breaker state. Returns a verdict: SAFE_TO_PROCEED, PROCEED_WITH_CAUTION, or BLOCKED.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "target_tool": {
      "type": "string",
      "description": "Name of the tool to preview",
      "default": "health_report"
    },
    "tool_args": {
      "type": "object",
      "description": "Arguments that would be passed to the tool",
      "default": {}
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
    "explain_this",
    {"target_tool": "Name of the tool to preview", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
