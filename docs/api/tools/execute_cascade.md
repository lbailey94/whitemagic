# execute_cascade

**Category**: system | **Safety**: write
**Gana**: `gana_tail`

## Description

Execute an intelligent tool chain pattern with Yin-Yang balance pacing

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "pattern_name": {
      "type": "string",
      "description": "Cascade pattern name (e.g., 'analyze_codebase')",
      "default": "list"
    },
    "context": {
      "type": "object",
      "description": "Context dictionary with inputs for the pattern",
      "default": {}
    },
    "options": {
      "type": "object",
      "description": "Execution options (enable_yin_yang, max_parallel_calls, dry_run)"
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
    "execute_cascade",
    {"pattern_name": "Cascade pattern name (e.g., 'analyze_codebase')", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
