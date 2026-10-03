# START HERE: finish Gate 9A

Updated 2026-09-22. **Verdict: OPEN.** This is the current continuation guide and
supersedes older task-status descriptions, not frozen requirements or historical receipts.
Prepared at the user's request as usage was nearly exhausted. Do not mistake a handoff for closure.

## Current candidate

Repository: `/home/lucas/Desktop/WMgen3`
Base HEAD: `981b0bfac7acefb383ef86ef64699e32545c7849`.
All implementation and documents remain uncommitted. Preserve unrelated work, do not reset,
stash, broadly format, stage everything, or start from HEAD alone. A HEAD checkout omits this work.
Current modified/untracked implementation manifest:
`receipts/gate9a_handoff_20260922/source-manifest.sha256`.
It fingerprints current implementation files; it is NOT a claim they passed one integrated run.

Read this guide, then the source, rather than restarting historical archaeology or another general audit.

## Update 2026-09-22 (sweep integration landed)

Steps 1–4 of this guide are implemented and verified by the continuation lane; see
`receipts/GATE_9A_SWEEP_ACCEPTANCE_2026-09-22.md` and its logs. The trusted planner, atomic v5
`commit_sweep`, validated inert replay, and ops/harness wiring are in the tree; ratified profile
v1 and the D2(b) volatile-usage receipt disclosures are in place; `gen3.think_sweep` and
`gen3.sweep_replay` are the explicit routes and batch ingest no longer auto-sweeps. Candidate
fingerprint: `receipts/gate9a_sweep_20260922/source-manifest.sha256` (the earlier handoff manifest
is historical — its hashes intentionally no longer match the working tree). Remaining before a
verdict: articles 2–9 and Evil Gana executable evidence, M0–M8 dispositions, the derived-cache
boundary, and a fresh integrated run plus independent review.

## What is implemented

1. LMDB is authoritative for intake. Compiler-issued CommitCapability binds request/authority/
   realm/epoch/operation. Record, lexical postings, allocator, epoch, nullifier and receipt commit
   atomically. Authenticated replay precedes new issuance and new-operation policy checks.
2. Current Store is format v4, intake receipt v2. Unsupported formats refuse; no migration/adoption.
3. Both production warrant mint paths require compiler seals. Typed basis checks refuse misuse
   before reference-executor mutation/nullification. Snapshot/seal construction has negative docs.
4. Counter malformed/missing/overflow cases refuse. Direct intake mismatch, wrong basis and
   receipt-v2 corruption tests exist; rollback/reopen tests remain.
5. New `crates/wm-gen3-core/src/sweep.rs` defines immutable request/effects, eight limits and
   observed counts, volatile usage snapshots, Disabled outcome, sweep receipt and proposed tagged
   CommitReceiptEnvelopeV5. `pulse_compiler::authorize_sweep` validates the typed bindings.
6. Sweep request construction is TEST-ONLY. `PRODUCTION_SWEEP_PROFILE_AVAILABLE = false`.
   There is NO integrated production planner or authorized sweep Store writer yet. The v5
   envelope is a proposal/type only; current Store has NOT been upgraded to v5.
7. `crates/wm-gen3-core/tests/gate9a_sweep_sizing.rs` is a runnable bounded synthetic sizing
   test using real tokenize/propose_supersedes functions but reconstructing the preflight in memory.
   It is not proof that the actual LMDB scanner is bounded or that the production planner matches.

## Evidence and its limits

- Prior converged candidate: external verifier reported 180 passed, 0 failed, 1 ignored, 5 filtered;
  release build and 8 harness scenarios passed. See GATE_9A_CONVERGENCE_VERIFICATION_2026-09-21.md.
  That manifest predates subsequent hardening and new sweep types: do NOT reuse its totals as current.
- Root independently ran 9 Store tests and 12 docs successfully before the latest sweep additions.
- Latest Sol report: 6 sweep tests, 14 compiler tests, 14 docs passed; no-default core check passed.
- Latest Terra report: sizing integration test 1 passed; three repetitions per fixture.
- Root confirmed Sol's final sweep/compiler/lib hashes and git diff --check at this handoff.
- No fresh combined workspace/release run was performed for this final handoff. Counts overlap;
  do not sum them or claim full M0–M8 qualification from focused tests.

