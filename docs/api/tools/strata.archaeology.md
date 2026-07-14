# strata.archaeology

**Category**: archaeology | **Safety**: read
**Gana**: `gana_chariot`

## Description

Git history archaeology — excavate layers, find fossils, track extinctions, analyze composition, measure temper.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to the codebase"
    },
    "subcommand": {
      "type": "string",
      "enum": [
        "excavate",
        "fossil",
        "extinction",
        "composition",
        "temper"
      ],
      "description": "Archaeology subcommand to run"
    },
    "top": {
      "type": "integer",
      "default": 10,
      "description": "Top N results"
    },
    "layer": {
      "type": "string",
      "description": "Git layer/commit for excavate"
    },
    "file_path": {
      "type": "string",
      "description": "File filter for temper"
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
    "path",
    "subcommand"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "strata.archaeology",
    {"path": "Path to the codebase", "subcommand": "Archaeology subcommand to run", "top": 10, "layer": "Git layer/commit for excavate", "file_path": "File filter for temper", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
