# W2_02 / W2_04 — acceptance prep + operator checklist

**Status:** prep note · 2026-09-17 · compiled at tip `528047e` (tree clean; this note is an
untracked addition) · **no code, no verdicts; authorizes nothing by itself.**

**Framing correction (read first):** W2_02 and W2_04 **specs are already frozen + ratified**
(`receipts/W2_SPEC_BATCH_FREEZE_2026-09-17.md`: W2_02 sha256 `c9a2f09f…`, W2_04 `71f66725…`;
owner Lucas Bailey). Their headers still read "DRAFT" — errata §H #33: **receipts are canonical**.
The queued work for these rows is therefore **acceptance wiring + demonstration** (the pattern of
W2_01 / W2_03 / W2_07), not a new freeze. The synthesis map classes them `LINK · INVARIANT`
(W2_02) and `RECIPE` (W2_04), consistent with that reading.

**Common acceptance unit shape** (precedent: `IMPL_W2_01_ACCEPTANCE_2026-09-17`,
`IMPL_W2_03_07_2026-09-17`): one Python driver + journals + responses + results + `SHA256SUMS`
under `receipts/impl_w2_0X_2026-09-17/`, plus a receipt with acceptance / adversarial /
disclosures tables. Exit rule applies: **no inert acceptance test** — every "declared" item must
carry a scan or assertion, never a bare sentence.

---

## W2_02 — retention / lifecycle (frozen spec `c9a2f09f…`)

