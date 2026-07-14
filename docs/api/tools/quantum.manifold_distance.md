# quantum.manifold_distance

**Category**: metrics | **Safety**: read
**Gana**: `gana_tail`

## Description

Compute geodesic distance between two points on a Riemannian manifold (euclidean, hyperbolic, or spherical). Dispatchs to Julia QuantumGeometry.jl first, then Rust, then Python.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "a": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "First point coordinates"
    },
    "b": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Second point coordinates"
    },
    "manifold": {
      "type": "string",
      "enum": [
        "euclidean",
        "hyperbolic",
        "spherical"
      ],
      "default": "euclidean",
      "description": "Manifold type"
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
    "a",
    "b"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "quantum.manifold_distance",
    {"a": [], "b": [], "manifold": "Manifold type", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
