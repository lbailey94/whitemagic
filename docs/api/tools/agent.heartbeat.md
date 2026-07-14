# agent.heartbeat

**Category**: agent | **Safety**: write
**Gana**: `gana_girl`

## Description

Send a heartbeat to keep agent registration active, with optional workload update

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "agent_id": {
      "type": "string",
      "description": "Agent ID",
      "default": "current-agent"
    },
    "workload": {
      "type": "number",
      "description": "Current workload 0.0-1.0",
      "default": 0.0
    },
    "current_task": {
      "type": "string",
      "description": "Currently executing task ID"
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
    "agent.heartbeat",
    {"agent_id": "Agent ID", "workload": 0.0, "current_task": "Currently executing task ID", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
