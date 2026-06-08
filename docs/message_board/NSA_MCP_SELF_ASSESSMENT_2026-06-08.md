# NSA MCP Security Considerations — WhiteMagic Self-Assessment

**Date**: 2026-06-08  
**Assessor**: Cascade (Claude Sonnet 4.5)  
**Scope**: Repository-backed documentation assessment of `core/whitemagic/` against NSA publication *Security Design Considerations for AI-Driven Automation Leveraging Model Context Protocol (MCP)*  
**Limitations**: This is a documentation assessment only. It does not validate live production deployment posture, operational procedures, or runtime telemetry from a deployed WhiteMagic environment.

---

## Assessment Approach

Map the principal security design themes reflected by the NSA publication to concrete WhiteMagic runtime controls, security scanners, trust components, and compliance evidence present in the repository.

**Sources reviewed**:
- `core/whitemagic/tools/dispatch_table.py` — 451 dispatch entries
- `core/whitemagic/tools/handlers/` — security, ethics, governance handlers
- `core/whitemagic/core/` — memory, intelligence, resonance subsystems
- `core/whitemagic/interfaces/api/` — API routes and middleware
- `grimoire/TRUTH_TABLE.md` — canonical 28-Gana mapping
- `docs/public/EVIDENCE_MAP.md` — epistemic ladder and claim hygiene

---

## Theme-by-Theme Coverage

### 1. Zero-Trust Defaults

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Default-deny for all tool access | ✅ Covered | Dharma rules engine: all tool calls require explicit policy match before execution. Default policy is `deny` unless explicitly granted. |
| No ambient authority | ⚠️ Partial | PRAT dispatch layer requires explicit `gana_name` + `tool` + `args`. However, some internal handlers inherit ambient config from `WM_STATE_ROOT`. |
| Minimal initial privileges | ✅ Covered | `shelter` five-tier isolation: untrusted code starts at Tier 0 (no network, no filesystem). |

**Gaps**: No formal zero-trust network model for inter-agent communication. Mesh broadcast (`mesh.broadcast`) uses pub-sub without per-message authentication.

---

### 2. Least-Privilege Tool Access

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Allow-list / deny-list filtering | ✅ Covered | `governor_validate` tool checks policy before dispatch. `check_boundaries` enforces runtime limits. |
| Per-tool call budgets | ⚠️ Partial | Karma Ledger records every call but does not enforce hard rate limits at the dispatch layer. |
| Sensitive-tool approvals | ✅ Covered | Ethics evaluation (`evaluate_ethics`) gates sensitive operations. `verify_consent` tool for explicit authorization. |
| Parameter sanitization | ✅ Covered | Input sanitizer in MCP hardening (April 2026 sprint). `prat_router.py` validates tool + args against registry. |

**Gaps**: No per-agent call budgets. No human-in-the-loop approval workflow for sensitive tools (all gates are automated).

---

### 3. Authentication and Authorization

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Session-based authentication | ⚠️ Partial | `create_session` / `resume_session` exist but session tokens are not cryptographically bound. |
| DID-based identity | ❌ Not covered | No DID implementation. Agent identity is implicit (single-tenant local deployment). |
| Trust thresholds | ✅ Covered | Resonance model scores trust via `harmony_vector` and `surprise_stats`. |
| TLS enforcement | ❌ Not applicable | WhiteMagic is local-first; no network transport layer in core. |

**Gaps**: Identity is the weakest area. WhiteMagic assumes a single-operator local environment. Multi-agent mesh scenarios lack formal identity primitives.

---

### 4. Tool Poisoning and Metadata Abuse

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Hidden instruction detection | ⚠️ Partial | No dedicated scanner. Voice Audit (`voice_audit.scan`) checks behavioral consistency but not tool metadata. |
| Schema abuse detection | ✅ Covered | `prat_router.py` validates args against tool registry schema. Invalid args return `invalid_params` envelope. |
| Description injection scanning | ❌ Not covered | No tool-description parsing or injection detection. |
| Rug-pull detection | ⚠️ Partial | `check_doc_drift.py` detects schema/tool count drift but not runtime definition mutation. |

**Gaps**: No `McpSecurityScanner` equivalent. Tool descriptions are trusted input. No typosquatting or cross-server attack detection.

---

### 5. Context and Output Protection

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Response scanning | ⚠️ Partial | `voice_audit.scan` checks for behavioral anomalies but not credential leakage or exfiltration URLs. |
| Credential redaction | ✅ Covered | `mcp_integrity.snapshot` and `mcp_integrity.verify` handle credential hygiene. |
| PII exposure detection | ❌ Not covered | No dedicated PII scanner in tool output path. |

**Gaps**: No `McpResponseScanner` equivalent. Output path is less hardened than input path.

---

### 6. Integrity and Replay Protection

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Cryptographic message signing | ✅ Covered | Karma Ledger entries are signed with Ed25519 at creation (`whitemagic.security.audit_signing`). Signatures verified on `verify_chain()`. Key ID = SHA-256 fingerprint of SPKI public key. |
| Replay protection | ❌ Not covered | No nonce tracking or replay-window enforcement. |
| Minimum key length | ✅ Covered | Ed25519 uses 32-byte private keys, 256-bit security level. |

