# activation.spread

**Category**: memory | **Safety**: write
**Gana**: `gana_winnowing_basket`

## Description

Spread activation from seed memories through the association graph, priming related memories for recall.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "seed_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Memory IDs to start activation from"
    },
    "max_hops": {
      "type": "integer",
      "description": "Maximum hops from seeds (default 3)",
      "default": 3
    },
    "decay": {
      "type": "number",
      "description": "Activation decay per hop (default 0.7)",
      "default": 0.7
    },
    "cross_galaxy_factor": {
      "type": "number",
      "description": "Multiplier for cross-galaxy edges (default 0.5)",
      "default": 0.5
    },
    "min_activation": {
      "type": "number",
      "description": "Minimum activation to continue spreading (default 0.05)",
      "default": 0.05
    },
    "apply_priming": {
      "type": "boolean",
      "description": "If true, boost neuro_score and recall_count of primed memories",
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
    "seed_ids"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "activation.spread",
    {"seed_ids": [], "max_hops": 3, "decay": 0.7, "cross_galaxy_factor": 0.5, "min_activation": 0.05, "apply_priming": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
