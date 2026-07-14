# simulation.search

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Run MCTS-guided trajectory tree search for creative exploration. Uses UCB1 with novelty bonus for selection. Returns best trajectory and tree statistics.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "iterations": {
      "type": "integer",
      "description": "MCTS iterations (default: 100)"
    },
    "max_depth": {
      "type": "integer",
      "description": "Max tree depth (default: 10)"
    },
    "branching_factor": {
      "type": "integer",
      "description": "Children per node (default: 3)"
    },
    "initial_state": {
      "type": "object",
      "description": "Initial state dict"
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
    "simulation.search",
    {"iterations": 10, "max_depth": 10, "branching_factor": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
