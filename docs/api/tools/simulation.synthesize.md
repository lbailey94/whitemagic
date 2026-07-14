# simulation.synthesize

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Synthesize emergent insights from simulation trajectories. Extracts patterns, discovers cross-trajectory connections, detects anomalies, and generates strategic insights. Ranks by novelty, impact, coherence, and cross-domain potential.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "scenario_name": {
      "type": "string",
      "description": "Scenario to synthesize from"
    },
    "top_n": {
      "type": "integer",
      "description": "Top insights to return (default: 5)"
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
    "simulation.synthesize",
    {"scenario_name": "Scenario to synthesize from", "top_n": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
