# effect.visualize

**Category**: dharma | **Safety**: read
**Gana**: `gana_ghost`

## Description

Export effect flow visualization (MandalaOS Phase C). Generates DOT (Graphviz), Mermaid, or JSON visualization of effect relationships. Pass a tool name for per-tool view, or omit for system-wide summary.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "description": "Tool name to visualize. Omit for system-wide view."
    },
    "format": {
      "type": "string",
      "enum": [
        "dot",
        "mermaid",
        "json"
      ],
      "default": "dot",
      "description": "Output format."
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
    "effect.visualize",
    {"tool": "Tool name to visualize. Omit for system-wide view.", "format": "Output format.", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
