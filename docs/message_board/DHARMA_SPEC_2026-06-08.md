# WhiteMagic Dharma Specification v0.1.0

**Version**: 0.1.0  
**Date**: 2026-06-08  
**Status**: Draft — intended for community review, grant appendices, and competitive positioning  
**Canonical implementation**: `core/whitemagic/dharma/rules.py`  
**License**: MIT  

---

## 1. What This Is

Dharma is WhiteMagic's declarative policy engine for agentic AI governance. It evaluates every tool call, memory operation, and external action against YAML-defined ethical and safety rules before execution. Unlike cloud-dependent policy services, Dharma runs entirely locally, requires no network access, and leaves an immutable audit trail (Karmic Trace + Karma Ledger).

This document specifies:
- The YAML rule schema
- The evaluation runtime
- The action spectrum
- The audit trail format
- The upgrade path toward "governance for the paranoid"

---

## 2. Design Principles

1. **Local-first**: No cloud dependency, no API keys, no telemetry
2. **Deterministic**: Same action + same rules → same decision, every time
3. **Symbolic**: 28-Gana taxonomy provides a memorable, culturally resonant vocabulary
4. **Accountable**: Every evaluation is logged with full context (Karmic Trace)
5. **Graduated**: Five action levels from observation to blocking
6. **Hot-reloadable**: Rules change without restart
7. **Polyglot-ready**: Haskell FFI bridge for high-assurance paths

---

## 3. YAML Rule Schema

### 3.1 Top-Level Document

```yaml
dharma_spec_version: "0.1.0"  # Phase 1 addition
extends: "default"            # Phase 1 addition — inherit from base profile

rules:
  - name: "rule_name"
    description: "Human-readable purpose"
    action: "warn"            # log | tag | warn | throttle | block | transform
    severity: 0.6             # 0.0–1.0
    explain: "Why this rule triggered"
    profile: "default"        # default | creative | secure | violet
    tool_patterns: ["delete_*", "write_*"]
    keyword_patterns: ["harm", "destroy"]
    safety_levels: ["WRITE", "DELETE"]
    regex_patterns: ["(?i)password\\s*=\\s*\\S+"]
    transform:                # Phase 1 addition
      type: "redact"
      field: "parameters.password"
```

### 3.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dharma_spec_version` | string | No | Schema version for compatibility checking |
| `extends` | string | No | Base profile to inherit rules from |
| `name` | string | Yes | Unique rule identifier |
| `description` | string | Yes | Human-readable purpose |
| `action` | enum | Yes | `log`, `tag`, `warn`, `throttle`, `block`, `transform` |
| `severity` | float | Yes | 0.0 (trivial) to 1.0 (critical) |
| `explain` | string | Yes | Reason shown to operator / in audit |
| `profile` | string | Yes | `default`, `creative`, `secure`, `violet` |
| `tool_patterns` | list[str] | No | fnmatch-style tool name globs |
| `keyword_patterns` | list[str] | No | Substring matches on action description |
| `safety_levels` | list[str] | No | Exact matches on action safety tag |
| `regex_patterns` | list[str] | No | Regex matches on action description |
| `transform` | dict | No | Parameter rewriting / redaction (Phase 1) |

### 3.3 Action Spectrum

| Action | Effect | Use Case |
|--------|--------|----------|
| `log` | Record in Karmic Trace only | Benign observation |
| `tag` | Add metadata tag, proceed | Mark for later review |
| `warn` | Log + emit warning, proceed | Cautionary but not blocking |
| `throttle` | Rate-limit + warn | Repetitive or high-volume risk |
| `block` | Deny execution entirely | Critical safety boundary |
| `transform` | Rewrite parameters, proceed | Redact PII, scope limits (Phase 1) |

**Conflict resolution**: When multiple rules trigger, the *most restrictive* action wins (block > throttle > warn > tag > log > transform).

### 3.4 Profiles

