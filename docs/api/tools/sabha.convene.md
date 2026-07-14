# sabha.convene

**Category**: governance | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Convene a Gana Sabhā (council) for cross-quadrant deliberation. When a task spans multiple quadrants of the 28-mansion mandala, the Sabhā gathers perspectives from quadrant elders, detects inter-Gana conflicts, and produces an arbiter recommendation. Based on Mahābhārata 12.108.25: 'The king, acting in concert with the leaders, should do what is for the good of the whole order.'

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "Description of the task requiring cross-quadrant council"
    },
    "ganas": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Specific Ganas to include (optional, defaults to quadrant elders)"
    },
    "quadrants": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "East",
          "South",
          "West",
          "North"
        ]
      },
      "description": "Specific quadrants to consult (optional, defaults to all)"
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
  },
  "required": [
    "task"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "sabha.convene",
    {"task": "Description of the task requiring cross-quadrant c", "ganas": [], "quadrants": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
