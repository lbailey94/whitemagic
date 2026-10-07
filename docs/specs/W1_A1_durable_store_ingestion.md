# Wave-1 spec A1 — Durable store + ingestion gate

**Status: FROZEN rev 1 (2026-09-17, sha256 `cf638395…`) · rev 2 amendment drafted 2026-09-17
(noise disposition — pending operator ratification).** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 (cross-cutting spec template) at WMgen3 tip `b7565ee` (tree clean), under the frozen nucleus
(`docs/NUCLEUS.md`, sha256 `73c5a9cf…`). **Owner: Lucas Bailey (operator)** — assigned at
ratification. Rev 2 is additive to rev 1 and takes effect at operator ratification +
`receipts/W1_SPEC_A1_AMEND_<date>.md`. Docs-only: no code, no gates, no verdicts, no thresholds.

**Row:** Durable store + ingestion gate (wave plan §2 row 1; two decomposition rows: Durable store
`CLEANLY → compile · E1` and Ingestion gates `CLEANLY → compile · E9`).
**Wire (Gen3 expression):** `remember` contract + journal refusals; exact-hash gate candidate;
near-dup only with declared battery; quarantine-not-purge.
**Nucleus touch points:** N1 (durable records + provenance chains); Part 1 invariants 2 (rotation,
not deletion; quarantine, not destroy), 3 (provenance on every durable record), 8 (evidence domains
immutable), 9 (durability ≠ truth); Part 3 statutes (fail-closed budgets; import tier fixed
`persistent`).
**Caution carried (wave plan):** the journal `duplicate_exact` vocabulary is **owned by this
spec**; Gen2 dedup is a non-journaled short-circuit — the spec must say which side discloses.
**Do not re-raise:** errata A#3 (0.85 is tag-set Jaccard, not embedding cosine); errata #23 (37.2 %
dup applies to the migration/live-store inventory, not codex — codex exact dup 0.05 %).

---

## 1. Frozen behavioral spec

Observable behavior, inputs/outputs, journal events, statutory parameters named (Tier-2). Nothing
benchmark-derived.

### 1.1 Intake contract

- **Input:** items of `RememberItem { content, source, kind }` with `kind ∈ {Reported, System,
  Simulated}` (`crates/wm-gen3-core/src/ops.rs:79-90`). (SOURCE-IMPLEMENTED)
- **Domain immutability:** the evidence domain is set at intake and never changes afterwards
  (Part 1 invariant 8): testimony stays `reported`, simulations stay `simulated`, system logs stay
  `system`. Re-labelling is a new record, never an edit of an existing one. (Constitutional)
- **Durability:** every accepted item yields a durable record with provenance (source label at
  minimum; result-granularity chain per N1) and a stable id; acceptance survives process restart.
- **Batch event:** exactly one `ingest.batch` journal event per `remember` call, carrying `items`,
  `written`, `ids_sha256` (`ops.rs:446-450`; canary C6 verb→event inventory: remember →
  `ingest.batch`). (RUNTIME-OBSERVED)

### 1.2 Refusal contract (fail-closed, journaled, never silent)

Every refused item is journaled as `remember.refusal` with a machine-readable reason; no item is
silently dropped, no partial write is reported as full success.

