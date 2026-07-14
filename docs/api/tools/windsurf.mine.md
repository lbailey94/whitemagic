# windsurf.mine

**Category**: archaeology | **Safety**: read
**Gana**: `gana_chariot`

## Description

Cross-session pattern mining — extracts decisions, breakthroughs, errors, topics, and user directives from an export directory. Returns structured results suitable for codex galaxy ingestion.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "export_dir": {
      "type": "string",
      "description": "Directory containing exported .md transcript files"
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
    "export_dir"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "windsurf.mine",
    {"export_dir": "Directory containing exported .md transcript files", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
