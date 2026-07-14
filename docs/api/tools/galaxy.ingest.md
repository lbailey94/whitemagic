# galaxy.ingest

**Category**: system | **Safety**: write
**Gana**: `gana_void`

## Description

Ingest files from a directory into a galaxy's memory store. Reads text files matching a glob pattern and stores each as a memory.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Galaxy name to ingest into",
      "default": "main"
    },
    "source_path": {
      "type": "string",
      "description": "Directory path to ingest from",
      "default": "."
    },
    "pattern": {
      "type": "string",
      "default": "**/*.md",
      "description": "Glob pattern for files"
    },
    "max_files": {
      "type": "integer",
      "default": 500,
      "description": "Max files to ingest"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Tags to apply to all ingested memories"
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
    "galaxy.ingest",
    {"name": "Galaxy name to ingest into", "source_path": "Directory path to ingest from", "pattern": "Glob pattern for files", "max_files": 500, "tags": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
