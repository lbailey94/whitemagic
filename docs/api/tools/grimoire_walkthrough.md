# grimoire_walkthrough

**Category**: introspection | **Safety**: read
**Gana**: `gana_willow`

## Description

Interactive 28-chapter Grimoire walkthrough — get chapter details, exercises, and tool mappings

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "chapter": {
      "type": "integer",
      "minimum": 1,
      "maximum": 28,
      "description": "Chapter number (1-28)"
    },
    "quadrant": {
      "type": "string",
      "enum": [
        "eastern",
        "southern",
        "western",
        "northern"
      ],
      "description": "Filter by quadrant"
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
    "grimoire_walkthrough",
    {"chapter": 10, "quadrant": "Filter by quadrant", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
