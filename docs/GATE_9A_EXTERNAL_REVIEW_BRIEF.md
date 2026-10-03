# Independent Gate 9A evidence review — external AI handoff

Work in /home/lucas/Desktop/WMgen3. You are the independent verification lead alongside
Sol (authority/orchestration), Terra (LMDB/storage), and the coordinating assistant.
Your task is to determine what remains to close Gate 9A and produce an actionable,
source-backed acceptance matrix. Do not assume the desired closure verdict.

## Current state and ownership

Base HEAD: 981b0bfac7acefb383ef86ef64699e32545c7849. This is a shared dirty checkout;
HEAD does NOT identify the current candidate. Sol and Terra are actively editing it.
Compiler interfaces and v4/receipt-v2 shared definitions have just landed; storage and
orchestration integration is ongoing. Temporary compile mismatches may occur.
The earlier 181-pass acceptance receipt describes the earlier Slice 1 candidate only.
Terra reports six passing storage tests for counter hardening before current integration.
Neither result qualifies the changing tree. Historical completion claims are not proof.

Sol owns capability.rs, pulse_compiler.rs, intake.rs, ops.rs and harness main.rs.
Terra owns store.rs and its embedded tests. Do not edit those files or create alternate
implementations. Your sole authored file is docs/GATE_9A_INDEPENDENT_EVIDENCE_REVIEW.md.
Do not stage, commit, reset, stash, format broadly, change gate status, or overwrite WIP.
If using a separate environment, obtain a current working-tree snapshot including untracked
files; checking out HEAD alone omits the work under review. Record source hashes/timing.

## Read first (paths relative to the repository above)

1. docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md
2. docs/GATE_9A_CLOSURE_CHECKLIST.md
3. docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md (all Articles, adversary attempts,
   hypotheses, gate definitions, and section 8.2 packaging amendment)
4. docs/GATE_9A_AUTHORITY_CONVERGENCE_PLAN.md
5. docs/GATE_9A_SWEEP_TRANSACTION_PLAN.md
6. docs/GATE_9A_SLICE1_CONTRACT.md
7. receipts/GATE_9A_SLICE1_ACCEPTANCE_2026-09-21.md

Then inspect crates/wm-gen3-core/src/{capability,pulse_compiler,intake,store,ops,contract,
projection,transport,journal}.rs; crates/wm-gen3-harness/src/main.rs; both crate Cargo.toml;
crates/wm-gen3-core/tests/{adversary_contract,intake_public}.rs;
scripts/{check_closures.sh,check_slice1_harness.py}. Follow relevant callers to other modules.
For regression mapping, use receipts/BENCHMARK_*.md and their referenced preregistrations,
source benchmark functions and test drivers; do not assume every historical receipt is current.

## Deliverable

Produce these in the one owned review document:

1. A matrix for all nine constitutional Articles and every specified Gate9A adversary
   attempt: actual production enforcement/call chain, executable test or driver, evidence
   candidate, covered/partial/missing/pending status, and exact remaining acceptance work.
2. A M0–M8 regression inventory mapping declared obligations to commands/drivers and
   expected invariants. Separate synthetic/reference checks from actual LMDB integration
   and model-dependent or historical execution. Identify missing coverage and exclusions.
3. A source-backed inventory of canonical writers, capability issuers and separate durable
   side effects. Pay attention to in-crate paths: pub(crate) alone is not authority enforcement.
4. Prioritized findings with file/line references, consequences, owner, and concrete acceptance
   criteria. Review snapshot sealing, issuer visibility, fresh authority, manifest/realm/epoch
   binding, replay before issuance, same-transaction effect/nullifier/receipt durability,
   format refusal, raw relation writers and derived-to-canonical authority boundaries.
5. Challenge unresolved sweep bounds, volatile lifecycle evidence and automatic sweep semantics.
   Recommend choices with compatibility implications; do not invent or ratify policy.
6. A closure recommendation with remaining blockers; do not declare Gate9A closed yourself.

Distinguish implemented, proposed, source-reviewed, agent-reported, independently tested,
and pending-integration evidence. No code comments posing as compile-fail tests. Do not
count model facade tests as production-path proof. Record files/hashes inspected and flag
concurrent source changes so findings are reproducible.

## Execution scope

Start with source/evidence review. Do not run builds or tests while the shared integration is
changing; return a proposed focused command list for coordination. No models/downloads,
real or historical stores, migration, network services, deployment, publication, benchmarks
against private data, or release ceremony. Never invoke the harness against its default store.
Future approved runtime acceptance must use explicit disposable synthetic stores.

Send back: report path, five most important findings, blockers to9A closure, and the best next
acceptance tasks. If repository access is unavailable, report that limitation rather than
presenting a document-only review as source verification.
