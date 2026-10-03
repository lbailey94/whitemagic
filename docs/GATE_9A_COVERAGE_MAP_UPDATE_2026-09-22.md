# Gate 9A coverage map update — 2026-09-22

Status: external review update by the continuation lane (opencode), superseding the status column
(not the historical text) of `GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` for the current working
tree. It does not change gate status. Evidence: the 2026-09-22 batteries (workspace suite, driver
form, harness scenarios, closure scans) and the tests cited below. Candidate fingerprint:
`receipts/gate9a_article_evidence_20260922/source-manifest.sha256`; logs in the same receipt
directory.

Method note: the 2026-09-21 review's statuses predate the sweep integration and the article-evidence
round; this update re-evaluates each item against the current tree and cites executable evidence.
Where a claim is model-level only, that is stated rather than upgraded.

## A. Nine articles

| # | Status now | Executable evidence on the current tree |
|---|---|---|
| 1 | **covered** | Ingestion and sweep/relation/counter mutation both consume compiler-issued `CommitCapability` and revalidate every binding inside one LMDB transaction (`store::tests::sweep_commit_*`, `gate9a_sweep_acceptance.rs`, `intake_public.rs`). Raw writers (`alloc_relation_id`, `put_relation`, `alloc_sweep`) are gated to test/reference builds; `update_relation` removed; `Store` exposes no public raw writer (compile-fail doctest). `mint_from_arbitration` remains `pub(crate)` behind the private `CompilerSeal` field and is only called from the compiler module (arbitration path) and tests (compile-fail doctest on `CompilerSeal`). |
| 2 | **covered** | Production trace: transport accept loop → `ingress_raw_bytes` → `authenticate_identity` → priority-lane enqueue; the spawned thread holds no commit path (`CommitCapability` is `!Send`/`!Sync`; compile-fail doctests) and spawns are transport-only (`check_closures.sh` [3/3]). `RemoteStimulus` has no conversion into authority (compile-fail) and the production admission route refuses its payload without local authority (`contract::tests::stimulus_payload_cannot_reach_production_admission_without_local_authority`). PEB-11 driver passes. |
| 3 | **covered** | No bridge from stored records into calibration (compile-fail on `LocalCalibrationPool`); committed remote-reported records leave the pool unchanged and foreign scores refuse (`contract::tests::committed_report_cannot_enter_local_calibration_pool`, `conformal` contamination tests, adversary battery row 4). |
| 4 | **covered** | Runtime refusal (`try_spawn_authoritative_loop`), `!Send`/`!Sync` compile-fail proofs, and a static rule that no `thread::spawn`/`rayon::spawn` exists outside `transport.rs` (`check_closures.sh` [3/3]). |
| 5 | **covered** | Identity is the Ed25519 key, never a socket/IP label: unregistered socket labels and impersonated registered labels are refused; a label authenticates only after TOFU key registration (`ganying::identity_boundary_tests::socket_address_never_authenticates_identity`), alongside existing replay/fork/noise tests. |
| 6 | **covered (model-level)** | Driver-form PEB-14b passes: ±24 h clock skew invariance, ancestry-vs-wall-clock inversion, true-concurrency preservation. No production consumer of `relativity` exists in this slice (no callers outside the module); the verdict states model-level qualification. |
| 7 | **covered** | Derived-only boundaries now have policy + tests: `docs/DERIVED_CACHE_POLICY.md`; canonical state unchanged by cache writes; version bump invalidates; projection-off recall writes nothing (`ops::cache_boundary_tests`). The hologram has no canonical-store handle (compile-fail) and indexing leaves canonical state byte-identical (`contract::tests::derived_hologram_index_cannot_mutate_canonical_store`). Projection-enabled intake/sweep refuse fail-closed. Remaining: cache GC/migration (9C register, non-blocking). |
| 8 | **covered (model-level; no production entry points)** | Cladistics Pareto-gate battery passes in driver form (PEB-6). A repo-wide search finds no production callers of `cladistics` outside its own module, so no evolution entry point exists in this slice; receipt-bearing evolution is deferred with the verdict stating the exclusion. |
| 9 | **covered** | Inventory updated (`GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md`) with the sweep transaction row and cache policy pointer; three new acceptance tests: audit failure after a successful commit is reported without rollback (`/dev/full` journal), lost acknowledgement recovers the identical receipt without a second epoch advance, and production commits create no JSONL ledgers (`gate9a_article9_acceptance.rs`). Transport ledger remains scoped to its own protocol. |

