# simulation.run

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Run a Monte Carlo simulation scenario with varied initial conditions. Generates N trials with different persona configurations and analyzes outcome distribution, parameter sensitivity, and robustness.

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
    "simulation.run",
    {"scenario_name": "Name for the scenario", "seed_documents": [], "archetypes": [], "num_personas": 10, "ticks_per_trial": 10, "num_trials": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
