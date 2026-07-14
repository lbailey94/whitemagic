# zodiac.activate

**Category**: system | **Safety**: read
**Gana**: `gana_dipper`

## Description

Activate a specific zodiac core with context. Each core (Aries through Pisces) provides specialized processing: Aries=initiative, Taurus=stability, Gemini=synthesis, etc. Returns wisdom, resonance score, and transformation applied.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "core": {
      "type": "string",
      "enum": [
        "aries",
        "taurus",
        "gemini",
        "cancer",
        "leo",
        "virgo",
        "libra",
        "scorpio",
        "sagittarius",
        "capricorn",
        "aquarius",
        "pisces"
      ],
      "description": "Zodiac sign to activate"
    },
    "context": {
      "type": "object",
      "description": "Operation context",
      "properties": {
        "operation": {
          "type": "string",
          "description": "Operation type"
        },
        "intention": {
          "type": "string",
          "description": "Intention behind activation"
        },
        "urgency": {
          "type": "string",
          "enum": [
            "low",
            "normal",
            "high"
          ],
          "default": "normal"
        }
      }
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
    "core"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "zodiac.activate",
    {"core": "Zodiac sign to activate", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