| Profile | Posture | Use Case |
|---------|---------|----------|
| `default` | Balanced | General operation |
| `creative` | Permissive | Research, brainstorming, artistic work |
| `secure` | Restrictive | Production, sensitive data, untrusted inputs |
| `violet` | Paranoid | Air-gapped, adversarial, high-stakes |

---

## 4. Evaluation Runtime

### 4.1 Action Input Format

```python
{
    "tool": "delete_memory",
    "description": "remove old training data from staging",
    "safety": "DELETE",
    "parameters": {"memory_id": "abc123"},
    "context": {"user": "lucas", "session_id": "sess-42"},
}
```

### 4.2 Decision Output Format

```python
{
    "action": "warn",
    "score": 0.4,              # 1.0 - severity
    "triggered_rules": ["mass_mutation"],
    "explain": "Bulk mutations detected. Verify scope is intentional.",
    "profile": "default",
    "timestamp": "2026-06-08T15:30:00Z",
    "request_id": "uuid",
}
```

### 4.3 Evaluation Pipeline

1. **Haskell fast-path** (if available): FFI bridge evaluates via compiled rule set
2. **Python fallback**: Pattern matching against loaded rules
3. **Worst-action aggregation**: Most restrictive triggered rule wins
4. **Karmic trace write**: Immutable append-only log entry
5. **Karma Ledger record**: Merkle-hashed audit bundle

### 4.4 Hot Reload

Rules are checked for filesystem changes on each evaluation (mtime comparison). If any `.yaml` or `.yml` in the rules directory changed, the engine reloads automatically. No restart required.

---

## 5. Karmic Trace & Karma Ledger

### 5.1 Karmic Trace

In-memory ring buffer of recent decisions (default 50 entries). Each entry contains:
- Timestamp
- Action context (tool, description, safety)
- Matched rules
- Decision outcome
- Profile active at time of evaluation

### 5.2 Karma Ledger

Persistent, append-only, Merkle-hashed audit log stored in SQLite. Each record is tamper-evident: altering any past record breaks the hash chain.

Fields:
- `timestamp` (ISO-8601)
- `action_hash` (SHA-256 of action dict)
- `rules_triggered` (JSON array)
- `decision` (action, score, explain)
- `merkle_root` (cumulative hash)
- `prev_hash` (chain linkage)

---

## 6. Comparison to External Standards

| Feature | WhiteMagic Dharma | Microsoft ACS | GRDL | ADP |
|---------|-------------------|---------------|------|-----|
| **License** | MIT | Open-source | Unknown | Apache 2.0 |
| **Local-first** | ✅ | ❌ (Azure) | Unknown | Partial |
| **YAML rules** | ✅ | ✅ (manifest) | ✅ | Partial |
| **Hot reload** | ✅ | ✅ | Unknown | Unknown |
| **Immutable audit** | ✅ (Merkle) | ✅ (ACS logs) | Unknown | ✅ (hash chain) |
| **Action spectrum** | 6 levels | allow/warn/deny/escalate | Unknown | A1–A5 taxonomy |
| **Symbolic taxonomy** | ✅ (28-Gana) | ❌ | ❌ | ❌ |
| **Memory integration** | ✅ (dream cycle) | ❌ | ❌ | ❌ |
| **Kill switches** | ✅ (feature flags) | ✅ | Unknown | Unknown |
| **Formal verification** | ❌ (Phase 3) | Partial (Cedar) | Unknown | ❌ |
| **Taint tracking** | ❌ (Phase 2) | ❌ | Unknown | ❌ |
| **Default-deny network** | ❌ (Phase 2) | ✅ | Unknown | Unknown |

---

## 7. Upgrade Path

### Phase 1: Schema Hardening (v0.2.0)
- [ ] Add `transform` action (redact, scope-limit, parameter rewrite)
- [ ] Add `dharma_spec_version` field
- [ ] Add `extends` inheritance
- [ ] Add schema validation on load
- [ ] Document public API

