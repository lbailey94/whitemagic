# codebase.scan

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Scan the codebase and ingest files + directory topology into the codex galaxy. Files are chunked with overlapping windows (no truncation data loss). Supports incremental mode (skips unchanged files via content-hash dedup). Optionally triggers semantic embedding indexing after ingestion. Use this to build a self-model of the project that enables semantic recall.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "project_root": {
      "type": "string",
      "description": "Root directory to scan. Defaults to WM_ROOT."
    },
    "incremental": {
      "type": "boolean",
      "description": "If true, skip files whose content hash hasn't changed.",
      "default": true
    },
    "max_files": {
      "type": "integer",
      "description": "Maximum number of files to ingest.",
      "default": 10000
    },
    "embed": {
      "type": "boolean",
      "description": "If true, trigger semantic embedding indexing after ingestion.",
      "default": true
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
    "codebase.scan",
    {"project_root": "Root directory to scan. Defaults to WM_ROOT.", "incremental": true, "max_files": 10000, "embed": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
