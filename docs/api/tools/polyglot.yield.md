# polyglot.yield

**Category**: inference | **Safety**: read
**Gana**: `gana_tail`

## Description

Execute yield curve operations through the Julia yield backend. Models temporal value of improvements: decaying, compounding, appreciating, transient. Supports value_at, duration, fit_parameters, portfolio_duration, select_by_horizon, detect_regime_change.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": [
        "value_at",
        "duration",
        "fit_parameters",
        "portfolio_duration",
        "select_by_horizon",
        "detect_regime_change"
      ],
      "description": "Yield curve operation to execute"
    },
    "yield_type": {
      "type": "string",
      "enum": [
        "decaying",
        "compounding",
        "appreciating",
        "transient"
      ],
      "default": "decaying"
    },
    "t": {
      "type": "number",
      "description": "Time point"
    },
    "v0": {
      "type": "number",
      "default": 1.0
    },
    "lambda": {
      "type": "number",
      "default": 0.1
    },
    "r": {
      "type": "number",
      "default": 0.05
    },
    "tau": {
      "type": "number",
      "default": 10.0
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
    "operation"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "polyglot.yield",
    {"operation": "Yield curve operation to execute", "yield_type": "example", "t": 1.0, "v0": 1.0, "lambda": 0.1, "r": 0.05, "tau": 10.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
