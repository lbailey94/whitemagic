# jit_research

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Iterative plan-search-reflect research across the memory store. Decomposes a query into sub-questions, searches for evidence, reflects on gaps, and synthesizes findings.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The research question to investigate.",
      "default": "current system state"
    },
    "max_rounds": {
      "type": "integer",
      "description": "Maximum iteration rounds (default 3).",
      "default": 3
    },
    "evidence_limit": {
      "type": "integer",
      "description": "Evidence items per sub-question (default 5).",
      "default": 5
    },
    "hops": {
      "type": "integer",
      "description": "Graph walk depth (default 2).",
      "default": 2
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
    "jit_research",
    {"query": "The research question to investigate.", "max_rounds": 3, "evidence_limit": 5, "hops": 2, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
