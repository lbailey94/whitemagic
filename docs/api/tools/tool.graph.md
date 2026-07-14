# tool.graph

**Category**: introspection | **Safety**: read
**Gana**: `gana_extended_net`

## Description

Query the tool dependency graph. Without arguments, returns a summary (total tools, edges, edge types). With a 'tool' argument, returns next_steps, prerequisites, and plan. With detail='full', returns all edges.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "description": "Tool name to query relationships for (optional \u2014 omit for graph summary)"
    },
    "detail": {
      "type": "string",
      "enum": [
        "summary",
        "full"
      ],
      "default": "summary",
      "description": "Level of detail: summary (default) or full (all edges)"
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
    "tool.graph",
    {"tool": "Tool name to query relationships for (optional \u2014 o", "detail": "Level of detail: summary (default) or full (all ed", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
