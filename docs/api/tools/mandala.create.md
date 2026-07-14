# mandala.create

**Category**: system | **Safety**: write
**Gana**: `gana_roof`

## Description

Create a new mandala compartment from a template or explicit config (MandalaOS Phase B). Templates: research (network read, creative Dharma), sandbox (no network, default Dharma), production (read-only, secure Dharma), secure (no network/fs, minimal resources). Each mandala gets its own dharma_profile, capabilities, and resource limits.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Unique mandala compartment name."
    },
    "template": {
      "type": "string",
      "enum": [
        "research",
        "sandbox",
        "production",
        "secure"
      ],
      "description": "Template to use (optional \u2014 overrides capabilities/limits/dharma_profile)."
    },
    "tier": {
      "type": "string",
      "enum": [
        "auto",
        "thread",
        "namespace",
        "container",
        "wasm"
      ],
      "description": "Isolation tier override."
    },
    "dharma_profile": {
      "type": "string",
      "description": "Dharma rules profile (default, creative, secure)."
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Capability grants (e.g., network_read, fs_write:/tmp)."
    },
    "limits": {
      "type": "object",
      "description": "Resource limits (timeout_s, max_memory_mb, max_cpu_s, max_disk_mb)."
    },
    "ephemeral": {
      "type": "boolean",
      "default": true,
      "description": "Auto-destroy on completion."
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
    "mandala.create",
    {"name": "Unique mandala compartment name.", "template": "Template to use (optional \u2014 overrides capabilities", "tier": "Isolation tier override.", "dharma_profile": "Dharma rules profile (default, creative, secure).", "capabilities": [], "ephemeral": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
