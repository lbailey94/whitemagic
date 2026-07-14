# harmony_vector

**Category**: metrics | **Safety**: read
**Gana**: `gana_straddling_legs`

## Description

Get the multi-dimensional Harmony Vector — Whitemagic's real-time health pulse. Returns seven normalized [0-1] dimensions: balance (yin/yang ratio), throughput, latency, error_rate, dharma (ethical score), karma_debt (declared-vs-actual side-effect mismatches), and energy (resource pressure). Also reports guna distribution (sattvic/rajasic/tamasic), p50/p95 latency, and a composite harmony_score. Use this to self-regulate agent behavior.

## Input Schema

```json
{
  "type": "object",
  "properties": {
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
    "harmony_vector",
    {"request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
