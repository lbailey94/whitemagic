# code.graph

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Build or rebuild the code structure graph from source files. Extracts functions, classes, files, modules as nodes and calls, imports, inherits, defines as edges using tree-sitter (Rust) or Python ast/regex fallback. Supports incremental mode (only reparse changed files via content hash). Persists to SQLite for fast queries.

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
      "description": "If true, only reparse files whose content hash changed.",
      "default": true
    },
    "max_files": {
      "type": "integer",
      "description": "Maximum number of files to process.",
      "default": 50000
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
    "code.graph",
    {"project_root": "Root directory to scan. Defaults to WM_ROOT.", "incremental": true, "max_files": 50000, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
