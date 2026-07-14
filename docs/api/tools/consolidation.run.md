# consolidation.run

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Run a sleep consolidation cycle — transfer, strengthen, and prune memories across galaxies.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "dry_run": {
      "type": "boolean",
      "description": "If true, only report what would be transferred without modifying databases",
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
    "consolidation.run",
    {"dry_run": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