## Exact remaining sequence and ownership

### 1. Select a production resource profile (Terra proposes; coordinator reviews)

Sizing receipt: `receipts/GATE_9A_SWEEP_SIZING_2026-09-22.md`.
Proposed REVIEW-ONLY starting values: 256 records, 16 KiB aggregate raw record bytes,
1 KiB largest record, 2 KiB posting bytes, 1,024 token occurrences, 256 relations,
8,192 examined pairs, 1,024 effects. These are deliberately small synthetic-derived ceilings,
NOT ratified production support or universal performance guarantees. Assess supported workload
requirements before accepting them; a 1 KiB record ceiling is restrictive. Record selected values,
profile version, units, refusal semantics and rationale. Keep configurable boundary tests separate
from approved production maxima. Never flip the profile-available flag merely to unblock a build.

### 2. Trusted bounded preflight (Sol orchestration; Terra bounded Store reads)

Compute exact effects outside the RW transaction from a coherent read snapshot. Check byte and
count budgets BEFORE decoding/allocating large objects; cap temporary pair/index/usage collections,
not only final effects. Include relation serialized sizes/usage snapshot costs if eight dimensions
alone do not bound these. Stop on scan/read/decode/limit errors with no canonical mutation.
Use real production algorithm, not the sizing test's reconstruction, as the single planner truth.
Only the trusted planner may construct production SweepRequest. Compiler must not simply stamp
caller-selected effects/counts. Preserve lifecycle truth table: used candidate promotes; used old
persistent stays; unused persistent of sufficient age demotes. Age alone is NOT equivalent.

Bind trusted process-local usage snapshot, random process identity, checked sequence, canonical
entries and digest. Explicitly disclose that restart loses usage lineage. This preserves current
process behavior, not durable usage history; do not silently introduce a new canonical usage writer.
Disabled returns before scanning, allocation, authority or ledger mutation.

### 3. Atomic Store integration (Terra; Sol owns shared types)

Agree exact manifest/receipt schema first. Recommended fresh-only v5 tagged intake/sweep envelope,
with explicit version/kind; reject v4 and older, no migration or ambiguous mixed decoding.
Update intake and sweep together when storage encoding changes; keep fixtures/tests aligned.
One per-realm operation-ID namespace: cross-kind reuse conflicts. Under one LMDB RW transaction:
validate capability/request, realm/epoch/read-set, duplicate/prior state, checked allocations;
write all relation effects, sweep/relation counters, one epoch advance, nullifier and receipt.
Rollback must leave ALL those surfaces unchanged. Gate/remove direct production alloc/write helpers
once all callers use the new path. Do not pre-burn a separate JSONL nullifier.

Replay must retrieve the ORIGINAL sealed request/plan before fresh issuance or rescanning changed
records/usage. Current SweepRequest is serialize-only: design validated replay decoding without
introducing a public deserialization authority-forging path. Storing bytes is not itself validated
recovery. Validate receipt/plan binding and distinguish corrupt ledger from changed-request conflict.

### 4. Ops and harness integration (Sol or coordinator; explicit file ownership)

Replace think_sweep's separate mutations and unwrap_or(0) with typed outcome/error propagation.
No reference-only fallback on the ordinary production path. Route disabled as a true no-op.
Legacy batch currently triggers an automatic sweep: choose explicit separately identified child
operation/retry semantics OR documented intake-only response with not_requested. Do not silently
claim compatibility after removing behavior. Never reuse an intake ID/token for sweep.
Review projections: this slice is projection-disabled; refusing it does not qualify model behavior.

### 5. Other closure obligations (independent reviewer + coordinator)

