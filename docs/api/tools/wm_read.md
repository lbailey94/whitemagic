# wm_read

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Unified read interface — auto-selects best strategy or uses explicit mode. Modes: auto, hybrid (vector+graph RRF), graph_walk, semantic, lexical, spatial (5D KNN), constellation, temporal, codebase (Fragment), strata (static analysis), id. Default mode 'auto' detects: mem_* → id, path present → codebase, coords present → spatial, tags without query → constellation, otherwise → hybrid.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query text or memory ID (e.g. 'mem_abc123')"
    },
    "mode": {
      "type": "string",
      "enum": [
        "auto",
        "hybrid",
        "graph_walk",
        "semantic",
        "lexical",
        "spatial",
        "constellation",
        "temporal",
        "codebase",
        "strata",
        "id"
      ],
      "default": "auto",
      "description": "Read strategy. 'auto' detects best strategy from query shape."
    },
    "limit": {
      "type": "integer",
      "description": "Maximum results to return",
      "default": 10
    },
    "include_private": {
      "type": "boolean",
      "description": "Include private/excluded memories in results",
      "default": false
    },
    "include_cold": {
      "type": "boolean",
      "description": "Search cold storage / archived memories",
      "default": false
    },
    "path": {
      "type": "string",
      "description": "Codebase path for codebase mode (Fragment/Rust acceleration)"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Tags for constellation mode"
    },
    "coords": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "minItems": 5,
      "maxItems": 5,
      "description": "5D holographic coordinates [x, y, z, w, v] for spatial mode"
    },
    "time_window": {
      "type": "string",
      "description": "Time window for temporal mode (e.g. '7d', '30d')",
      "default": "7d"
    },
    "bucket": {
      "type": "string",
      "description": "Bucket granularity for temporal mode (e.g. '1d', '7d')",
      "default": "1d"
    },
    "hops": {
      "type": "integer",
      "description": "Graph walk depth for graph_walk mode",
      "default": 2
    },
    "anchor_limit": {
      "type": "integer",
      "description": "Number of anchor results for graph_walk mode",
      "default": 5
    },
    "strata": {
      "type": "boolean",
      "description": "When True with path, auto-detects strata mode for static analysis",
      "default": false
    },
    "format": {
      "type": "string",
      "enum": [
        "json",
        "text",
        "sarif",
        "html"
      ],
      "description": "Output format for strata mode",
      "default": "json"
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
    "wm_read",
    {"query": "Search query text or memory ID (e.g. 'mem_abc123')", "mode": "Read strategy. 'auto' detects best strategy from q", "limit": 10, "include_private": false, "include_cold": false, "path": "Codebase path for codebase mode (Fragment/Rust acc", "tags": [], "coords": [], "time_window": "Time window for temporal mode (e.g. '7d', '30d')", "bucket": "Bucket granularity for temporal mode (e.g. '1d', '", "hops": 2, "anchor_limit": 5, "strata": false, "format": "Output format for strata mode", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
