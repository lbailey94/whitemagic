# archaeology

**Category**: archaeology | **Safety**: write
**Gana**: `gana_chariot`

## Description

Unified file archaeology — track reads/writes, find unread/changed files, search history, generate reports. Actions: mark_read, mark_written, have_read, find_unread, find_changed, recent_reads, stats, scan, report, search, process_wisdom, daily_digest.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "mark_read",
        "mark_written",
        "have_read",
        "find_unread",
        "find_changed",
        "recent_reads",
        "stats",
        "scan",
        "report",
        "search",
        "process_wisdom",
        "daily_digest"
      ],
      "description": "Action to perform",
      "default": "stats"
    },
    "path": {
      "type": "string",
      "description": "File path (for mark_read/written/have_read)"
    },
    "directory": {
      "type": "string",
      "description": "Directory to scan (for find_*/scan)"
    },
    "context": {
      "type": "string",
      "description": "Read/write context"
    },
    "note": {
      "type": "string",
      "description": "Optional note"
    },
    "insight": {
      "type": "string",
      "description": "Key insight (for mark_read)"
    },
    "query": {
      "type": "string",
      "description": "Search query (for search)"
    },
    "patterns": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Glob patterns (for find_unread/scan)"
    },
    "limit": {
      "type": "integer",
      "default": 50,
      "description": "Result limit"
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
    "archaeology",
    {"action": "Action to perform", "path": "File path (for mark_read/written/have_read)", "directory": "Directory to scan (for find_*/scan)", "context": "Read/write context", "note": "Optional note", "insight": "Key insight (for mark_read)", "query": "Search query (for search)", "patterns": [], "limit": 50, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
