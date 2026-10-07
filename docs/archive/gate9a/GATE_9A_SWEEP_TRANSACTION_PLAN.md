# Gate 9A sweep and relation transaction plan

**Status:** design only. It follows the implemented Slice 1 ingestion contract; it
does not close Gate 9A, authorize implementation, model execution, historical data,
or a migration. Baseline for the inspected working tree is
`981b0bfac7acefb383ef86ef64699e32545c7849` plus the uncommitted Slice 1 candidate.

## Scope and source facts

`Store` is the authoritative durable implementation. `think_sweep` currently performs
these separate commits: allocates `META_SWEEP` before the disabled check; allocates a
relation ID and inserts each proposal; then independently overwrites each promoted or
demoted relation. Relations are canonical for this gate because `recall` loads live
relations and uses them for supersession and structural strata. `embed_cache` is a
separate derived persistent cache and is excluded from this slice.

The intended next slice is one **enabled, bounded sweep operation**. Computation is
outside the write transaction. The transaction applies an exact, typed effect list:

- `CreateSupersedes { src, dst, confidence_bits, rule_id }`;
- `SetRelationState { relation_id, expected_prior_state, next_state }`.

The store assigns relation IDs and the one new sweep ID only inside the transaction.
It rejects duplicate `(src, dst)` creates both within the supplied list and against the
durable relations DB. It rejects duplicate lifecycle targets, unknown relation IDs,
non-finite confidence, a mismatched kind/rule/class, and a prior-state mismatch.
State changes therefore prove exactly the prior durable relation that was authorized;
they never accept a broad "update relation" value.

## Bounded preflight and unresolved numeric limits

The present code calls the sweep bounded, but it is not bounded enough for one claimed
transaction: `Policy::pair_budget` is mutable and has no hard maximum, while lifecycle
at `ops.rs` iterates every durable relation. A complete sweep can therefore propose or
change an unbounded number of relations. This blocks the one-bounded-transaction claim.

Before implementation, preflight must enforce a frozen limit in each dimension that can
grow independently: records scanned, postings bytes read, expanded token occurrences,
relations scanned, candidate-pair examinations, and emitted effects. Every observed count
and every configured limit is bound into the policy/limits digest. Exceeding any limit
returns `SweepTooLarge` with **no canonical mutation** and no operation consumption;
silent truncation is excluded from the first sweep protocol.

The repository currently provides no evidence-backed production values for these six
limits. The mutable `pair_budget = 200_000` default is workload configuration, not a safe
constitutional maximum, and it supplies no bounds for the other dimensions. Numeric
constants therefore remain an explicit blocker requiring measured synthetic sizing and
operator ratification. Implementers must not invent them in code.

## Authority, manifest, and replay

A future compiler-issued affine `CommitCapability`, specialized for the sweep scope, is the
only commit input. It is not implemented by this plan and is the same authority type proposed
for intake, not a parallel authority system. Its request contains a stable caller operation ID, store realm,
expected global epoch, sweep-contract version, policy digest, read-set commitment, and
the ordered typed effect list. Its digest uses the Slice 1 domain-separated, framed
encoding rules but a distinct operation/scope literal, for example
`wm.gen3.sweep.v1`; it must bind every effect field and ordering.

Receipt lookup occurs before stale-epoch validation. A replay needs fresh possession of
the future typed authority and exact operation ID, realm, manifest digest, authority
descriptor, operation kind, and committed receipt. A changed request is
`IdempotencyConflict`; one-sided nullifier/receipt state is `CorruptCommitState`.
The receipt records pre/post epoch, assigned sweep ID, allocated relation-ID range or
explicit ordered IDs, effect count/digest, and per-effect outcome digest.

One global epoch is retained for now. It intentionally serializes successful intake and
sweep commits: a sweep computed from epoch E must reject at E+1 and be recomputed. It
must not merge an old proposal list after concurrent ingestion or another sweep, because
the candidate data and duplicate relation read-set may have changed. This is contention
by design, not a reason to bypass epoch validation.

The proposed shared interface is deliberately small and uses the existing authority:

```text
SweepLimits {
  max_records_scanned, max_postings_bytes, max_token_occurrences,
  max_relations_scanned, max_pair_examinations, max_effects
}
VolatileUsageSnapshot {
  process_instance_id, sequence, ordered_relation_counts, digest
}
SweepRequest {
  operation_id, realm_id, expected_epoch, limits, policy_digest,
  usage_snapshot, ordered_effects
}
authorize_sweep(&RatifiedChannel, &SweepRequest, &AuthorizationSnapshot)
  -> Result<CommitCapability, PulseError>
Store::commit_sweep(CommitCapability, &SweepRequest)
  -> Result<SweepCommitOutcome, StoreError>
```

