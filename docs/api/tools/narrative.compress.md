# narrative.compress

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Compress clusters of episodic memories into coherent narrative summaries. Runs as a dream phase or on-demand.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "max_clusters": {
      "type": "integer",
      "description": "Maximum clusters to process (default 5).",
      "default": 5
    },
    "sample_limit": {
      "type": "integer",
      "description": "How many recent memories to scan (default 500).",
      "default": 500
    },
    "dry_run": {
      "type": "boolean",
      "description": "Preview without persisting narratives.",
      "default": false
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
    "narrative.compress",
    {"max_clusters": 5, "sample_limit": 500, "dry_run": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