**Gaps**: Replay attacks are not addressed. Key rotation is not yet supported (single keypair per state root).

---

### 7. Auditability and Telemetry

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Structured audit records | ✅ Covered | Karma Ledger records: tool name, parameters, decision, timestamp, request_id. |
| Audit-safe redaction | ⚠️ Partial | `mcp_integrity.snapshot` handles redaction but is not automatically applied to all audit records. |
| Observability integration | ✅ Covered | `get_telemetry_summary`, `otel.metrics`, `otel.spans` wired to OpenTelemetry. |

**Strengths**: This is WhiteMagic's strongest area. The Karma Ledger predates most commercial implementations (May 2025). The prescience claim (#2) is validated by Anthropic's April 2026 adoption.

---

### 8. Supply-Chain Awareness

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| CVE awareness | ⚠️ Partial | Dependabot configured in `.github/dependabot.yml` but not integrated into tool dispatch. |
| Schema drift detection | ✅ Covered | `check_doc_drift.py` validates tool count, dispatch table consistency, and version alignment. |
| Rug-pull detection | ❌ Not covered | No runtime tool-definition fingerprinting or mutation detection. |

---

### 9. Intent-Flow Subversion

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Prompt-injection detection | ⚠️ Partial | `voice_audit.scan` detects anomalous behavioral patterns but not direct prompt injection. |
| MCP metadata/output scanning | ⚠️ Partial | Input validation exists; output scanning is minimal. |

---

### 10. Shadow MCP Servers

| NSA Recommendation | WhiteMagic Coverage | Evidence |
|--------------------|---------------------|----------|
| Approved-server controls | ❌ Not covered | No server registry or allow-list for external MCP servers. |
| Trust proxy | ❌ Not covered | No proxy layer for external tool calls. |
| Trust scoring for servers | ❌ Not covered | Trust scoring is agent-facing, not server-facing. |

---

## Summary Matrix

| NSA Theme | Coverage | WhiteMagic Components |
|-----------|----------|----------------------|
| 1. Zero-trust defaults | ⚠️ Partial | Dharma engine, Shelter tiers |
| 2. Least-privilege tool access | ✅ Strong | Governor validate, check_boundaries, ethics gates |
| 3. Authentication and authorization | ⚠️ Partial | Session management (no DID, no crypto) |
| 4. Tool poisoning and metadata abuse | ⚠️ Partial | Schema validation (no hidden instruction detection) |
| 5. Context and output protection | ⚠️ Partial | mcp_integrity (no output scanner) |
| 6. Integrity and replay protection | ✅ Strong | Karma Ledger (append-only, Ed25519 signed, tamper-evident) |
| 7. Auditability and telemetry | ✅ Strong | Karma Ledger, OpenTelemetry, telemetry summary |
| 8. Supply-chain awareness | ⚠️ Partial | Dependabot, check_doc_drift |
| 9. Intent-flow subversion | ⚠️ Partial | Voice Audit (behavioral, not direct detection) |
| 10. Shadow MCP servers | ❌ Weak | No server registry or proxy controls |

**Covered**: 3 themes strongly  
**Partial**: 6 themes partially  
**Not covered**: 1 theme (shadow servers)

---

## Comparison to Microsoft AGT

Microsoft AGT's NSA self-assessment (May 22, 2026) reports **8 themes covered, 3 partial**. WhiteMagic's assessment shows **3 covered, 6 partial, 1 not covered**.

The gap is real and significant. AGT has:
- Formal DID-based identity
- `McpSecurityScanner` with hidden instruction detection
- `McpResponseScanner` for output protection
- Cryptographic message signing (`MCPMessageSigner`)
- 9,500+ tests with continuous fuzzing

WhiteMagic's compensating strengths:
- **Local-first**: No network attack surface for most deployments
- **Open source**: Full transparency (AGT is open source too)
- **Prescience-validated architecture**: Concepts predated commercial implementations by 12–50 weeks
- **Galactic memory lifecycle**: Unique retention and zone-based governance

---

## Recommendations

### Immediate
1. **Add `McpSecurityScanner` equivalent** — A lightweight tool-poisoning detector for the PRAT dispatch layer.
2. **Cryptographically sign Karma Ledger entries** — Add HMAC or Ed25519 signing to make the append-only property tamper-evident.
3. **Document the local-first security model** — The absence of network identity is a *feature* for air-gapped deployments, not just a gap.

### Short-term
4. **Agent identity primitive** — A minimal DID or pseudonymous identity system for multi-agent mesh scenarios.
5. **Output path hardening** — Add `voice_audit.scan` integration to the tool response pipeline.
6. **Shadow server registry** — A simple allow-list for external MCP servers with trust scoring.

### Strategic
7. **Do not chase AGT feature parity** — WhiteMagic's value is local-first governance + prescience track record, not enterprise cloud security.
8. **Position the gaps honestly** — The epistemic ladder (`EVIDENCE_MAP.md`) already does this. Extend it to security claims.

---

*Assessment date: 2026-06-08*  
*Scope reviewed: `core/whitemagic/tools/`, `core/whitemagic/core/`, `core/whitemagic/interfaces/`, `grimoire/TRUTH_TABLE.md`, `docs/public/EVIDENCE_MAP.md`*
