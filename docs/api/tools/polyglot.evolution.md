# polyglot.evolution

**Category**: inference | **Safety**: read
**Gana**: `gana_tail`

## Description

Execute evolution algorithms through the Rust evolution backend. Supports information theory (shannon_entropy, kl_divergence, information_gain), thermodynamic simulation (thermo_cool, thermo_reheat, thermo_adapt, boltzmann_select), HRR composition (hrr_encode, hrr_bind, hrr_unbind, hrr_superposition), Monte Carlo integration (mc_run_trials, mc_importance_sampling), and counterfactual estimation (cf_project_forward, cf_estimate_impact).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": [
        "shannon_entropy",
        "kl_divergence",
        "information_gain",
        "system_uncertainty",
        "adapt_weights",
        "exploration_score",
        "thermo_cool",
        "thermo_reheat",
        "thermo_adapt",
        "boltzmann_probabilities",
        "boltzmann_select",
        "hrr_encode",
        "hrr_bind",
        "hrr_unbind",
        "hrr_superposition",
        "hrr_synergy",
        "hrr_similarity",
        "mc_run_trials",
        "mc_importance_sampling",
        "mc_control_variates",
        "mc_antithetic_variates",
        "cf_project_forward",
        "cf_bootstrap_ci",
        "cf_estimate_impact"
      ],
      "description": "Evolution operation to execute"
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
    "operation"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "polyglot.evolution",
    {"operation": "Evolution operation to execute", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
