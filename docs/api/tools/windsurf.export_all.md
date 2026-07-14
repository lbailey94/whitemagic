# windsurf.export_all

**Category**: archaeology | **Safety**: write
**Gana**: `gana_chariot`

## Description

Bulk export all Windsurf/Cascade conversations via the language server gRPC API. Falls back to .pb file parsing if the API is unavailable. Outputs markdown transcripts + JSON metadata to a dated directory.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "output_dir": {
      "type": "string",
      "description": "Custom output directory (default: ~/Desktop/WindsurfRips/api_export_YYYY-MM-DD)"
    },
    "full_steps": {
      "type": "boolean",
      "default": false,
      "description": "Also fetch complete step-by-step data (bypasses 200K truncation)"
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
    "windsurf.export_all",
    {"output_dir": "Custom output directory (default: ~/Desktop/Windsu", "full_steps": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