Resolve persistent embedding-cache authority/model-version/provenance/invalidation/rebuild policy.
Projection-enabled recall can write cache; derived does not mean harmless or side-effect-free.
Complete all nine Articles and specified adversary attempts with source enforcement and executable
checks. Remaining focus: remote admission, Ed25519 vs socket identity, derived-write boundaries,
evolution receipts, external-effect scope. Reference-model tests are not composed production proof.
Use `docs/GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` and
`docs/GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md`; recheck line numbers and dispositions.
PEB15 section8.2 assigns core qualification to9A and packaged compatibility to9B. Explicitly
account for that amendment and any excluded tests; don't rewrite historical closure claims.

## Required sweep acceptance

- At-bound/one-over EVERY resource dimension, including oversized single payloads; no mutation.
- Deterministic plan/effect digests; mutation of any effect/policy/usage/limit changes binding.
- Fresh authority, wrong realm/epoch/basis, cross-kind op IDs, duplicate creates/targets and prior-state conflicts.
- Real planner lifecycle truth table and explicit restart/volatile-evidence behavior.
- Abort after each staged effect/counter/epoch/nullifier/receipt; reopen proves no partial effects or burned IDs.
- Successful reopen/replay retrieves original plan after later commits and usage changes; no rescan/reissuance.
- Disabled and read/decode failures: no canonical effect, no zero-ID fallback.
- Concurrent identical/different operations: one durable commit with replay or conflict as appropriate.
- Byte-preserving unsupported-format refusal and malformed envelope/ledger rejection.
- Actual harness paths, including chosen batch/sweep policy; reference build separation maintained.

## Validation commands after the tree stabilizes

Run from repository root. Inspect outputs and preserve logs, exit codes, source hashes and features.
These commands do not authorize model execution, real stores, or release activity.

```bash
cargo test --offline --locked -p wm-gen3-core --test gate9a_sweep_sizing -- --nocapture
cargo test --offline --locked -p wm-gen3-core sweep::tests -- --nocapture
cargo test --offline --locked -p wm-gen3-core store::tests -- --nocapture
cargo test --offline --locked -p wm-gen3-core --doc
cargo test --workspace --offline --locked --features wm-gen3-core/reference-models -- --skip projection::tests --skip ops::gated_tests
cargo check --offline --locked -p wm-gen3-core --no-default-features
cargo build --release --offline --locked -p wm-gen3-harness
cargo tree --offline --locked -p wm-gen3-harness -e features
bash scripts/check_closures.sh
python3 scripts/check_slice1_harness.py target/release/wm-gen3
git diff --check
```

Extend the harness battery for new sweep behavior. Existing smoke is only intake coverage.
Filtered suite remains explicitly filtered: map every declared M0–M8 driver/invariant and
formally disposition exclusions before closure. Do not casually run unfiltered model tests.
Never invoke a harness against its default store. Use disposable synthetic paths only.
Broad cargo fmt may flag unrelated legacy drift; do not reformat the shared repository.

## Closure decision

Close only when all supported canonical mutation paths use validated compiler authority and
atomic durable ledgers; remaining Articles/adversary/regression obligations are evidenced;
no required behavior is merely disabled and called passed; exact candidate hashes/features/results
are recorded; independent review dispositions contain no unresolved closure blockers.
Then write a NEW verdict explicitly superseding premature historical closure headlines.
9B packaging, 9C cognitive recovery,9D migrations/operational chaos remain separate phases.

## Copy-paste continuation brief

> Work in /home/lucas/Desktop/WMgen3. Read docs/GATE_9A_FINISHING_GUIDE.md first and verify
> receipts/gate9a_handoff_20260922/source-manifest.sha256 against the working tree. Gate9A is OPEN.
> Preserve all uncommitted work. Sol owns sweep/compiler/types; Terra owns bounded Store reads,
> transaction/recovery; coordinator owns integration and verdict; independent reviewer owns evidence.
> Start with measured profile review and trusted planner integration, then atomic v5 Store and
> explicit ops/harness wiring. Do not restart completed ingestion work or mistake test-only sweep
> constructors for production readiness. Use synthetic disposable stores only; no models/history,
> migration, deploy, publish or broad staging. Implement in bounded reviewed increments, run relevant
> checks, record exact evidence, and close9A only when this guide's complete criteria are met.


## Final integration hints — read before implementing the planner

These are review questions and required invariants, not claims that a defect was reproduced.

