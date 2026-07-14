# state.update

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Update the current work state. Set current task, add/complete tasks, add next steps, record file modifications, decisions, or errors. Replaces reliance on static .md docs for short-term context.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "current_task": {
      "type": "string",
      "description": "Set what's being worked on now"
    },
    "add_active_task": {
      "type": "string",
      "description": "Add an active task"
    },
    "complete_task": {
      "type": "string",
      "description": "Mark a task as completed"
    },
    "add_next_step": {
      "type": "string",
      "description": "Add a next step"
    },
    "clear_next_steps": {
      "type": "boolean",
      "description": "Clear all next steps"
    },
    "context_key": {
      "type": "string",
      "description": "Context key to set"
    },
    "context_value": {
      "type": "string",
      "description": "Context value to set"
    },
    "record_file": {
      "type": "string",
      "description": "Record a file modification (path)"
    },
    "file_description": {
      "type": "string",
      "description": "Description of file change"
    },
    "record_decision": {
      "type": "string",
      "description": "Record a decision"
    },
    "decision_rationale": {
      "type": "string",
      "description": "Rationale for the decision"
    },
    "record_error": {
      "type": "string",
      "description": "Record an error"
    },
    "error_context": {
      "type": "string",
      "description": "Context for the error"
    },
    "last_session_summary": {
      "type": "string",
      "description": "Summary of last session"
    },
    "last_session_id": {
      "type": "string",
      "description": "ID of last session"
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
    "state.update",
    {"current_task": "Set what's being worked on now", "add_active_task": "Add an active task", "complete_task": "Mark a task as completed", "add_next_step": "Add a next step", "clear_next_steps": false, "context_key": "Context key to set", "context_value": "Context value to set", "record_file": "Record a file modification (path)", "file_description": "Description of file change", "record_decision": "Record a decision", "decision_rationale": "Rationale for the decision", "record_error": "Record an error", "error_context": "Context for the error", "last_session_summary": "Summary of last session", "last_session_id": "ID of last session", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