**Row class:** LINK (Gen2 keeps retention; Gen3 fixes `persistent`) + INVARIANT (rotation, not
deletion — Part 1 #2).

**What exists in Gen3 today (verified in this pass):**
- Records are created **`Persistent`** on every constructor
  (`crates/wm-gen3-core/src/evidence.rs:204,281,338,375`; comment `:40`: lifecycle is exercised
  on inferred relations) — the fixed import tier is structural.
- Relation lifecycle only: `think_sweep` (`ops.rs:967`) proposes, promotes
  (candidate→persistent, reason `survived+sweep+used`, `ops.rs:1114-1124`) and demotes
  (persistent→cold after ≥3 unused sweeps, `:1126-1138`) — **state changes, never deletion**;
  `relation.state_change` journal events.
- **No delete/forget/triage/retention/decay/hebbian symbols** anywhere in
  `crates/wm-gen3-core/src` or `crates/wm-gen3-harness/src` (source scan this pass; the only
  `pruned` hits are `pairs_pruned_by_projection`, a pair-budget term, not record pruning).
- No scheduler: the sweep runs only via explicit invocation (adapter, D1 policy); no background
  loop exists.

**Acceptance map (§5 / §3 → slice):**

| Spec item | Slice form |
|---|---|
| §5.1 organ naming | scan assertion (supporting): `RetentionEngine` / `Lifecycle::forget` absent in Gen3 source+binary |
| §5.2 propose-only + journaling | scan (no prune path) + cite W2_01 driver (proposal events); sweeps demonstrate proposals stay state changes |
| §5.3 all-zero success impossible | live probe: forced persist failure is a typed refusal (`remember.refusal` / `Err`), never an aggregate zero-success — cite A1 fixtures (`IMPL_A1_FIXTURES`) |
| §5.4 uniform policy + **record persistence (primary, behavioral)** | live: fixture survives **multiple explicit sweeps**, including passes that trigger `candidate→persistent` and `persistent→cold` **relation** transitions; after each pass every memory record remains present, content-identical, and addressable (count/hash/recall); relation lifecycle moves, records do not |
| §5.5 cold integrity | N/A in Gen3 (no cold records/tier); relation `Cold` is a state, disclosed as such |
| §3.1 all-zero success | §5.3 |
| §3.2 never-armed sweep | behavioral: sweeps run only when explicitly invoked (the fixture passes); scan supports (no scheduler) |
| §3.3 uniform policy | §5.4 |
| §3.4 propose-only | scan + event citation |
| §3.5 thresholds statutory | scan: no retention thresholds/constants in Gen3 |
| §3.6 cold integrity | N/A (disclosed) |
| §3.7 starvation | cite `IMPL_A2_DISCIPLINE` (typed starvation-vs-refusal) |
| §3.8 delete-path exclusion | behavioral §5.4 + scan supports; any re-entry = new registration |

**Proposed driver:** `driver_w2_02_retention.py` — **primary (behavioral):** ingest a fixture; run
multiple explicit `think_sweep` passes, including passes that cross `candidate→persistent` and
`persistent→cold` relation transitions; after each pass assert every memory record is still
present, content-identical, and addressable. This is the invariant the spec cares about:
**record persistence ≠ relation lifecycle.** **Supporting (absence):** symbol scans; records
report `Persistent`; pure reads leave store bytes unchanged; journals contain no purge/triage
events. String scans are supporting evidence only — symbols can be renamed, so the behavioral
invariant is the demonstration. **Expected core code change: none.** If a record is lost or a
scan contradicts the by-absence contract, stop and re-register (no silent fix).

**Exit receipt:** `receipts/IMPL_W2_02_ACCEPTANCE_2026-09-17.md`.

---

## W2_04 — dream / consolidation (frozen spec `71f66725…`)

**Row class:** RECIPE (consolidation = journaled `think` pass) · the spec itself is frozen; the
pass mechanism is the missing demonstration half.

**What exists in Gen3 today (verified in this pass):**
- The pass exists: `think_sweep` (`ops.rs:967`) emits `relation.proposed` (`:1095`),
  `think.sweep` with full stats (`:1197`), and `relation.state_change` (`:1123,:1137`).
- Measured-ordering surface: structural strata consume live `supersedes` relations
  (`ops.rs:676-686`, `state() != Cold`). **Demotion to `Cold` removes a relation from the live
  set** → a later recall's ordering changes; promotion (candidate→persistent) is observable as
  state persistence across process restarts (PERSISTENT rung) and journaled state change.
- No destructive triage: state changes + `update_relation` only; no delete path (scan).
- No phase enum, no CITTA labels, no priming/decay symbols (phase-agnostic and field-smuggling
  cases are N/A-by-construction, named not skipped).

**Acceptance map (§5 / §3 → slice):**

| Spec item | Slice form |
|---|---|
| §5.1 pass-effect measurement | driver, **matched A/B control**: identical fixture stores; same recalls on both; `think_sweep` invoked **only in A** — A: relation crosses the lifecycle condition → journal attests → later ordering changes; B: no pass → relation stays live → ordering unchanged. Plus promotion persists across restart (two-process check) |
| §5.2 journal attestation | driver asserts `think.sweep` + `relation.proposed`/`relation.state_change` per pass + hash-out linkage (N4) |
| §5.3 no destructive triage | **semantic object preservation** (not whole-file bytes — the pass's purpose is a state transition): memory record count unchanged; target memory content/hash/provenance unchanged; relation identity/endpoints/kind/provenance unchanged and still present; only its lifecycle state changed; no deletion/purge event. Whole-`data.mdb` equality is reserved for genuinely read-only ops |
| §5.4 no label citations | statement-level (no CITTA/phase metric exists to cite) |
| §5.5 phase-agnostic | scan: no phase-count artifacts in Gen3 |
| §3.1 destructive triage | §5.3 (semantic preservation) |
| §3.2 in-memory "ran" | pass without journal events fails: driver asserts event presence for the measured pass |
| §3.3 report-as-capability | N/A (no report surface); disclosed |
| §3.4 label artifact | N/A; disclosed |
| §3.5 phase inheritance | §5.5 |
| §3.6 field smuggling | scan: no priming/decay symbols; wave-4 gate untouched |
| §3.7 teeth test | the §5.1 measured delta is the test; a no-delta pass is reported as decoration |

**Proposed driver:** `driver_w2_04_consolidation.py` — build **matched A/B fixture stores**
(identical ingest); run the same recalls on both; invoke the declared pass only in A; demonstrate
A: lifecycle crossing + journal attestation + changed later ordering vs B: relation still live,
ordering unchanged (causal attribution of the delta to the pass); semantic object preservation
assertions per §5.3; promotion persistence across a fresh process; **F4 guard**: any
relation-count metric used in the report is the deduped metric (raw counts disclosed separately).
**Expected core code change: none.**

**Exit receipt:** `receipts/IMPL_W2_04_ACCEPTANCE_2026-09-17.md`.

---

## Operator checklist (both rows)

**Operator authorization recorded (2026-09-17):** directive verbatim — "All three: ratify,
authorize, commit" (session `6c634017`). B5 registration ratified; **W2_02/W2_04 acceptance
slices authorized for execution**; standing-authorization scope clarified
(`receipts/W2_SPEC_BATCH_FREEZE_CLARIFICATION_2026-09-17.md`; errata #36).

- [x] Authorize the two acceptance slices for execution (owner already assigned in the batch
      freeze; this is the execution authorization, not a new freeze). — recorded 2026-09-17
- [x] Confirm the no-code-change expectation: if a driver surfaces a gap, the slice stops and
      returns for a registration — no silent implementation. — confirmed 2026-09-17
- [x] Confirm receipt names + bundle names as above; results demonstrated in-session with
      `SHA256SUMS` pinned. — confirmed 2026-09-17
- [ ] Optional cosmetics (never a contract change): reconcile the stale `DRAFT` headers per
      errata #33.

**Carry:** WEAK stays WEAK · relation-count metrics carry the F4 guard · no verdict/claim/gate
movement · ops leftovers (stress fixtures wiring, Gen2-lane JSON write-through) unchanged.
