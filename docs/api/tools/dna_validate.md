# dna_validate

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Validate a proposed fix against WhiteMagic's core DNA principles. Checks for violations of immutable principles (no self-destruction, memory integrity, reversibility, test before deploy). Returns safe/violation status and suppression recommendation.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "fix_details": {
      "type": "object",
      "description": "Dict with 'action' and 'file' keys describing the proposed fix",
      "properties": {
        "action": {
          "type": "string",
          "description": "Action being taken (e.g. 'delete file', 'update version')"
        },
        "file": {
          "type": "string",
          "description": "File path being modified"
        }
      }
    },
    "threat_type": {
      "type": "string",
      "description": "Type of threat being addressed",
      "default": "unknown"
    },
    "recent_failures": {
      "type": "integer",
      "description": "Number of recent failed responses (for suppression logic)",
      "default": 0
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
    "fix_details"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "dna_validate",
    {"threat_type": "Type of threat being addressed", "recent_failures": 0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
