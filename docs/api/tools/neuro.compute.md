# neuro.compute

**Category**: synthesis | **Safety**: read
**Gana**: `gana_dipper`

## Description

Compute neuromodulator (dopamine, serotonin, acetylcholine) levels from activity signals.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "novelty": {
      "type": "number",
      "description": "Novelty signal 0-1",
      "default": 0.5
    },
    "reward": {
      "type": "number",
      "description": "Reward signal 0-1",
      "default": 0.5
    },
    "stability": {
      "type": "number",
      "description": "Stability signal 0-1",
      "default": 0.5
    },
    "coherence": {
      "type": "number",
      "description": "Coherence signal 0-1",
      "default": 0.5
    },
    "focus": {
      "type": "number",
      "description": "Focus signal 0-1",
      "default": 0.5
    },
    "activity_level": {
      "type": "number",
      "description": "Activity level 0-1",
      "default": 0.5
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
    "neuro.compute",
    {"novelty": 0.5, "reward": 0.5, "stability": 0.5, "coherence": 0.5, "focus": 0.5, "activity_level": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