1. **One coherent read snapshot.** Capture records, relations, relevant metadata and expected
   epoch from the same LMDB read transaction. Independently opened readers can assemble a plan
   from different durable states. A final epoch comparison is only sufficient if every relevant
   production writer advances that epoch; legacy bypass writers currently do not. Remove/gate
   them before relying on the epoch as the complete concurrency predicate.
2. **Do not trust caller-declared measurements.** Counts, usage provenance and proposed effects
   must come from the trusted planner, not a request whose constructor merely checks arithmetic.
   A self-consistent digest proves binding, not that the claimed observation occurred. Seals must
   certify actual validation rather than wrap arbitrary caller input.
3. **Check budgets before allocation.** Inspect LMDB value lengths before deserialization where
   possible. Bound individual and aggregate serialized bytes, token string bytes, relation values,
   usage entries and temporary candidate sets. Count repeated pair visits/work, not only unique
   pairs finally retained. A huge single token, giant source field or duplicate-heavy corpus can
   defeat an otherwise convincing count limit. Use checked arithmetic everywhere.
4. **Test memory-boundedness in the real scanner.** The sizing fixture reconstructs the algorithm
   in memory; its counters and timings do not prove production cursor/decoder behavior. Keep the
   planner truth in one implementation and compare fixture-derived expectations with that path.
5. **Restore data, never authority.** Persisted sealed-request bytes need explicit versioned,
   bounded, validated decoding. Do not derive Deserialize for authority/seal types to make replay
   convenient. Decode an inert wire representation, validate receipt/request/ledger coherence,
   and require fresh authority at replay entry. Corruption is not a new operation to retry blindly.
6. **Replay survives changed world and process.** Exact committed replay must work after later
   canonical commits and after a new process has a different usage identity. New planning uses the
   new identity; replay authenticates against the original stored plan. Never require matching the
   current process ID to the old receipt, and never regenerate original usage to replay a commit.
7. **Distinguish disabled, empty, refused and committed.** Disabled has no canonical effect.
   An enabled sweep producing zero relation effects may still advance sweep age and influence later
   lifecycle decisions: specify its counter/epoch/receipt semantics explicitly. A failed/oversized
   sweep must not age relations. Test these cases separately.
8. **Fix effect ordering semantics.** Specify whether lifecycle sees only preexisting relations
   (as current code skips relations created in this sweep), whether create and transition can target
   the same object, and which exact prior bytes/state are compared. Require finite bounded confidence,
   canonical float encoding (including negative zero policy), deterministic iteration and duplicate
   rejection. A digest must not depend on HashMap iteration order.
9. **Receipt evidence must explain the decision.** A usage digest alone binds opaque evidence but
   does not reconstruct it. Ensure the persisted original plan contains the intended evidence and
   policy/version needed for audit. Clearly distinguish attributable process observations from
   independently verifiable or restart-persistent usage history.
10. **Cross-kind ledger checks come before decoding a kind-specific receipt.** Sharing an operation
    ID between intake and sweep should produce the specified conflict, not an accidental decode error
    or a second commit. Envelope/receipt/request/nullifier version and digest checks must agree.
11. **Test the default production build externally.** Unit cfg(test) exposes synthetic issuers.
    At least one integration/harness test must compile core without those test-only constructors and
    without reference-models, then execute the real authorized path. A seal test can otherwise pass
    while the only successful runtime path depends on a fixture helper.
12. **Acknowledge commit ambiguity accurately.** Once LMDB commits, later journal/view/response
    failure cannot be reported as proof of rollback. Preserve the operation ID and use authenticated
    receipt lookup. Test a lost acknowledgement and retry; external delivery remains outside exactly-once
    local effects. Do not advance counters/budgets twice when reconstructing process views.

Suggested efficient review order: trusted planner provenance and bounds; coherent read snapshot;
transaction validation and all-or-nothing effects; receipt/replay recovery; real default-feature
caller; then full evidence refresh. Review these with source and failure tests, not only happy-path
counts. Do not enlarge the schema/API to solve hypothetical future phases before these invariants work.
