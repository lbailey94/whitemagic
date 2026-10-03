# Gate 9A Sol morning preparation

**Status:** implementation checklist for the next bounded sweep slice. This is not
ratification, implementation evidence, Gate 9A closure, migration approval, model execution,
or historical activation.

## Shared interface checklist

The sweep path must use the existing compiler-issued affine `CommitCapability`; it must not
introduce `SweepCapability` or let `ops` mint authority. The compiler validates a fresh typed
authority, Store-sealed realm/epoch snapshot, canonical sweep scope and operation kind, exact
request digest, policy/limits digest, and usage-snapshot digest. LMDB remains the sole durable
owner of the operation nullifier and receipt.

`SweepRequest` should have private immutable fields and a validating constructor. Its canonical
manifest binds:

- manifest/schema version, operation ID, realm ID, and expected global epoch;
- authority descriptor and digest, exact sweep scope, and sweep operation kind;
- sweep policy/rule version and policy digest;
- every configured and observed preflight count for records scanned, postings bytes read,
  expanded token occurrences, relations scanned, pair examinations, and emitted effects;
- `VolatileUsageSnapshot` digest and process-instance ID;
- the exact ordered effect list and effect-list digest.

The only initial effects should be:

- `CreateSupersedes { src, dst, confidence_bits, rule_id }`;
- `SetRelationState { relation_id, expected_prior_state, next_state }`.

Canonical ordering, duplicate-pair and duplicate-target rejection, finite confidence, allowed
state transitions, and checked numeric conversions belong in the request constructor or compiler
preflight. Store must independently revalidate all security-relevant bindings and durable prior
state inside one RW transaction.

`VolatileUsageSnapshot` should bind a fresh process-instance ID, monotonic snapshot sequence, and
canonical ordered `(relation_id, usage_count)` entries. It is trusted process-local evidence,
not durable evidence. Restart loses this lineage and can change promotion/demotion eligibility
until new recalls occur; the receipt must disclose that boundary. Tomorrow’s implementation must
preserve the existing usage-dependent promotion and demotion rules. Age-only demotion is excluded.

`SweepReceipt` should carry an explicit receipt version and operation kind, operation ID, realm,
authority digest, compiler scope/capability class, manifest and policy/limits digests,
usage-snapshot digest and process-instance ID, pre/post epoch, assigned sweep ID, allocated
relation IDs, ordered effect count/digest, per-effect outcome digest, all observed preflight
counts, and `committed = true`. Replay lookup occurs before new compiler issuance and current
epoch validation; altered manifests conflict, while nullifier/receipt asymmetry is corrupt state.

## Disabled and automatic sweep behavior

Disabled sweep is a typed volatile no-op. It must return a distinct `Disabled` outcome and write
no sweep counter, epoch, relation, nullifier, or receipt. Counter and Store errors must propagate;
`unwrap_or(0)` is forbidden. The disabled result may be journaled outside canonical LMDB state.

Compatibility-batch ingestion must not reuse its intake operation ID or capability for an
automatic sweep. If automatic sweep remains supported, the caller supplies a distinct stable
sweep operation ID and fresh sweep authority, producing a separate receipt. Otherwise the route
must explicitly report that no sweep was requested. An unreceipted post-ingestion sweep is not a
supported middle state.

## First implementation step

Begin with a projection-disabled synthetic preflight measurement harness that performs no Store
writes and issues no capability. Fixtures vary record count and content bytes, token expansion,
posting fan-out, relation count, pair examinations, and effect materialization. Record the exact
six counts, peak collection lengths, elapsed time, machine/toolchain envelope, and repeated-run
variance. Choose a documented conservative headroom rule before proposing numeric limits. Current
source provides no evidence-backed numeric bound; `pair_budget = 200_000` cannot substitute.

After that sizing evidence is reviewed, implement the shared immutable types, framed digests,
validation errors, and compiler authorization for synthetic sweep requests. Do not add the Store
writer or route production callers in that authority step. Proposed ownership:

- Terra/coordinator: a narrowly scoped synthetic sizing fixture under `benchmarks/` or `scripts/`
  and any read-only counting helper required to reproduce current preflight;
- Sol after limits are ratified: a narrowly named new `sweep.rs`,
  `capability.rs`, and `pulse_compiler.rs`;
- Terra after the interface compiles: `store.rs` transaction, receipt persistence, rollback, and
  Store tests;
- coordinator after both: `ops.rs`, harness routing, legacy writer removal, integrated evidence.

## Decisions still required

Actual policy/schema decisions:

1. Ratified numeric values for all six preflight limits, based on sizing evidence rather than the
   mutable `pair_budget = 200_000` default.
2. Whether sweep receipt fields fit as a discriminated operation in current fresh-only Store v4,
   or require a new store/receipt version. No mixed decoding or migration should be inferred.
3. Whether production compatibility batches request an automatic sweep or return intake only.
4. The process-instance ID generation and trust statement for the volatile usage snapshot.

Routine engineering choices after those decisions include Rust module placement, fixed-width
framing helpers, internal field names, error enum organization, and deterministic digest test
vectors. These do not justify changing lifecycle semantics or authority boundaries.

## First morning tests

1. A valid synthetic request produces a compiler-issued `CommitCapability` binding every sweep
   field, both digests, realm, epoch, operation ID, scope, and operation kind.
2. Changing one effect, its order, any bound/count, policy digest, or usage entry changes the
   manifest and causes capability/request mismatch refusal.
3. Stale epoch, wrong realm, wrong typed authority, malformed effect, duplicate pair/target, and
   any exceeded preflight dimension refuse before capability issuance.
4. The disabled path returns `Disabled`, propagates a synthetic counter error when enabled, and
   performs no canonical allocation when disabled.
5. A compatibility intake ID cannot serve as the sweep ID; exact sweep replay returns its stored
   receipt before fresh issuance, while changed content is an idempotency conflict.
