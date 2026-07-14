# llama.agent

**Category**: inference | **Safety**: write
**Gana**: `gana_roof`

## Description

Run an agentic loop with a local llama.cpp model that can autonomously call WhiteMagic tools (search, create memories, analyze patterns) to complete a given task. Injects relevant memories as context and supports up to 10 tool-call iterations.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model": {
      "type": "string",
      "description": "llama.cpp model name (e.g., 'llama3.2', 'phi4', 'qwen2.5')"
    },
    "task": {
      "type": "string",
      "description": "The task or question for the agent"
    },
    "max_iterations": {
      "type": "integer",
      "default": 10,
      "description": "Maximum tool-call rounds"
    },
    "context": {
      "type": "boolean",
      "default": true,
      "description": "Whether to inject relevant memories"
    },
    "store": {
      "type": "boolean",
      "default": false,
      "description": "Store outputs as memories"
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
    "model",
    "task"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "llama.agent",
    {"model": "llama.cpp model name (e.g., 'llama3.2', 'phi4', 'q", "task": "The task or question for the agent", "max_iterations": 10, "context": true, "store": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
