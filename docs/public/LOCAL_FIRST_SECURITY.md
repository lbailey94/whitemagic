# Local-First Security Model

**Date**: 2026-06-08  
**Version**: 1.0.0  
**Status**: Draft for review  
**Audience**: Security auditors, air-gapped operators, single-tenant deployers, research practitioners

---

## The Core Thesis

> **Not every agent needs cloud governance. Some need to run offline, air-gapped, on-device, or under operator control without external dependencies.**

WhiteMagic's security model is intentionally different from enterprise cloud governance (Microsoft AGT, Anthropic Managed Agents, Cloudflare Workers). We optimize for a threat model where **insider risk and operator control** matter more than external attacker surface.

This document explains:
1. Why local-first is a legitimate security paradigm
2. How WhiteMagic's threat model differs from cloud governance
3. When to choose local-first vs. cloud-first
4. What protections exist and what gaps remain

---

## 1. What "Local-First" Means

| Dimension | Local-First (WhiteMagic) | Cloud-First (AGT/Anthropic/Cloudflare) |
|-----------|-------------------------|----------------------------------------|
| **Network** | No network required | Network is assumed |
| **Identity** | Implicit (single operator) | Explicit (DID, Entra, OAuth) |
| **Data** | Never leaves the machine | Stored/processed in cloud |
| **Updates** | Operator-controlled | Vendor-controlled |
| **Compliance** | Operator responsibility | Vendor certifications (SOC 2, HIPAA) |
| **Threat focus** | Insider risk, physical access | External attacker, lateral movement |
| **Audit** | Local Karma Ledger | Cloud-backed telemetry |

**Local-first is not "less secure." It is "secure against different threats."**

---

## 2. Threat Model

### Assumptions

