# Tactical Plan — Immediate & Short-Term Actions

**Date**: 2026-06-08  
**Source**: Competitive landscape analysis (Microsoft AGT v4, Anthropic Dreaming, Cloudflare Project Think) + internal state audit  
**Horizon**: Immediate (this week) + Short-term (2–4 weeks)

---

## Immediate Actions (This Week)

### I-1: Fix Exception Scan Baseline

**Context**: April 2026 scan found 1,188 `except Exception` blocks; 537 auto-fixed, 832 deferred. Current scan shows ~1,488 total (growth from new code in `agents/`, `_archived/`, `benchmarks/`). The "unknown" bucket (1,268) is the deferred manual review pile.

**Action**:
- Re-run `scripts/batch_fix_exceptions.py` on the categorized buckets (file_io: 26, import_error: 141, json: 9, network: 1, sqlite: 43) = **220 auto-fixable blocks**.
- Review the 1,268 "unknown" blocks: exclude `_archived/` and `tests/` from the count (they should not block production metrics).
- Update `AGENTS.md` baseline with the new clean count.

**Effort**: 1–2 hours  
**Owner**: Cascade  
**Gate**: Full test suite passes after fix.

---

### I-2: Update Prescience Claims with New Validations

**Context**: Three prescience claims have been overtaken by commercial releases. The claims need updating, not retraction — they were validated but the "still unique" framing is now false.

**Affected claims**:

| # | Claim | Old Framing | New Framing |
|---|-------|-------------|-------------|
| 7 | Dharma Engine / agent governance | "Still unique to WhiteMagic" | "Validated by Microsoft AGT v4 (May 2026); WhiteMagic remains local-first alternative" |
| 8 | PRAT token router compression | "Still unique to WhiteMagic" | "Validated by Microsoft AGT MCP Extensions (May 2026); WhiteMagic at 75.5% compression" |
| 9 | AI Dreaming / memory consolidation | "Still unique to WhiteMagic" | "Validated by Anthropic Dreaming (Apr 2026); WhiteMagic predated by 12 weeks" |

**Action**:
- Update `apps/site/lib/data/prescience.ts` (or desktop site equivalent).
- Update `docs/public/EVIDENCE_MAP.md` competitive positioning section.
- Add "Honest Miss" entries for claims that overstated uniqueness.

**Effort**: 30 minutes  
**Owner**: Cascade

---

### I-3: Publish Honest Competitive Positioning

**Context**: The June 5 positioning patch was internal. The external site (`whitemagic.dev` or `whitemagic-site/`) needs the same honesty.

**Action**:
- Update `/services/agent-governance` page: acknowledge AGT v4, position WhiteMagic as lightweight alternative.
- Update `/research` page: add Anthropic Dreaming and Cloudflare Project Think as validation events.
- Ensure no page claims "unsolved" or "unique" for concepts now shipped by major vendors.

**Effort**: 1 hour  
**Owner**: Cascade + Lucas (site deploy)

---

## Short-Term Actions (2–4 Weeks)

### S-1: AgentDojo Benchmark Integration

**Context**: The `WhiteMagicDharmaDefense` adapter is structurally sound (10/10 policy gates) but lacks a capable benchmark driver. OpenCode and Ollama were investigated and found insufficient.

**Options**:
1. **Use GPT-4o/Claude Sonnet via API** as the driver (requires API budget).
2. **Wait for OpenCode tool-schema support** (timeline unknown).
3. **Build a minimal driver** using `whitemagic/tools/` directly with scripted adversarial prompts.

**Recommended**: Option 3 for immediate empirical credibility. Build a 20-scenario adversarial test suite that exercises all 10 policy gates with known-bad inputs.

**Deliverable**: `tests/integration/test_agentdojo_defense.py` with 20 scenarios, 100% gate coverage.

**Effort**: 4–6 hours  
**Owner**: Cascade  
**Gate**: All scenarios pass; results documented in `docs/message_board/`.

---

### S-2: Cryptographic Karma Ledger Signing

**Context**: NSA MCP self-assessment identified Karma Ledger as strong on auditability but weak on cryptographic integrity. Microsoft AGT has `MCPMessageSigner` with HMAC and 32-byte key floor.

**Approach**:
- Add Ed25519 signing to `karma_record` and `karma_anchor` tools.
- Sign each ledger entry with a per-session key derived from `WM_STATE_ROOT`.
- Store signature alongside entry; verify on `karma.verify_anchor`.

**Deliverable**: `karma.anchor` and `karma.verify_anchor` return `{..., "signature": "base64", "algorithm": "Ed25519"}`.

**Effort**: 3–4 hours  
**Owner**: Cascade  
**Gate**: `test_karma_signing.py` with roundtrip verification and tamper detection.

---

### S-3: Document the Local-First Security Model

**Context**: WhiteMagic's lack of network identity is a *feature* for air-gapped, single-tenant, or offline deployments. This is not a gap — it's a different threat model.

**Deliverable**: `docs/public/LOCAL_FIRST_SECURITY.md` explaining:
- Why no DID / no TLS is intentional for local deployments
- Threat model: insider risk > external attacker
- Comparison to cloud-first governance (AGT) and when to choose each

**Effort**: 2 hours  
**Owner**: Lucas (with Cascade drafting)

---

### S-4: Update 30-Objectives Plan

**Context**: `30_OBJECTIVES_PLAN.md` (May 16) shows 23/29 complete (79%). The competitive landscape shift means some objectives need re-scoping.

**Revisions needed**:
- Obj 19 (Aria persona spec): Still blocked — but now lower priority given commercial alternatives.
- Obj 23 (epistemic ladder UI): Higher priority — honest competitive framing is now the differentiator.
- Obj 26 (MandalaOS v0.1 spec): Re-scope as "local-first governance substrate" not "novel governance OS."

**Effort**: 1 hour  
**Owner**: Cascade

---

## Verification Gates

| Gate | Command | Target |
|------|---------|--------|
| Full CI | `pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q` | 2,423 passed, 0 failed |
| Doc drift | `python scripts/check_doc_drift.py` | 9/9 passed |
| Versions | `python scripts/check_versions.py` | Pass |
| Prescience data | `npm run check-data` (desktop site) | All passed |
| Exception count | `python scripts/scan_exception_patterns.py` | < 1,200 unknown (post-cleanup) |

---

*Last updated: 2026-06-08*