## B. Evil Gana attempts 2, 6, 7 (previously comment-only)

| # | Executable evidence now |
|---|---|
| 2 | `Store` compile-fail doctest (no public raw writer) + production admission refusal without local authority (runtime) + all canonical writes capability-gated. |
| 6 | `ganying::identity_boundary_tests::socket_address_never_authenticates_identity` (negative, impersonation, TOFU-positive). |
| 7 | `hologram` compile-fail doctest (no method accepts a `Store`) + runtime canonical-invariance test with a real LMDB store. |

Attempts 1/3/4/5/8 remain covered as before.

## C. Durable writer inventory (current tree)

| Writer | Status |
|---|---|
| `commit_intake` | covered (unchanged) |
| `commit_sweep` (new) | covered — one transaction for relations/counters/epoch/nullifier/tagged receipt; abort, replay, conflict, tamper and cross-kind tests |
| `put_record_and_postings`, `put_vector` | reference-only in production |
| `alloc_relation_id`, `alloc_sweep`, `put_relation` | gated to `cfg(any(test, feature="reference-models"))`; production callers removed |
| `update_relation` | removed |
| `put_embedding_cache` | derived, non-canonical; policy + tests (`DERIVED_CACHE_POLICY.md`) |

Issuers: `authorize_intake` / `authorize_sweep` / `authorize_sweep_replay` (production);
`mint_from_feasibility` (seal-only); `mint_from_arbitration` (seal-gated to the compiler module —
AMBER 1 disposition below).

## D. Prioritized missing tests — status

1. Sweep/relation authorized transaction tests — **done** (sweep acceptance + store tests).
2. Executable negatives for attempts 2/6/7 — **done** (section B).
3. Derived-cache boundary tests — **done** (Article 7 row).
4. Article 2 production-path refusal test — **done**.
5. Article 3 boundary test — **done**.
6. Feasibility-warrant accessor test — **done** (`pulse_compiler::feasibility_accessor_tests`; accessors already returned `Option`/`Result`).
7. Sweep counter no-mask test — **done** (disabled no-op allocates nothing; counter fail-closed tests).
8. Article 9 inventory — **done** (inventory + three acceptance tests).
9. Exact-candidate qualification — **partially done this round**: driver-form regression 17/17, workspace battery, harness scenarios, manifest; final unfiltered/model disposition and independent review remain.

## E. AMBER dispositions

1. **`mint_from_arbitration` in-crate reach** — the seal is a private field of `CompilerSeal` (only the compiler module can construct it; compile-fail doctest). Disposition: document the compiler-module trust boundary in the verdict; no code change.
2. **Panic-prone accessors** — already resolved on the current tree (`Option`/`Result`); explicit no-panic test added.
3. **Comment-only attempts** — resolved (section B).
4. **`alloc_sweep` masking** — resolved by D4 (disabled is a typed no-op; errors propagate; no ID 0).
5. **Documentation conflict** — registered as errata #67 (`PHASE4_ERRATA.md` batch N); the closure verdict must reconcile the stale "RATIFIED/FROZEN/COMPLETE" claims (152/167/181/180 test counts) without rewriting frozen history.

## F. Remaining before a closure verdict

- Final battery on the frozen candidate (workspace + drivers + harness + closures) with manifest.
- Independent review of this update and the acceptance receipts; then a new verdict explicitly
  superseding historical closure headlines, stating model/evolution exclusions and the
  compiler-module trust boundary.
