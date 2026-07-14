# consciousness.mode

**Category**: synthesis | **Safety**: read
**Gana**: `gana_ghost`

## Description

Set or get the consciousness frequency mode. Modes: normal (default 30s), meditation (300s inward focus, dreaming off), rem (60s dream-heavy consolidation), deep (10s high-frequency active processing). Pass mode to set, omit to get current.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "mode": {
      "type": "string",
      "enum": [
        "normal",
        "meditation",
        "rem",
        "deep"
      ],
      "description": "Frequency mode to switch to. Omit to get current mode."
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
    "consciousness.mode",
    {"mode": "Frequency mode to switch to. Omit to get current m", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
