# Gate 9A Slice 1 sweep acceptance — 2026-09-22

Status: implementation and focused-evidence receipt from the continuation lane (opencode), working
under the operator-ratified terms in `receipts/GATE_9A_RATIFICATION_AMENDMENT_2026-09-22.md`.
**Gate 9A remains OPEN.** This receipt closes the sweep-integration step of the finishing guide
(steps 1–4); article-level evidence, M0–M8 dispositions, the derived-cache boundary, and an
independent verdict remain. Everything is uncommitted on top of `981b0bf`.

Candidate fingerprint: `receipts/gate9a_sweep_20260922/source-manifest.sha256` (28/28 verified).
Logs: `receipts/gate9a_sweep_20260922/logs/`.

## What landed

- **Ratified profile v1** (`sweep.rs`): the eight amendment values are frozen constants, bound into
  the policy digest; `PRODUCTION_SWEEP_PROFILE_AVAILABLE = true` because the full path exists.
- **Trusted bounded planner** (`sweep_planner.rs` + `Store::sweep_preflight`): one coherent LMDB
  read transaction; records decoded only after a pre-decode wire-size guard; observed byte/token/
  posting/relation budgets accumulated incrementally and refused before further allocation; df and
  relations bounded; the real production algorithm is the single planning truth (the sizing test's
  reconstruction is not consulted). Effects are canonically ordered; duplicate pair proposals are
  deduplicated deterministically; usage snapshot entries are bounded by `max_relations_scanned`.
- **v5 fresh-only store**: receipts are stored as tag-prefixed envelopes (explicit kind byte; a
  legacy raw receipt byte string can never decode as v5); v4 and older stores refuse with no
  migration; `commit_sweep` applies relation effects, both counters, one epoch advance, the
  nullifier and the tagged receipt in one LMDB transaction with per-stage abort tests; cross-kind
  operation-ID reuse is a typed `CrossKindConflict`; commit re-checks record existence, expected
  prior states, and that state effects cannot target relations allocated in the same transaction.
- **Validated inert replay**: persisted plan bytes decode into `ValidatedSweepPlan` (no
  `Deserialize` authority path; digests and bindings fully revalidated), and replay requires a
  fresh capability bound to the stored manifest digest and the *current* epoch. `Substrate::
  sweep_replay` works across later commits and process restarts with a fresh usage identity.
- **D2(b) disclosure**: receipts carry `usage_evidence_basis = process_local_volatile` and
  `usage_restart_persistent = false`; the persisted sealed request carries the bounded usage
  entries that drove decisions.
- **Ops wiring**: `think_sweep` plans and commits through the authorized path; disabled sweeps are
  typed no-ops that allocate nothing (counter peek only); projection-enabled sweeps fail closed
  (Slice 1 scope); refusals carry typed errors and never mutate. Legacy direct writers
  (`alloc_*`, `put_relation`) are gated to test/reference builds; `update_relation` was removed.
- **Harness**: batch ingest no longer triggers an automatic sweep — it returns
  `sweep: {"status": "not_requested"}` (ratified D4) — and explicit `gen3.think_sweep` /
  `gen3.sweep_replay` routes were added; the read-only guard covers them.

## Ratification mapping

| Decision | Disposition |
|---|---|
| D1 profile | Values ratified verbatim; refusal-only; at-bound/one-over coverage for records, per-record/aggregate bytes, tokens, pairs, postings and effects (planner unit tests + end-to-end acceptance). |
| D2(b) volatile usage | Preserved behavior with bound process-local snapshot; evidence persisted with the plan; replay never recomputes; restart sensitivity is disclosed in receipts and covered by an executable test (a used relation demotes after lineage loss once the durable age threshold is met); durable usage lineage deferred to a registered follow-on operation. |
| D3 v5 envelope | Fresh-only v5 tagged intake/sweep envelope; v4 and older refuse; no migration or mixed decoding; one operation-ID namespace per realm. |
| D4 disabled/legacy | Disabled is a typed no-op with no allocation; `unwrap_or(0)` path is gone; automatic post-batch sweep removed with a documented `not_requested` response. |

## Evidence (all commands from the finishing guide)

- Workspace suite (reference-models, ratified skips): 186 + 3 + 10 + 1 + 1 + 2 + 14 passed, 0
  failed, 1 ignored, 5 filtered — `logs/workspace-tests.log`.
- Focused: sweep 6, store 13, sizing 1, doc 14 passed — `logs/focused-tests.log`.
- No-default-features check, release harness build, feature tree — respective logs.
- Closure static scans PASS — `logs/closures.log`.
- Harness process-boundary scenarios: 9/9 including the new explicit-sweep scenario —
  `logs/harness-scenarios.log`.
- `git diff --check` clean — `logs/git-diff-check.txt`.

Dispositions: the two projection-path gated tests are now `#[ignore]` with an explicit reason
(projection-enabled intake fails closed under ratified Slice 1 scope; requalify in 9C). Phase
drivers and the unfiltered model suite remain out of this slice, per the coverage map. No models,
historical stores, migration, deployment, or publication were touched.

## Traps from the finishing guide, addressed

- Serialized plan bytes are now a validated inert representation, and the tamper test proves
  corruption refuses fail-closed.
- Review-only ceilings became the ratified profile; the qualification-not-capacity caveat is
  recorded in the amendment and in code comments.
- Trusted planner derives counts/effects; compiler binds the sealed plan; one coherent snapshot;
  budgets before allocation; cross-kind checks before kind-specific decoding; post-commit
  ambiguity handled by authenticated lookup/replay of the original operation identity.

## Remaining before a closure verdict

1. Articles 2–9 evidence and the Evil Gana executable attempts (`docs/GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md`).
2. M0–M8 driver/invariant mapping and formal exclusion dispositions.
3. Derived embedding-cache authority/version/invalidation policy (Article 7 boundary).
4. One fresh integrated run on the final exact candidate plus independent review, then a new
   verdict explicitly superseding historical closure headlines.

No commit or push was performed. The candidate manifest is the handoff fingerprint.

Companion records: qualified-path semantics supersessions are registered as errata batch N
(`docs/PHASE4_ERRATA.md`, items #60–66); store/data handling policy is
`docs/STORE_AND_DATA_HYGIENE.md` (audit: no production path touches real WM data; the only
real-tree reference is a test-only model-cache default in ignored 9C tests).
