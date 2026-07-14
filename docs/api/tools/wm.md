# wm

**Category**: system | **Safety**: write

## Description

[WM] WhiteMagic meta-tool — single entry point that auto-routes natural language to 28 Ganas / 630 tools. 'World in a seed'. Use for any WhiteMagic operation without knowing the specific tool name. Supports explicit route= override (e.g. route='gana_neck.create_memory'). Use thought='help' or route='discover' to see all Ganas and their tools. Use route='schema:gana_name' to get a Gana's nested tool list.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "thought": {
      "type": "string",
      "description": "Natural language describing what you want to do. Use 'help' to discover all capabilities."
    },
    "route": {
      "type": "string",
      "description": "Explicit route: 'gana_name.sub_tool', 'discover', or 'schema:gana_name'."
    },
    "args": {
      "type": "object",
      "description": "Args dict to pass through to the target tool."
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
    "wm",
    {"thought": "Natural language describing what you want to do. U", "route": "Explicit route: 'gana_name.sub_tool', 'discover', ", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
