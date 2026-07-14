# code.affected_by

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Find all symbols that would be affected if the given symbol changes. Performs reverse traversal of calls, imports, and references up to a configurable depth. Useful for impact analysis before refactoring.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Name of the symbol to analyze."
    },
    "max_depth": {
      "type": "integer",
      "description": "Maximum traversal depth (default 3).",
      "default": 3
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
    "symbol"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "code.affected_by",
    {"symbol": "Name of the symbol to analyze.", "max_depth": 3, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
