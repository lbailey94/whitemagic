# graph_topology

**Category**: introspection | **Safety**: read
**Gana**: `gana_ghost`

## Description

Graph topology introspection — centrality metrics, community detection, bridge nodes, echo chamber detection. Actions: summary, rebuild, centrality, communities, bridges, echo_chambers.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "description": "Action to perform: summary, rebuild, centrality, communities, bridges, echo_chambers",
      "default": "summary",
      "enum": [
        "summary",
        "rebuild",
        "centrality",
        "communities",
        "bridges",
        "echo_chambers"
      ]
    },
    "top_n": {
      "type": "integer",
      "description": "Max results for bridges (default: 10)",
      "default": 10
    },
    "sample_limit": {
      "type": "integer",
      "description": "Max edges to load for rebuild (default: 50000)",
      "default": 50000
    },
    "sigma_threshold": {
      "type": "number",
      "description": "Sigma threshold for echo chamber detection (default: 2.0)",
      "default": 2.0
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
    "graph_topology",
    {"action": "Action to perform: summary, rebuild, centrality, c", "top_n": 10, "sample_limit": 50000, "sigma_threshold": 2.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
