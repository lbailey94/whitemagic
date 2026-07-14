# windsurf.ingest

**Category**: archaeology | **Safety**: write
**Gana**: `gana_chariot`

## Description

Parse exported Windsurf transcripts and ingest into the sessions galaxy. Classifies turns by type (decision, breakthrough, error, code_change, etc.) and scores importance. Deduplicates — skips sessions already ingested.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "export_dir": {
      "type": "string",
      "description": "Directory containing .md transcript files (default: most recent export)"
    },
    "dry_run": {
      "type": "boolean",
      "default": false,
      "description": "Parse and report stats without ingesting"
    },
    "limit": {
      "type": "integer",
      "description": "Only ingest first N sessions (for testing)"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
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
    "windsurf.ingest",
    {"export_dir": "Directory containing .md transcript files (default", "dry_run": false, "limit": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
