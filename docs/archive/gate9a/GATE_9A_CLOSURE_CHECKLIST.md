# Gate 9A closure checklist — 2026-09-21

Status: OPEN. This is a current evidence checklist, not a ratification or amendment.
Baseline: 981b0bfac7acefb383ef86ef64699e32545c7849 plus uncommitted working-tree changes.
The Slice 1 acceptance receipt identifies an earlier tested candidate; subsequent source changes
require fresh hashes and relevant verification. Its 181 passing tests do not automatically
qualify the current tree or establish complete M0–M8 coverage.

## Required implementation and evidence

| Obligation | Current disposition | Closure evidence still required |
|---|---|---|
| Article 1: compiler authority for canonical mutation | OPEN: intake uses its own capability; sweep/relation writers remain separate | Same compiler-issued CommitCapability on actual LMDB paths; no caller-selected digest minting bypass; inventory all remaining issuers/writers |
| Atomic durable effects and retry | Partial: Slice 1 tested | Sweep/relation effects, counters, epoch, nullifier and receipt in one transaction; replay, conflict, abort and reopen tests |
| Article 2: remote stimulus has no execution standing | Existing contract/reference checks; composed path pending | Trace all actual remote admission/dispatch paths and test refusal without local authorization |
| Article 3: foreign confidence excluded from local calibration | Existing foreign-score refusal test | Map production calibration callers and test actual ingestion-to-calibration boundary |
| Article 4: no autonomous authoritative background loop | Existing reference checks; composed path pending | Inventory production scheduling and capability issuance; compile/runtime evidence beyond method names/comments |
| Article 5: cryptographic provenance | Not requalified in this round | Trace signed remote identity and distinction from local operator authority; cite concrete verification/rejection tests |
| Article 6: causal ancestry and influence closure | Not requalified in this round | Map causal enforcement and relevant regression drivers to current candidate |
| Article 7: projection is derived; non-finite inputs refuse | Coordinate tests exist; persistent cache boundary OPEN | Derived cache/version/rebuild policy and proof derived writers cannot mutate canonical records/relations |
| Article 8: evolution is Pareto-gated and receipt-bearing | Not requalified in this round | Map actual evolution entry points to statute/receipt enforcement and existing benchmark obligations |
| Article 9: external effects explicitly outside local atomicity | Scope clarification needed | Inventory audit/replay files, transport effects and model/cache activity; document their distinct durability guarantees |
| Evil Gana compile-time/runtime battery | Partial; some integration assertions are comments | Executable negative compilation tests and production-path runtime tests for each specified attempt |
| M0–M8 core regression | Coverage mapping OPEN | Enumerate each declared benchmark driver and expected invariant; distinguish reference/model tests from production integration; disposition model exclusions explicitly |
| Exact candidate and independent verdict | OPEN | Final source/artifact hashes, features, commands/results, finding dispositions, independent review |

## Current next assignments

- Sol: compiler-side typed feasibility authorization using CommitCapability, preserving arbitration;
  capability.rs / pulse_compiler.rs / intake.rs only. Production storage wiring remains a subsequent
  dependency until the concrete attestation and receipt schema are agreed.
- Terra: fail-closed counter decoding and overflow handling with synthetic tests in store.rs;
  this hardening does not replace the authorized sweep transaction.
- Coordinator: reconcile interfaces, inspect diffs, independently verify focused results and map
  wider regression coverage before integration.

## Decisions that block sweep integration

1. A hard candidate/effect bound is not yet specified. Existing mutable pair_budget and an
   all-relations lifecycle pass do not prove bounded work. Refuse oversize without partial mutation
   or ratify a deterministic selection rule; do not silently invent a policy limit.
2. Current recall usage is volatile. Lifecycle authorization needs explicitly bound evidence or
   a scoped exclusion; disabling a required behavior is not proof that the full gate passed.
3. Receipt schema/compiler binding compatibility must be explicit. No silent reinterpretation
   of existing v3 receipts, migration, or existing-store adoption.
4. Disabled sweep should have no canonical effect under the proposed contract; legacy automatic
   sweep behavior needs an explicit compatibility decision and separate authority/operation identity.

## Gate boundary

PEB-15 amendment section 8.2 assigns core encapsulation/regression to 9A and packaged CLI
verification to 9B. The final verdict must state that interpretation and account for the older
release-packaging wording and completion claims. Do not rewrite frozen history to claim closure.
Migration/dirty upgrade/physical power-loss qualification remains later 9D work. No real-data,
model, migration, release or deployment execution is authorized by this checklist.

References: GATE_9A_SLICE1_CONTRACT.md; GATE_9A_SWEEP_TRANSACTION_PLAN.md;
PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md; ../receipts/GATE_9A_SLICE1_ACCEPTANCE_2026-09-21.md.
