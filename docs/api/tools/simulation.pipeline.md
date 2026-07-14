# simulation.pipeline

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Run the full P5 simulation pipeline end-to-end: create world, run Monte Carlo scenario, analyze with dream consolidation, synthesize insights, and optionally record/resolve calibrated predictions. Chains all 8 P5 components in a single call.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "scenario_name": {
      "type": "string",
      "description": "Name for the scenario"
    },
    "seed_documents": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "archetypes": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "num_personas": {
      "type": "integer",
      "description": "Personas per trial (default: 3)"
    },
    "ticks_per_trial": {
      "type": "integer",
      "description": "Ticks per trial (default: 10)"
    },
    "num_trials": {
      "type": "integer",
      "description": "Number of MC trials (default: 10)"
    },
    "prediction_statement": {
      "type": "string",
      "description": "Optional prediction to record"
    },
    "prediction_probability": {
      "type": "number",
      "description": "Predicted probability [0,1]"
    },
    "consolidate": {
      "type": "boolean",
      "description": "Run dream consolidation (default: true)"
    },
    "top_n_insights": {
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
    "simulation.pipeline",
    {"scenario_name": "Name for the scenario", "seed_documents": [], "archetypes": [], "num_personas": 10, "ticks_per_trial": 10, "num_trials": 10, "prediction_statement": "Optional prediction to record", "prediction_probability": 1.0, "consolidate": false, "top_n_insights": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
