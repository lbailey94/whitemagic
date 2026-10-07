# Wave-2 spec 02 — Retention / lifecycle

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Retention/lifecycle (wave plan §3; **link** (Gen2) · E5).
**Wire:** statutory selection; fixed `persistent` in Gen3 until earned.
**Nucleus touch points:** Part 1 invariant 2 (rotation, not deletion); Part 3 horizons (import
tier fixed `persistent`); E5.
**Caution carried:** **retention ≠ lifecycle** — the gentle `RetentionEngine` (decay-only,
dream-wired) and the delete-capable `LifecycleManager::forget` (no callers) are **two organs**;
the link must name the organ. **Do not re-raise:** errata W2-2 (divergence recorded); DO_NOT_MIGRATE
#21 (`forget` delete path unwired).

---

## 1. Frozen behavioral spec

### 1.1 The two organs, named separately

- **RetentionEngine (the link):** 7 signals averaged; thresholds retain 0.35 / decay 0.15; the
  sweep **only decays importance** (×0.5/×0.8) — it never deletes (`retention.rs:70-71,110,
  294,317-323`; SOURCE-IMPLEMENTED + dream-wired).
- **`LifecycleManager::forget` (a different organ, not part of this link):** delete-capable via
  `store.delete`; **unwired** (no callers outside `wm-memory`); excluded until its own
  registration (DO_NOT_MIGRATE #21). Never silently deleted.
- Gen3 keeps the import tier fixed **`persistent`**; replacement is unearned (horizons, E5).

### 1.2 Forgetting is propose-and-review

- The only shipped prune path returns **proposals** with `requires_human_review: true` and writes
  a cycle record — nothing is purged (`retention.prune`, `autonomous.rs:306-390`).
- Cold rotation is the non-destructive tier: records are hash-verified, de-indexed, and return by
  explicit thaw or unranked navigation (`no_thaw` reads; integrity `verified`; floors disclosed
  as `not_applicable_unscored_recovery`).

### 1.3 Uniform object-type policy

- v26 hard-DELETEd association edges while memory rows survived — **rotation-not-deletion was not
  uniform across object types** (`W2_retention_lifecycle.md`). The successor states one policy
  per object type (rows, edges, state records) and no type may be purged silently.

### 1.4 Selection is statutory

- Thresholds (retain/decay; any archive line) are **Tier-2 settings, named and versioned** — no
  swept values, no benchmark-derived lines.

### 1.5 Evidence and disclosure

- A decay sweep under starvation/refusal is typed as refused, never reported as "no proposals"
  (9.1.8 starvation-vs-refusal; the v26 all-zero "success" class is excluded).
- Cold/archived records disclose their state on retrieval (A2 owns the disclosure vocabulary;
  `unavailable_cold_record` is the template).

### 1.6 Non-goals

No delete path in the link · no automatic purge · no non-uniform object-type behavior · no
tuned thresholds · no claim that decay "improves" ordering without a measured effect.

---

## 2. Selection history

**Ancestor (Gen1 v26):** five signals (semantic 1.0 / recency 0.9 / emotional 0.8 / connection
0.7 / protection override), thresholds keep ≥0.35 / decay ≥0.15 / archive <0.15. The sweep was
**never armed automatically** (`attach()` had no caller); the persist path was **broken on the
shipped backend** (missing batch methods → archive verdicts raised; the manager returned all-zero
"success" — inert persistence). Rows were never deleted; edges were hard-deleted.

**Selection fate:** folded to Gen2 `retention.rs` — decay-only, dream-wired; the delete-capable
`lifecycle.rs` is dormant; cold rotation exists with integrity verification; the ratified row is
PRESERVE IMPL. → link, with `persistent` fixed in Gen3 until earned.

**Evidence levels:** v26 organs SOURCE-IMPLEMENTED; never-armed/broken-persist STATICALLY-
REACHABLE (documented, runtime UNVERIFIED); Gen2 engine live via dream (SOURCE-IMPLEMENTED +
wired), `Lifecycle` unwired (STATICALLY-REACHABLE absence); cold rotation live (W1 §8).

---

## 3. Adversarial cases

1. **All-zero "success"** — an archive/decay verdict that cannot be persisted must **raise
   loudly**, never aggregate to zeros and report success (the v26 class).
2. **Never-armed sweep** — scheduling is declared and attested (journal/N4), not assumed from
   code presence.
3. **Uniform object-type policy** — a fixture with rows + edges + state records: nothing is
   deleted; any edge lifecycle is proposed, not hard-executed.
4. **Propose-only** — no prune path executes without human review; the proposal is journaled.
5. **Threshold statutory** — thresholds come from Tier-2 settings; a swept value fails.
6. **Cold integrity** — cold records verify before return; a failed verification discloses.
7. **Starvation** — a refused sweep is typed refused, not "no proposals".
8. **Delete-path exclusion** — `forget`-class deletes have no callers; a re-entry requires its
   own registration + receipt.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Decay sweep (dream-wired) | strength distribution decays; survival measured | distribution flat | EFFECTFUL → PERSISTENT |
| Proposal surfacing (`retention.prune`) | proposals journaled | nothing changes in ordering (gate, not scorer) | EXECUTED |
| Cold rotation | cold set grows, hot set bounded | hot growth unbounded | PERSISTENT |

No inert passengers: the sweep's effect is measured; a decay that changes nothing is decoration.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Organ naming** — every artifact says RetentionEngine or Lifecycle::forget.
2. **Propose-only + journaling** — no silent purge; refusal typed.
3. **All-zero success impossible** — persist failure raises.
4. **Uniform policy** — object-type matrix asserted.
5. **Cold integrity** — hash-verified returns; disclosure on failure.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_02_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
