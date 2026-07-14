# simulation.analyze

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Analyze simulation results and optionally run dream-cycle consolidation. Returns outcome distribution, coherence statistics, and consolidation reports with insights and recommendations.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "scenario_name": {
      "type": "string",
      "description": "Scenario to analyze"
    },
    "consolidate": {
      "type": "boolean",
      "description": "Run dream-cycle consolidation (default: true)"
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
    "scenario_name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "simulation.analyze",
    {"scenario_name": "Scenario to analyze", "consolidate": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
