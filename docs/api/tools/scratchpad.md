# scratchpad

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Unified scratchpad management for active work. Actions: create (new scratchpad), update (modify section), finalize (convert to permanent memory).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "create",
        "update",
        "finalize"
      ],
      "description": "Action to perform",
      "default": "create"
    },
    "name": {
      "type": "string",
      "description": "Scratchpad name (for create)"
    },
    "session_id": {
      "type": "string",
      "description": "Associated session ID (for create)"
    },
    "scratchpad_id": {
      "type": "string",
      "description": "Scratchpad ID (for update/finalize)"
    },
    "section": {
      "type": "string",
      "enum": [
        "current_focus",
        "decisions",
        "questions",
        "next_steps",
        "ideas"
      ],
      "description": "Section to update (for update)"
    },
    "content": {
      "type": "string",
      "description": "Content (for update)"
    },
    "memory_type": {
      "type": "string",
      "enum": [
        "short_term",
        "long_term"
      ],
      "default": "long_term",
      "description": "Target memory type (for finalize)"
    },
    "auto_analyze": {
      "type": "boolean",
      "default": true,
      "description": "Multi-spectral analysis (for finalize)"
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
    "scratchpad",
    {"action": "Action to perform", "name": "Scratchpad name (for create)", "session_id": "Associated session ID (for create)", "scratchpad_id": "Scratchpad ID (for update/finalize)", "section": "Section to update (for update)", "content": "Content (for update)", "memory_type": "Target memory type (for finalize)", "auto_analyze": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
