# simulation.create

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Create a simulation world with personas, seed documents, and rules. Sets up a dedicated simulation galaxy and generates cognitive agents with distinct internal states.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "world_name": {
      "type": "string",
      "description": "Name for the simulation world"
    },
    "seed_documents": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Seed document contents"
    },
    "personas": {
      "type": "array",
      "items": {
        "type": "object"
      },
      "description": "Persona specs [{name, archetype}]"
    },
    "archetypes": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Persona archetypes (analyst, creative, conservative, explorer, synthesizer)"
    },
    "rules": {
      "type": "array",
      "items": {
        "type": "object"
      },
      "description": "Rule specs [{name, description, type}]"
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
    "world_name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "simulation.create",
    {"world_name": "Name for the simulation world", "seed_documents": [], "personas": [], "archetypes": [], "rules": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