Private fields and validating constructors must make the canonical order and digests
unforgeable by ordinary callers. `CommitCapability` binds the sweep scope, operation kind,
realm, expected epoch, operation ID, exact request digest, policy/limits digest, and usage
digest. The LMDB transaction remains the only owner of the durable operation nullifier
and receipt; it must not use the reference JSONL nullifier journal.

## Read set and volatile evidence

Before issuing capability, the compiler may read records, postings, relations, and a
policy snapshot. The transaction revalidates the minimum durable read set: realm,
global epoch, format version, policy digest, relation keys/states named by effects, and
absence of every proposed `(src,dst)` pair. The global epoch makes a whole-store record
digest unnecessary for correctness in this version.

Current promotion/demotion depends on `self.usage`, an in-memory volatile map incremented
by recall. Preserving current lifecycle behavior therefore requires an immutable trusted
process-local usage snapshot captured during preflight. The snapshot contains a fresh
process-instance ID, monotonic snapshot sequence, and relation IDs with their exact usage
counts in canonical order. Its framed digest, together with the lifecycle rule/version,
is bound into the sweep request and compiler-issued capability. The exact ordered effect
list remains the transaction input; LMDB does not reinterpret volatile usage.

This is explicitly process-local evidence. Restart loses the usage map and starts a new
process-instance lineage, which can change promotion and demotion eligibility until new
recalls occur. Receipts must disclose the usage-snapshot digest and process-instance ID;
they do not claim durable reconstruction. An age-only demotion rule is rejected because
it would demote relations that current behavior retains after observed use. Journal events
remain audit side effects and do not substitute for the bound snapshot.

## Transaction and format effects

For an enabled accepted request, one LMDB RW transaction must, in this order:

1. authenticate/replay-check operation identity and validate realm, format, epoch,
   policy/read-set, bounds, and all arithmetic;
2. read `META_SWEEP` and `META_NEXT_RELATION`, checked as exact eight-byte values;
3. assign the sweep ID and contiguous relation IDs, checking both counter overflows;
4. write every relation create and state transition;
5. advance both counters and global epoch once;
6. write nullifier and complete receipt; commit.

Malformed/missing counters are errors, never zero defaults. Any staged-write failure or
transaction abort leaves every relation, both counters, epoch, nullifier, and receipt
unchanged. Disabled sweep is a journaled volatile no-op with **no canonical mutation**:
no counter, epoch, nullifier, receipt, or operation consumption. This changes the
current pre-disabled counter bump and needs compatibility approval.

The implemented intake substrate is fresh-only store format v4 with receipt v2; v3 is
refused without migration. A sweep receipt/manifest therefore adds an explicitly
discriminated operation kind within v4 and must not reinterpret intake receipt bytes.
Any later incompatible receipt change requires an explicit decoder/version decision.

Automatic legacy sweep after compatibility-batch ingestion is also undecided. It must
either be removed/disabled for production, or receive a separately supplied sweep
operation ID and compiler-issued authority. It must never manufacture an authority from
the intake operation or run as an unreceipted post-commit side effect.

## Synthetic acceptance cases

All cases use temporary synthetic LMDB environments, projection disabled, and no model
or historical data.

1. Exact bounded create and state-transition list commits, reopens, and changes recall
   supersession exactly as its receipt claims.
2. Replay is immutable; altered policy, effect ordering, authority, prior state, realm,
   or operation payload conflicts; stale epoch has no durable effect.
3. Inject failure after each relation write, both counters, epoch, nullifier, and receipt;
   reopen proves no effect and the next accepted operation reuses the initial IDs.
4. Duplicate create in-list, existing pair, duplicate state target, unknown relation,
   wrong prior state, non-finite confidence, malformed/overflowed counters, and bound
   violations all fail closed without consuming the operation.
5. Concurrent/intentionally stale computation rejects on epoch/read-set change; a fresh
   recomputation commits once.
6. Disabled sweep writes no canonical state; the chosen legacy-batch policy is tested
   directly. Bound usage snapshots preserve current promotion/demotion rules, changing
   the snapshot changes the manifest, and restart-loss disclosure is asserted.
7. Unsupported receipt/header schema and nullifier/receipt asymmetry refuse after reopen.

## Ownership

Sol owns the future compiler authority, request/receipt framing, compatibility wrapper,
and policy/volatile-usage decision. Terra owns the `Store` transaction, counter/read-set
validation, receipt/nullifier persistence, rollback hooks, and synthetic store tests.
Astra independently checks source reachability, release feature exclusion, exact test
evidence, and that no direct relation/counter writer remains after integration.