### Phase 2: Security Depth (v0.3.0)
- [ ] Add default-deny network egress wrapper
- [ ] Add taint tracking (provenance tags on tool inputs)
- [ ] Add 4-tier evaluation (policy → heuristic → LLM → human)
- [ ] Add kernel sandboxing integration (Landlock/seccomp)

### Phase 3: Formal Methods (v0.4.0)
- [ ] Add formally verifiable policy subset (Koka/Idris bridge)
- [ ] Add compile-time enforcement (typestate)
- [ ] Add OPA/Rego backend
- [ ] Add Cedar backend
- [ ] Publish academic-style architecture paper

---

## 8. Example Rules

### 8.1 Default Profile

```yaml
dharma_spec_version: "0.1.0"

rules:
  - name: privacy_guard
    description: Flag operations involving private or sensitive data
    action: warn
    severity: 0.6
    explain: "This operation may involve private or sensitive data. Ensure consent."
    profile: default
    keyword_patterns: ["personal", "private", "sensitive", "credential", "password"]

  - name: mass_mutation
    description: Flag bulk write operations
    action: tag
    severity: 0.4
    explain: "Bulk mutations detected. Verify scope is intentional."
    profile: default
    keyword_patterns: ["batch", "bulk", "mass", "all"]
    safety_levels: ["WRITE"]
```

### 8.2 Secure Profile

```yaml
extends: "default"

rules:
  - name: network_egress
    description: Deny any network call unless explicitly allowlisted
    action: block
    severity: 0.9
    explain: "Network egress denied in secure profile. Add explicit allowlist rule if needed."
    profile: secure
    tool_patterns: ["http_*", "fetch_*", "download_*", "upload_*"]

  - name: destructive_operation
    description: Block destructive operations without human approval
    action: block
    severity: 0.95
    explain: "Destructive operation blocked in secure profile. Use dry_run first."
    profile: secure
    safety_levels: ["DELETE", "DROP", "TRUNCATE"]
```

### 8.3 Violet (Paranoid) Profile

```yaml
extends: "secure"

rules:
  - name: default_deny
    description: Block any action not explicitly allowlisted
    action: block
    severity: 1.0
    explain: "Violet profile: default-deny. No matching allowlist rule found."
    profile: violet
    # This rule has no patterns — it acts as a catch-all when no other rule matches
```

---

## 9. Integration Points

### 9.1 Tool Dispatch Gate

Every tool call in WhiteMagic passes through `evaluate_ethics` before execution:

```python
from whitemagic.dharma.rules import get_rules_engine

engine = get_rules_engine()
decision = engine.evaluate(action_dict, profile="default")

if decision.action == DharmaAction.BLOCK:
    return {"status": "blocked", "reason": decision.explain}
```

### 9.2 MCP Server Exposure

Dharma tools are exposed via MCP so any compatible client (Claude, Cursor, Cline) can query governance state:

- `evaluate_ethics` — evaluate an action
- `check_boundaries` — check if action violates boundaries
- `get_ethical_score` — get aggregate ethical score
- `dharma_rules` — list active rules
- `set_dharma_profile` — switch profile

### 9.3 Karma Ledger Hook

Every decision is automatically recorded in the Karma Ledger for forensic reconstruction.

---

## 10. Citation

```bibtex
@misc{whitemagic2026dharma,
  title={WhiteMagic Dharma Specification v0.1.0: Declarative local-first governance for agentic AI},
  author={{WhiteMagic Labs}},
  year={2026},
  month={jun},
  howpublished={\url{https://whitemagic.ai/docs/dharma-spec}},
  note={MIT-licensed YAML policy engine with Karmic trace and Karma Ledger}
}
```

---

*Specification version 0.1.0 — June 8, 2026*  
*For questions or implementation review: contact via WhiteMagic Labs channels*
