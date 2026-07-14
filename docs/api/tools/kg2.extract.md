# kg2.extract

**Category**: memory | **Safety**: write
**Gana**: `gana_chariot`

## Description

Extract entities and relations using LightNER (fast pattern-based extraction)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "source_id": {
      "type": "string",
      "description": "Source memory/document ID",
      "default": "manual"
    },
    "text": {
      "type": "string",
      "description": "Text to extract entities from"
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
    "kg2.extract",
    {"source_id": "Source memory/document ID", "text": "Text to extract entities from", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
