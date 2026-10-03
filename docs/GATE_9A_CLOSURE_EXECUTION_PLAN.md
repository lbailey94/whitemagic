# Gate 9A closure execution plan — 2026-09-21

Status: active implementation plan; Gate 9A remains OPEN. Supersedes task assignment
sections of the earlier checklist, not the frozen preregistration or its acceptance criteria.
No model calls, historical stores, migrations, publication, deployment, or release ceremony.

## Milestone A — authoritative ingestion convergence (assigned now)

Sol owns capability.rs, pulse_compiler.rs, intake.rs, ops.rs, harness orchestration and their
focused tests. Terra owns store.rs, LMDB snapshot construction, commit validation, recovery
and storage tests. Agree the interface before dependent edits; no concurrent ownership of a file.

Use one compiler-issued CommitCapability. Authorization must recompute the typed request
binding and validate fresh local authority against a real store-authenticated snapshot.
Ops cannot fabricate that snapshot. A digest-stamping facade is insufficient. Preserve scored
arbitration semantics without fake feasibility scores or invented candidate/sequence IDs.

Use fresh-only store format v4 and receipt v2 with explicit compiler bindings; v3 refuses.
The previous candidate was fresh-store-only and uncommitted. Add no migration or adoption.
Sol defines the receipt schema with Terra before either integrates it.

Retain process-local policy order without claiming compiler validation proves gates it does
not enforce. Replay checks fresh authority and the original request before new issuance and
current-epoch refusal. LMDB alone owns canonical nullifier/effect durability. Store rechecks
all token/request bindings and current state inside the write transaction. Remove the old
production IntakeCapability issuance path once the new path works.

Exit: focused compiler/storage/public API tests, wrong-binding no-write tests, replay and
rollback/reopen checks, release build/features, and subprocess acceptance on the integrated
candidate, independently reviewed by the coordinator. Passing compiler-only tests is not exit.

## Milestone B — settle sweep semantics (next, before sweep coding)

Sol defines policy/evidence semantics; Terra validates transaction feasibility; coordinator
reconciles compatibility and acceptance implications. Produce one agreed contract addressing:

- Hard candidate/effect bounds with explicit oversize refusal or deterministic selection.
- What usage evidence authorizes lifecycle changes; volatile observations cannot silently be
  described as durable. Preserve required behavior or explicitly disposition a scope change.
- Ordered create and exact-prior-state transition effects; duplicate/conflict rules.
- One snapshot, one epoch advance, atomic relation/sweep allocation and effects.
- Disabled sweep has no canonical effect under the proposed contract; make compatibility
  changes explicit. Automatic batch-triggered sweep needs distinct operation identity/authority.

Do not invent a parallel SweepCapability. Use the same compiler-issued CommitCapability.
Unresolved numerical limits or lifecycle semantics remain blockers, not implementation guesses.

## Milestone C — canonical writer closure

Terra implements one bounded atomic sweep transaction and failure/reopen evidence.
Sol implements compiler validation and explicit orchestration with retry semantics.
Coordinator independently traces every writer and caller, checks recall behavior and verifies
no old relation/counter mutation route remains reachable as an unauthorized production path.
Exit includes no orphaned IDs, no partial lifecycle batch, concurrent stale/conflict refusal,
repeatable replay, and production feature-boundary evidence.

## Milestone D — derived state and other constitutional boundaries

Sol defines cache/projection authority, identity/version and invalidation rules. Terra verifies
persistent cache operations and their separation from canonical state. Coordinator inventories
other durable effects: audit journals, transport replay logs and reference nullifier files.
Do not treat disabling a required supported behavior as successful qualification of that behavior.
No model execution is implied; mark any required model-dependent evidence pending separate scope.

Map all nine Articles and every specified adversary attempt to actual production enforcement
and executable tests. Existing reference tests or comments are not substitutes for that mapping.

## Milestone E — exact candidate acceptance and verdict

Coordinator owns evidence synthesis and independent review. Sol maps M0–M8 drivers to declared
invariants; Terra reviews recovery coverage and failure-injection limits. Run required checks
only after the integration candidate stabilizes. Distinguish model/reference checks, full declared
benchmark coverage, production integration, and physical crash qualification.

Record source/artifact hashes, enabled features, commands, results, skips and every unresolved
finding. Refresh the earlier Slice 1 source manifest rather than claiming its hashes identify a
new candidate. Resolve conflicting historical completion wording through a new current verdict;
do not rewrite frozen history. Close 9A only when all required obligations are evidenced.

Gate9B packages/verifies the compatibility shell under PEB15 section8.2; Gate9C proves cognitive
behavior and Pareto value; Gate9D covers migration and operational reality. Completing 9A permits
entry to those phases, not a claim that they have already passed.
