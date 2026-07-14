# simulation.calibrate

**Category**: system | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Record predictions, resolve them against reality, and get calibration scorecard with Brier scores. Supports three actions: record, resolve, scorecard. Feeds calibration gap back into future predictions.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "record",
        "resolve",
        "scorecard"
      ],
      "description": "Action (default: scorecard)"
    },
    "statement": {
      "type": "string",
      "description": "Prediction statement (for record)"
    },
    "probability": {
      "type": "number",
      "description": "Predicted probability [0,1] (for record)"
    },
    "outcome": {
      "type": "boolean",
      "description": "Actual outcome (for resolve)"
    },
    "prediction_id": {
      "type": "string",
      "description": "Prediction ID (for resolve)"
    },
    "confidence": {
      "type": "number",
      "description": "Confidence [0,1] (for record)"
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
    "simulation.calibrate",
    {"action": "Action (default: scorecard)", "statement": "Prediction statement (for record)", "probability": 1.0, "outcome": false, "prediction_id": "Prediction ID (for resolve)", "confidence": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