1. The operator is trusted (or at least, the system serves the operator's interests)
2. The machine is physically controlled by the operator
3. Network connectivity is optional, intermittent, or explicitly denied
4. The primary adversary is software malfunction, not external intrusion

### In-scope threats

| Threat | WhiteMagic Defense |
|--------|-------------------|
| Agent goes rogue (self-modification, tool misuse) | Dharma rules engine, 5-tier Shelter isolation, kill switch |
| Undeclared side effects (READ tool writes data) | Karma Ledger declared-vs-actual tracking |
| Audit tampering | Ed25519-signed entries, Merkle hash chain |
| Privilege escalation | Default-deny tool dispatch, capability-based Shelter tiers |
| Prompt injection in tool outputs | Input sanitizer (PRAT dispatch layer) |
| Memory poisoning / stale data | Galactic memory lifecycle, dream-cycle consolidation |

### Out-of-scope threats (by design)

| Threat | Why Out-of-Scope |
|--------|-----------------|
| Multi-tenant isolation | Single-tenant by design |
| Cloud-based DDoS | No cloud exposure |
| OAuth token theft | No OAuth |
| Cross-agent identity spoofing | No agent identity layer (yet) |
| External MCP server poisoning | No external MCP server consumption (yet) |

---

## 3. Security Controls

### 3.1 Dharma Rules Engine

Declarative policy engine with 14+ built-in rules across 4 profiles:

- **default**: Balanced (blocks surveillance, harm, cognitive capture; warns on privacy, external reach)
- **creative**: Relaxed (allows writes, logs only)
- **secure**: Strict (blocks all writes and external access)
- **violet**: Purple-team (blocks offensive security without engagement tokens; logs defensive ops)

Rules are evaluated on every tool call. Hot-reload supported. Karmic trace captures every decision.

### 3.2 Shelter Isolation (5 Tiers)

| Tier | Authority | Use Case |
|------|-----------|----------|
| 0 Sandbox | No network, no filesystem | Untrusted code, generated scripts |
| 1 Restricted | Read-only workspace | Analysis, read-only tools |
| 2 Standard | Read/write workspace | Normal agent operations |
| 3 Privileged | Network access | External API calls (if enabled) |
| 4 Admin | Full system access | Operator override |

Default for untrusted code: Tier 0. No ambient authority.

### 3.3 Karma Ledger

Append-only, cryptographically signed audit trail:

- Every tool call recorded with declared safety vs. actual side effects
- Ed25519 signatures on every entry (auto-generated keypair per state root)
- Merkle hash chain for tamper evidence
- Dual-log support for Edgerunner Violet ops classification (red-ops / blue-ops)
- XRPL anchoring optional (testnet/mainnet)

### 3.4 Voice Audit

Behavioral consistency checking across sessions:

- Detects anomalous behavioral patterns
- Chain-of-thought replay for auditor inspection
- Cross-session personality drift detection

### 3.5 Vectorized Language (PRAT)

Tool call compression that reduces token exposure:

- 75.5% average compression ratio
- Reduces attack surface by minimizing plaintext tool descriptions in context
- Symbolic encoding prevents injection via tool name manipulation

---

## 4. Comparison to Cloud-First Governance

### When to choose WhiteMagic (local-first)

- Air-gapped or classified environments
- Personal AI assistants on local hardware
- Research environments where data must not leave the lab
- Offline-first field deployments
- Operators who distrust vendor cloud access
- Compliance regimes requiring on-premise audit trails

### When to choose Microsoft AGT / Anthropic / Cloudflare (cloud-first)

- Enterprise multi-tenant deployments
- Scenarios requiring SOC 2 / HIPAA / EU AI Act compliance
- Teams needing 9,500+ conformance tests and continuous fuzzing
- Organizations with Azure/Cloudflare existing infrastructure
- Use cases requiring managed agent lifecycle (billing, SLA, support)

### Hybrid: Using Both

WhiteMagic and AGT are complementary, not substitutes:

- **WhiteMagic for local reasoning**: Offline, air-gapped, operator-controlled
- **AGT for cloud governance**: Multi-tenant, compliance-mapped, enterprise-managed
- **Anthropic for managed agents**: High-capability, managed lifecycle, dreaming
- **Cloudflare for edge execution**: Sub-second cold starts, global distribution

A future `whitemagic-dharma-agt-bridge` could translate AGT YAML policies into Dharma rules for unified policy management.

---

## 5. Honest Assessment of Gaps

### Gaps we acknowledge

| Gap | Severity | Path Forward |
|-----|----------|-------------|
| No DID-based identity | Medium | Add minimal pseudonymous identity for multi-agent mesh |
| No `McpSecurityScanner` equivalent | Medium | Add lightweight tool-poisoning detector to PRAT dispatch |
| No output path hardening | Medium | Integrate `voice_audit.scan` into tool response pipeline |
| No shadow server registry | Low | Add allow-list for external MCP servers |
| No replay protection | Low | Add nonce tracking to Karma Ledger |
| No key rotation | Low | Support multiple key IDs in `verify_chain()` |
| No formal compliance mapping | Medium | Self-assess against NSA, OWASP, EU AI Act |

### Gaps we do not consider bugs

| "Gap" | Why It's Intentional |
|-------|---------------------|
| No network identity | Local-first assumption: network is optional |
| No TLS enforcement | No network transport in core |
| No cross-language SDK | Python primary; polyglot is research, not production |
| No hosted service | Not a SaaS; operator hosts themselves |

---

## 6. Verification

### How to audit a WhiteMagic deployment

```bash
# 1. Verify Dharma rules are loaded
python -c "from whitemagic.dharma.rules import get_rules_engine; print(len(get_rules_engine().get_rules()))"

# 2. Verify Karma Ledger chain integrity
python -c "from whitemagic.dharma.karma_ledger import get_karma_ledger; print(get_karma_ledger().verify_chain())"

# 3. Verify Ed25519 signing is active
python -c "from whitemagic.security.audit_signing import get_audit_signer; print(get_audit_signer().is_available())"

# 4. Run adversarial test suite
pytest core/tests/unit/test_agentdojo_adversarial.py -v

# 5. Check for hardcoded paths
python core/scripts/check_ship.py
```

### Expected results on a healthy deployment

- Dharma rules: 14+ rules loaded
- Karma chain: `valid=True`, `signatures_verified > 0`
- Audit signer: `True` (cryptography library installed)
- Adversarial tests: 24/24 passed
- Ship check: No violations

---

## 7. Conclusion

WhiteMagic's security model is **local-first by design**, not local-first by accident. The absence of cloud identity, TLS, and multi-tenancy is a feature for operators who need to run agents offline, air-gapped, or under explicit personal control.

The model is validated by:
- 2,447 passing tests (including 24 adversarial defense scenarios)
- Ed25519-signed append-only audit trails
- 5-tier capability-based isolation
- Declarative policy engine with semantic rule evaluation

It is not a substitute for enterprise cloud governance. It is an alternative for practitioners who need governance without the cloud.

---

*Last updated: 2026-06-08*  
*Verification command: `pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q`*
