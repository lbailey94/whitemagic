# strata.analyze

**Category**: archaeology | **Safety**: read
**Gana**: `gana_chariot`

## Description

Run STRATA static analysis on a codebase. 80+ checkers across 15 languages detecting structural stubs, dead code, archive drift, and more.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to the codebase to analyze"
    },
    "incremental": {
      "type": "boolean",
      "default": true,
      "description": "Only analyze changed files"
    },
    "severity": {
      "type": "string",
      "enum": [
        "error",
        "warning",
        "info"
      ],
      "description": "Minimum severity to report"
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
    "path"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "strata.analyze",
    {"path": "Path to the codebase to analyze", "incremental": true, "severity": "Minimum severity to report", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