| Refusal | Reason token | State |
|---|---|---|
| Write budget exhausted (fail-closed) | `write budget exceeded (fail-closed)` | implemented (`ops.rs:412-417`; RUNTIME-OBSERVED) |
| Exact duplicate (the migration's gate) | `duplicate_exact` | implemented (`8c5e32f`); **owned by this spec** |
| Noise class (declared table, §1.3) | `noise_class` + `class` field | target — **rev 2** |
| Governance/starvation refusal | typed reason distinct from the above | target — 9.1.8 addition (delta §2.1, §2.4) |

### 1.3 The gate (target behavior)

- An item whose **identity key** is already present is refused with `remember.refusal` reason
  `duplicate_exact`; **no second record is written** and the existing record is not mutated by the
  refusal.
- **Identity key = (content SHA-256, `source`, `kind`)** — exact bytes plus declared provenance.
  The bytes alone are not identity: identical content from a different source/kind/context is a
  **distinct record** and remains admitted (context is the caller's provenance, not the bytes).
  Re-ingesting the same item from the same source is a no-op (Gen2 ingest-ledger contract
  template).
- **Scope:** the gate is per scope (galaxy/view label), not global. Cross-scope identical bytes are
  separate records unless a transfer is explicitly declared (E8 scope law).
- **Disclosure side (divergence #1, resolved here):** the **Gen3 journal is the disclosure
  surface**. The Gen2 `write_gate` silent short-circuit (dup_count bump, importance decay,
  `wm-dispatch/src/write_gate.rs:184-211`; W1 source map §1) is not the migrated behavior; if a
  Gen2 link sits in front of the journal path, it must surface the `duplicate_exact` refusal to the
  journal side or explicitly document that it absorbed the write **before** the journal — one side
  discloses, never neither.
- **Near-duplicates are out of scope.** No tuned similarity threshold may be imported (the
  0.85-class filter is tag-set Jaccard, not embedding cosine — errata A#3; benchmark-derived
  thresholds are DO_NOT_MIGRATE #10-class). Any semantic dedup re-enters only via a **declared
  battery + registration**.
- **Noise classes (rev 2 — disposition: refuse-with-journal).** Gen3 has **no quarantine organ**
  (no quarantined state, no lifecycle, no release); the permitted disposition is therefore the other
  half of the rev-1 rule: a typed journaled refusal. Declared class table (content-pattern,
  kind-independent, rule-based; changes are spec revisions, never runtime narration):

  1. `traceback` — content contains `Traceback (most recent call last):`;
  2. `error_line` — any line (after leading whitespace) begins with `Error:` or `Exception:`;
  3. `json_blob` — trimmed content begins with `{"json":` (the v26 raw-dump wrapper);
  4. `function_repr` — trimmed content begins with `<function `, contains ` at 0x`, ends with `>`;
  5. `too_short` — `content.trim()` length < 10 (declared constant, §1.4; v26 provenance).

  The refusal is emitted as `remember.refusal` with reason `noise_class`, the matched `class`, and
  the item's `content_sha256` + `source`; **no record is written** and the journal is the disclosure
  surface. Nothing is purged: a refusal prevents storage rather than destroying a stored record, and
  Gen3 exposes no delete path (Part 1 invariant 2; Charter §3.2 governs stored records).
  **Check precedence:** write budget → noise class → duplicate. The heuristic cost is disclosed and
  accepted by the operator: false positives block admission (including `kind = System` tracebacks).

### 1.4 Statutory parameters named (Tier-2, none swept)

- Write budget: fail-closed at the adaptive boundary (`ops.rs:357-364`; Charter §3.1).
- Import tier: fixed `persistent` (NUCLEUS §3 horizons; replacement unearned).
- The duplicate gate is rule-based (exact hash) — **no numeric parameter**.
- **Rev 2:** the noise table introduces exactly one declared constant — the `too_short` bound
  (`content.trim()` length < 10), inherited from the v26 noise classes; not tuned, not swept,
  changed only by a spec revision.

### 1.5 Journal events owned by this spec

`ingest.batch` · `remember.refusal` with reasons `write budget exceeded (fail-closed)`,
`duplicate_exact`, and `noise_class` (rev 2; the event carries `class` from the declared table plus
the refused item's `content_sha256` + `source`). Any new refusal reason must be added here first
(vocabulary is versioned with the spec, not narrated at runtime).

### 1.6 Non-goals

No near-dup semantics; no ranking effects (the gate is not a scorer); no Gen2 write-gate
absorption behavior; no retroactive cleanup of already-duplicated records (that would be a
destructive operation under its own registration); no changes to evidence-domain law.

---

## 2. Selection history

### 2.1 Ancestor (Gen1 v26)

`core/memory/deduplication.py` ("Campaign C001: Quarantine Rehabilitation") + per-backend
`content_hash` primitives (`find_by_content_hash`; postgres upsert; `galaxy_manager` cross-galaxy
hash skip; `sqlite_schema` `content_hash` since v14.1.1) + search-side near-dup filter
(`enable_dedup`, `dedup_threshold: 0.85` — tag-set Jaccard inside the Rust `search_similar` path
only).

### 2.2 Observed behavior

- Dedup was **cleanup, not a gate**: content SHA-256 existed as a column and in some backends, and
  duplicates were hunted post-hoc by a rehabilitation campaign (plus noise patterns, above).
- Result: the migration inventory found **59,831 rows / 35,930 distinct → 37.2 % internal dup**
  (matrix §2.1; errata #23 scopes this to the migration/live-store inventory — codex exact dup is
  0.05 %). Accumulation happened first; cleanup never finished.
- Near-duplicate search filtering existed at a tuned 0.85 threshold; exact-hash caching
  (`find_by_content_hash`) is the mechanical half.

### 2.3 Selection fate

- v26 cleanup campaigns **not inherited**.
- Gen2 turned idempotence into a property of the *path*: per-file SHA-256 ingest ledger (9.1.8
  onboarding), content-hash embedding cache, and `memory.deduplicate` as an explicit destructive
  operation instead of a background purge (Charter §3.2 rotation-not-deletion is the ruling the
  Gen1 purge campaigns lacked). Gen2 = capability source (W1 source map §1: write gate
  `write_gate.rs:103`, exact-hit short-circuit `:184-211`, ingest ledger `ingest.rs:9,454-498`).
- Gen3 fell to: `remember` contract + journal refusals (N1, E1, E9). The exact-hash gate is this
  spec's migration target; it is a **candidate**, not yet implemented.

### 2.4 Evidence-level register (per statement, protocol §3)

| Statement | Level |
|---|---|
| Gen1 dedup organs (files/symbols above) | SOURCE-IMPLEMENTED |
| Gen1 37.2 % dup figure (scoped per errata #23) | MEASURED (inventory; scope note applies) |
| Gen2 ingest ledger / write gate / dedup contract | SOURCE-IMPLEMENTED + RUNTIME-OBSERVED (status: live) |
| Gen3 `remember` / `ingest.batch` / budget refusal | SOURCE-IMPLEMENTED + RUNTIME-OBSERVED (C6) |
| Gen3 exact-hash gate | **NAMED** (target; not implemented) |

---

## 3. Adversarial cases

Each case must exist as a runnable acceptance assertion before the row exits; no inert passengers.

**From the 9.1.7 audit fix list (Tier 1 — `WMv9/docs/V9_1_7_SCOPE_2026-09-15.md`):**

1. **Store↔index drift (#5)** — a crash leaves the durable store populated while the derived index
   returns zero; the contract forbids "healthy" with drift: restart must yield coherent recall
   **or** explicit degraded disclosure.
2. **Atomic vs partial success (#6)** — a large item must produce one outcome: success or explicit
   `partial_success` with failure detail; never reported success while capture failed.
3. **Write-gate bounds (#4)** — out-of-range parameters are refused fail-closed via the shared
   parse helper (the `memory.update` bypass class). A clamp in place of a refusal is a defect.
4. **Installer sentinel class (#1)** — "never write with `>` over an existing file" becomes, here:
   a refused re-ingest must leave the store's existing bytes byte-identical (byte-preservation
   check over the file set).

**From the findings (row 1 battery):**

5. **Exact duplicate across scopes** — scope labels differ; decide per scope, not globally.
6. **Same content, different context/episode** — must **not** collapse; both records exist, each
   with its own provenance.
7. **Near-dup (paraphrase)** — a tuned threshold is banned; the case only validates that no
   implicit semantic dedup runs.
8. **Noise purge vs quarantine** — traceback-class input is refused/quarantined with a journal
   refusal; nothing is purged (Charter §3.2).

**From the 9.1.8 additions (delta §3.2):**

9. **Starvation-vs-refusal distinction** — a budget/starvation refusal (`WM_HOMEOSTASIS_FROZEN`
   class) is typed distinctly from `duplicate_exact`; reads stay open under starvation; a refusal
   is never counted as success.
10. **Strict-mode refusal** — a governance refusal under strict mode is a typed refusal with a
    reason (never a silent no-op).

---

## 4. Ablation

Disabling the mechanism must change a measured outcome; the journal is the instrument (rungs 4–8,
protocol §1).

**Mechanism ablated: the exact-hash gate** (controlled re-ingest fixture: same corpus ingested
twice into one store).

| Measure | Gate on | Gate off (Ablation) | Rung evidenced |
|---|---|---|---|
| `remember.refusal{duplicate_exact}` count | N (one per re-ingested item) | 0 | EXECUTED |
| Store record count after second ingest | unchanged | +N (generated from store manifest, not narrated) | EFFECTFUL |
| Second ingest after process restart | still refuses | records double | PERSISTENT |
| Retrieval ordering | **no change** (first-ingest ordering identical on/off) | same | — (negative assertion: a gate, not a scorer) |

**Mechanism ablated (rev 2): the noise class table** (`WM_GEN3_NOISE=0`, default on; declared
switch). Same fixture ingested with the table off: `remember.refusal{noise_class}` count N → 0 and
every item is admitted (written +N, recallable). Table on: refusals N, store count unchanged,
nothing purged. Retrieval ordering is unchanged on/off (negative assertion: intake hygiene, not a
scorer). No other refusal reason is affected by the switch.

Not claimed: **RE-ENTERS** — the gate is not read by selection; claiming a ranking effect would
falsify the row's placement. No field is added that no acceptance check consumes.

---

## 5. Acceptance + owner

Wrapper-side evaluation (harness reads journal + store manifests; counts generated, never
narrated):

1. **Duplicate refusal** — two ingests of one corpus: every second-ingest item refuses
   `duplicate_exact`; record count unchanged; a fresh process repeats the refusal (C5 round-trip
   template).
2. **Context non-collapse** — identical bytes with different `source`/`kind` admitted as distinct
   records on both ingests.
3. **Scope law** — identical bytes in two scopes admitted per scope; no silent merge across
   scopes.
4. **Drift (#5)** — writer killed at transaction points; restart yields coherent recall or explicit
   degraded disclosure, never silent zero.
5. **Partial (#6)** — large-payload fixture yields a single outcome (all-or-explicit-partial).
6. **Bare bytes check (#1)** — refused re-ingest leaves store bytes unchanged.
7. **Noise case (rev 2)** — each declared class (`traceback`, `error_line`, `json_blob`,
   `function_repr`, `too_short`) yields `remember.refusal` reason `noise_class` with the class
   named; zero records written; zero purges; control content (a log line without the class patterns
   and a ≥ 10-char string) is admitted; ordering over a pre-existing store is unchanged by the
   refusals (negative assertion); with `WM_GEN3_NOISE=0` the same input is admitted (ablation, §4).

**Owner:** Lucas Bailey (operator) — assigned at ratification, rev 1.
**Exit criteria (wave plan §2):** frozen spec + adversarial cases wired + ablation designed and,
where implemented, demonstrated + journal events declared (above) + receipt; **no inert acceptance
test**.

## 5.1 Revision history

- **rev 1** — frozen 2026-09-17, sha256 `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3`;
  receipt `receipts/W1_SPEC_A1_FREEZE_2026-09-17.md`.
- **rev 2** — amendment drafted 2026-09-17: operator disposition for traceback-class noise =
  **refuse-with-journal** (`noise_class`, declared class table §1.3, `WM_GEN3_NOISE` ablation §4;
  Gen3 has no quarantine organ). Additive to rev 1; takes effect at operator ratification with
  receipt `receipts/W1_SPEC_A1_AMEND_<date>.md`. Rejected alternatives recorded: admit +
  display-only flag (record-layout change, inert-passenger risk); scope-out detection (weakens the
  row battery, item 8).

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_A1_FREEZE_<date>.md` (spec sha256 + verified pins +
      session attestation)

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; the spec text changes by a new frozen revision with its
own receipt. Nothing in this spec authorizes code by itself; implementation follows the row's
gate.
