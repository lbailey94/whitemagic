# Wave-2 spec 06 — RSI over journal

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** RSI over journal (wave plan §3; **link** · E20).
**Wire:** `think` over the journal; **proposal ≠ verification**.
**Nucleus touch points:** N5 (audit discipline, raw + adjudicated), Part 1 invariant 9
(evidence/belief/speculation distinct); canon §5 ("operate on evidence, never self-certify").
**Caution carried:** Gen2's RSI resolution is **caller-asserted** (no independent verification;
relog-regression only) and the loop is **excluded from the curated profile** — a migration must
not claim "verified" in the tested sense (divergence W2-4).
**Corrections carried:** G-26 — `whitemagic_dream.log` carries **361 CORRECT lines**; qualify
"never CORRECT" by artifact. The ledger phrasing "906 → 36 → 29" reads healthy but the ratios are
coverage 4.0 %, success 2/36 (one event), correlations 1/29 nonzero (errata W2-6).

---

## 1. Frozen behavioral spec

### 1.1 The issue series lives in the journal

- Issues (friction-class) are **journal-observable series** with stable identity; regression
  detection = relog of the same hashed issue escalates (Gen2 reference:
  `friction.log`, content-hash dedup, `is_resolved`/`escalate_severity`
  `rsi.rs:99-151,196`; SOURCE-IMPLEMENTED + live). The Gen2 store is memory-ledger-backed
  (Codex + Telemetry) and outside curated — the link states its scope honestly; the journal is
  the Gen3 instrument (N4).
- **Stable pattern identity is required:** cluster/count-shaped ids shift across cycles (v26
  `0.0_-0.1` vs `-0.0_-0.1`); without stable identity, outcomes are noise and cross-cycle
  comparisons are invalid.

### 1.2 Maker ≠ checker (the core law)

- Success is declared **only via a witness independent of the proposing organ.** The v26 class —
  `verify_outcome` re-running the same `analyze()`, scoring success as proposal *disappearance*
  (delta 1.0 when absent) — is **excluded** (self-certification at mechanism level, against
  canon §5).
- **Disappearance ≠ success:** detector retirement is not remediation; **threshold motion as
  fix** is not remediation (count checks that "succeed" by moving the detector are excluded).
- Resolution events carry **independent verification**: a verified resolution names its
  verifying instrument/event; caller-asserted resolutions are stored **labeled asserted** — never
  promoted to "verified" (taxonomy: asserted | verified; N5 reporting keeps both).

### 1.3 Execution claims require execution

- No auto-fix claim without executed, measured evidence: the v26 path was structurally dead
  (method strings vs a closed 9-verb vocabulary → "Unknown action"; observations.jsonl fossil).
  A proposal is a proposal; only a measured post-state change is a fix.
- Proposals are **review-gated** (`requires_human_review: true` class; Gen2 reference) and
  journaled.

### 1.4 Constants and provenance

- Optimizer-style outputs (possibility winners class) must carry provenance and **never silently
  replace declared values**; a resumed target (energy/ratios class) is a proposal until its
  outcome is verified. Silent constant replacement is excluded.

### 1.5 Statutory parameters named (Tier-2)

Issue identity scheme (hash + stable cluster ids) · escalation rule · proposal review gate ·
severity ladder (if any). Nothing benchmark-derived.

### 1.6 Non-goals

No self-certification · no disappearance-as-success · no caller-asserted resolutions presented
as verified · no silent constant replacement · no auto-fix claims without execution · no
"healthy loop" framing (ratios published).

---

## 2. Selection history

**Ancestor (Gen1 v26):** `autodidactic_loop`/`recursive_loop`/`kaizen_engine` —
`feedback.db` fossil: **906 applications · 36 outcomes (4.0 % coverage) · 29 correlations (1
nonzero)**; success **2/36** and both are **one event seen twice** (`untitled` 155→72 and 95→72,
`auto_verified: true`); 34 honest failures; confidence decay on failures; `_95`↔`_155` = 1.0
(n=2). Auto-fix write path structurally dead. Homeostat: 55 `harmony/` rows all READ — but
`whitemagic_dream.log` carries 361 CORRECT lines (G-26). Possibility winners = self-scored
optimizer overwriting boot constants, no outcome verification. Identity proposals: 103/103
`execution_tool: null`.

**Selection fate:** E20 PRESERVE IMPL. → link — the spiral shape + regression detection are
inherited; Gen2 carries it distributed and outside curated; resolutions remain caller-asserted.
Lineage note: the explicit pattern-correlation matrix was **not ported** (candidate V8 analytics,
not owed for alpha).

**Evidence levels:** v26 ratios MEASURED (generated from `feedback.db`); self-cert mechanism
SOURCE-IMPLEMENTED; auto-fix dead STATICALLY-REACHABLE + fossil evidence; Gen2 loop live
(SOURCE-IMPLEMENTED; verification independence UNVERIFIED); Gen3 target NAMED (journal +
independent witness).

---

## 3. Adversarial cases

1. **Self-certification** — proposer and verifier share an organ → fail; the witness must be
   independent (cross-instrument).
2. **Disappearance-as-success** — a retired detector may not score success.
3. **Threshold motion** — moving a boundary is not a fix.
4. **Unstable identity** — shifting cluster ids make outcomes noise; identity must be stable or
   outcomes invalid.
5. **Caller-asserted resolution** — labeled asserted, never "verified".
6. **Silent constant replacement** — optimizer outputs need provenance; declared values change
   only via their own registration.
7. **Un-executed fixes** — "Unknown action"-class claims fail; only measured post-states count.
8. **Reporting honesty** — coverage/success/correlation ratios accompany any loop citation (N5);
   "never CORRECT" is qualified by artifact (G-26).
9. **Profile scope** — the link states that the Gen2 loop is excluded from curated (no
   verified-loop claim smuggled through the curated surface).

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Auto-verification (v26) | self-reported outcomes; the 2 "wins" are count changes | outcomes drop to 0 → signal was 100 % self-reported | EFFECTFUL |
| Cross-instrument verification (minimal fair trial) | independent witness required | unverified proposals stay proposals | RE-ENTERS |
| Loop on known-defect corpus | no retrieval/ordering change expected (gate, not scorer) | baseline | — (negative control) |
| Optimizer targets file (winners class) | overridden constants | declared defaults return; if nothing measurable changes → decoration | EFFECTFUL |

No inert passengers: a loop citation without coverage/success ratios is rejected.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Independent witness** — verified resolution names its instrument; asserted vs verified
   labeled.
2. **Disappearance guard** — absent-proposal scoring impossible.
3. **Identity stability** — cross-cycle comparisons assert stable ids.
4. **Execution evidence** — post-state measurement for any fix claim.
5. **Ratios published** — coverage/success/correlation counts generated from the ledger.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_06_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
