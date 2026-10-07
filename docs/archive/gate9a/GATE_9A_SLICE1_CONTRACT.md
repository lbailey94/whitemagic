# Gate 9A Slice 1 storage-authority contract

**Status:** implemented and synthetically checked as an uncommitted candidate; not Gate 9A closure
**Evidence:** [Slice 1 acceptance receipt](../receipts/GATE_9A_SLICE1_ACCEPTANCE_2026-09-21.md)
**Baseline:** `981b0bfac7acefb383ef86ef64699e32545c7849`
**Slice:** authorized durable ingestion through the existing `remember_batch` behavior
**Excluded:** World intake, sweep/relation mutation, historical data, model calls, deployment,
release ceremony, and any claim that a feature gate is cryptographic identity

This contract incorporates the useful shape of
`GATE_9A_STORAGE_AUTHORITY_CONTRACT_v1.1` while correcting the places where that text conflicts
with the checked-out implementation. `Store` in `crates/wm-gen3-core/src/store.rs` is the target
authoritative durable implementation. `KernelStore`, `SubstrateStore`, and `EvidenceStore` are
reference or construction models; they do not prove LMDB atomicity.

Implementation clarification: `EvidenceStore` remains a production working view. Only
`KernelStore`, `SubstrateStore`, and the explicitly named legacy ingestion helper require
`reference-models` outside unit tests. Enabling that feature is unsupported for the production
harness. The closure canary now uses an isolated, nonpersistent evidence model and marks its
journal event accordingly; it no longer plants an unreceipted canonical record.

## 1. Existing behavior that Slice 1 must preserve

The compatibility surface is the current `Substrate::remember_batch(&[RememberItem]) ->
Vec<Result<u64, String>>`:

- input order determines processing and successful ID order;
- every item produces one result, so a refusal does not roll back prior successful items and does
  not prevent later items from being considered;
- accepted import kinds are exactly `Reported`, `System`, and `Simulated`; World is absent;
- accepted records are `Class::Evidence`, `RecordStatus::Persistent`, confidence `1.0`;
- record IDs start at zero and `created_at == id`; `created_at` is logical ingest order, not wall
  clock time or Unix nanoseconds;
- gate precedence remains write budget, declared noise-table refusal when enabled, then exact
  duplicate `(sha256(content), source, kind)` refusal;
- budget `0` retains its current unlimited meaning, `writes_used` remains process-local, and the
  configured budget and noise ablation switch keep their current behavior;
- records and their lexical postings commit together; successful items update the in-memory
  identity map and `writes_used` once;
- existing journal event names and refusal strings remain stable.

The proposed 65,536-byte content cap, 1,024-byte source cap, persistent write-budget counter,
one-based ID allocation, batch-wide rollback, and nanosecond timestamp are prospective policy or
compatibility changes. Slice 1 does not adopt them. If desired later, they require a separately
versioned statute and migration/compatibility decision.

## 2. Authority boundary

Slice 1 introduces no arbitration score. Authorization is a feasibility gate, not cognitive
arbitration, and does not change kind, domain, class, confidence, status, or content.

The selected credential is possession of the existing `RatifiedChannel` value at the
trusted local call boundary. Its private field prevents ordinary downstream construction;
`RatifiedChannel::mint` exists only with the core crate's `operator` feature and `stub` only in
core unit-test builds. For this slice it authorizes only the operation scope
`wm.gen3.remember.v1` over the three existing non-World `ImportKind` values. It does not authorize
World records.

The authority descriptor bound into a request is:

| Field | Value |
|---|---|
| `authority_version` | `1_u8` |
| `scope` | UTF-8 literal `wm.gen3.remember.v1` |
| `issuer_label` | exact `RatifiedChannel::name()` bytes |
| `credential_class` | UTF-8 literal `local-ratified-channel-v1` |

Possession is checked by the typed API on every initial submission and retry. The label is audit
metadata and a digest component; label equality alone is not authentication. This is honest
local trusted-process authority, not a signature, durable principal identity, or cross-process
security boundary.

The only production binary in this workspace is `wm-gen3-harness`; its dependency now
explicitly enables the `operator` feature. The repository contains no `src/bin/wm.rs`.
The harness executable is the trusted local minting boundary and installs a `RatifiedChannel`
on its substrate. The ordinary `remember_batch` API routes through authorized ingestion; a
library substrate without an installed channel refuses ingestion. The separately named legacy
helper is available only to unit tests or explicit `reference-models` builds. The dedicated
`memory.intake_authorized` RPC exposes stable caller operation IDs and performs no automatic
sweep. Legacy batch RPC sweep behavior remains outside this slice.

## 3. Stable operation identity and single-use execution

`OperationId` is a caller-supplied opaque 128-bit value. It is stable across acknowledgement
retries and is distinct from the affine execution capability/nullifier. The operation ID is not
a record ID and carries no timestamp semantics.

For a new operation:

1. require the typed authority;
2. construct and validate the complete manifest below;
3. compute its domain-separated SHA-256 digest;
4. in one LMDB write transaction, check realm and expected epoch, ensure the operation ID is
   absent, apply exactly one accepted item, persist nullifier and receipt, advance epoch, and
   commit;
5. publish in-memory identity/budget changes only after LMDB commit.

For a retry, the caller resubmits the same operation ID, authority, and manifest. The store reads
the durable receipt and returns it without mutation only when all of these match exactly:

- store realm ID;
- manifest digest;
- authority version, credential class, issuer label, and scope as bound by that digest;
- operation kind and assigned target table;
- committed status.

Any mismatch is `IdempotencyConflict`. A missing/corrupt receipt for a present nullifier is
`CorruptCommitState`. Retry lookup does not require or recreate the consumed execution token, but
it does require fresh possession of the typed intake authority. This preserves single execution
while authenticating the local retry under the same authority class.

Resolve an authenticated committed retry before applying new-operation epoch, duplicate, or
budget checks. The retry retains its original expected epoch and manifest; it is not reissued
against the current epoch. A previously refused operation has no success receipt. For new
operations, durable duplicate checks and state preconditions are rechecked inside the write
transaction; an in-memory identity map alone is insufficient. The process-local budget remains
an explicitly limited policy counter, not a store-wide concurrent quota.

The public compatibility wrapper treats each item that passes the existing policy gates as its
own operation. It derives no operation ID from content; the caller-facing authorized API must
supply stable IDs. A batch-level request may carry an ordered list of item operation IDs, but
each item retains its current independent success/refusal semantics.

## 4. Canonical manifest v1

The digest input uses fixed-width big-endian integers and length-prefixed byte strings. No JSON,
MessagePack map, debug rendering, native-endian value, or floating-point text participates.
Lengths are `u64` so framing itself introduces no new content/source cap. Before hashing, checked
length conversions and total allocation bounds must fail closed.

The ordered byte sequence is:

| Order | Field | Encoding |
|---:|---|---|
| 1 | domain separator | length-prefixed ASCII `wm.gen3.commit-manifest` |
| 2 | manifest version | `u8 = 1` |
| 3 | store format version | `u32` |
| 4 | realm ID | 16 raw bytes |
| 5 | operation ID | 16 raw bytes |
| 6 | operation kind | `u8 = 1` (`remember`) |
| 7 | authority version | `u8 = 1` |
| 8 | credential class | length-prefixed UTF-8 |
| 9 | issuer label | length-prefixed UTF-8 |
| 10 | scope | length-prefixed UTF-8 |
| 11 | expected epoch | `u64` |
| 12 | target count | `u64 = 1` for an item operation |
| 13 | target table | `u8 = 1` (`records`) |
| 14 | allocation mode | `u8 = 1` (`store-next-contiguous`) |
| 15 | item ordinal | `u64`, original batch index |
| 16 | import kind | `u8`: Reported `0`, System `1`, Simulated `2` |
| 17 | content | `u64` byte length followed by exact UTF-8 bytes |
| 18 | source | `u64` byte length followed by exact UTF-8 bytes |
| 19 | record class | `u8 = 0` (`Evidence`) |
| 20 | status | `u8 = 2` (`Persistent`) |
| 21 | confidence bits | canonical `f32::to_bits(1.0)` as `u32` |
| 22 | created-at mode | `u8 = 1` (`equal-assigned-id`) |
| 23 | posting derivation | length-prefixed ASCII `field-tokenizer-v1` |
| 24 | vector effect | `u8 = 0` (`absent`) |

The manifest binds the values from which the record and postings are derived. Assigned record ID,
exact `created_at`, and derived posting keys are transaction outputs and are included in the
receipt. They need not be guessed before authorization because the manifest explicitly authorizes
allocation and the deterministic derivation rule.

All numeric parsing and arithmetic are checked. Reject unknown tags, non-finite or noncanonical
confidence encodings, exhausted ID space, epoch overflow, record-count/length overflow,
duplicate operation IDs, and malformed UTF-8. Slice 1's constant confidence is encoded and
validated even though callers cannot vary it.

## 5. Allocation and atomic durable effect

The authoritative transaction reads the next record ID derived from durable state, allocates the
next ID in the existing zero-based sequence, writes `created_at = id`, and advances the allocator
only if the transaction commits. Existing unversioned stores are refused; any future adoption
must separately specify allocator reconciliation. Conflicting or overflowing state fails closed.

One accepted item transaction contains all applicable durable effects:

- record value under `(records, id_be)`;
- all posting-list updates derived by the registered tokenizer;
- allocator/next-ID value;
- store epoch increment;
- operation nullifier;
- complete receipt.

Projection/model execution is outside the LMDB transaction and outside authority issuance. Slice
1 permits only `vector effect = absent` and fails closed if projection is enabled. It must not
call a model in tests. A later manifest version may authorize vectors only after it binds the
exact vector element bits, dimension, and model identity and commits the vector with the record.
The current prewrite of vector/cache data before the record is not accepted by this authorized
path.

The receipt contains at least: receipt version, realm ID, operation ID, manifest digest,
authority descriptor, scope, pre/post epoch, target table, assigned record ID, `created_at`, record
value digest, posting-set digest, vector-effect flag fixed to absent, and committed status.

## 6. Store initialization and format inspection

Fresh writable-store initialization must produce a coherent format marker, random realm ID,
epoch `0`, zero-based next-record ID, nullifier database, and receipt database before the store is
returned writable. Database handles must be opened outside an active transaction. The concrete
marker protocol must account honestly for LMDB database-creation transactions; it must not claim
that handle creation itself occurs in the metadata transaction. A partially initialized marker
or missing required database fails closed on reopen.

Selected implementation direction: using the default database, serialize a fresh-emptiness
check and commit an `INITIALIZING` marker before creating named databases through the safe
environment API. Only the initializer that installed this marker proceeds. Other opens refuse
an incomplete environment. Once every required database exists, one final write transaction
publishes format version 3, realm ID, both next-ID counters, epoch, and complete status together.
The store is returned only after that transaction succeeds. An interrupted initializer may
leave empty named databases; Slice 1 refuses this state and provides no automatic repair.
This deliberately replaces the supplied zero-residual-tables guarantee. Concurrent initialization,
marker ownership, and publication cut points require synthetic acceptance tests before qualification.

Opening an existing pre-format store is a migration decision outside Slice 1. Normal
`Store::open` must not silently stamp, adopt, scan, or upgrade it. Unknown old/future versions and
partial or corrupt headers fail closed before canonical writes.

The refusal preservation claim is logical: no LMDB transaction commits and all named-database
key/value content remains unchanged. Byte-for-byte `data.mdb` identity is not promised by opening
an LMDB environment unless a dedicated test proves it for the supported LMDB/platform setup.

## 7. Reference-model build boundary

Add an explicit core feature `reference-models = []`. Production storage-authority code must not
depend on reference-model types. Gating a public type with `cfg(test)` alone is insufficient for
integration tests because dependencies are compiled without their unit-test configuration.

The required build checks are:

- ordinary core and harness builds without `reference-models`;
- a declared integration-test target with `required-features = ["reference-models"]` when it
  needs model types;
- a release dependency-tree/feature check showing the production binary does not enable
  `reference-models`;
- an explicit operator-feature check when the recommended trusted-harness composition lands.

This feature boundary is compile-time exclusion of model code. It is not an identity,
authentication, or cryptographic boundary.

## 8. Slice 1 acceptance gates

All tests use synthetic temporary stores, projection disabled, and no real/historical data.

1. **Compatibility:** identical per-item results, zero-based IDs, refusal precedence, journal
   vocabulary, noise-ablation behavior, and process-local budget behavior.
2. **Atomic accepted item:** record, postings, allocator, epoch, nullifier, and receipt are all
   visible after reopen, or none are.
3. **Rollback injection:** failure after each staged write leaves no canonical partial effect and
   does not consume the operation ID or ID allocation.
4. **Retry:** identical request plus authority returns the stored receipt without epoch/budget/ID
   changes; altered realm, authority descriptor, scope, kind, order, content, source, or manifest
   version fails with `IdempotencyConflict`.
5. **Stale epoch:** no durable or in-memory effect and no burned operation ID.
6. **Numeric/framing validation:** the public immutable typed request fixes manifest version,
   scope, class, confidence and status; no binary-manifest decoder is exposed. Reject malformed
   RPC kinds/ordinals and metadata, check allocation/epoch/budget arithmetic, and bind all
   variable request fields with explicit framing. A future binary decoder needs its own
   unknown-tag, truncation and trailing-byte acceptance tests.
7. **Reopen/corruption:** receipt/nullifier mismatch and unsupported/partial format metadata refuse
   writes.
8. **Epistemic hygiene:** all three existing kinds round-trip unchanged; no World path is added;
   authority does not alter confidence/class/status.
9. **Build boundary:** default/release builds omit reference models; the explicit model-test target
   still compiles and runs.

Passing this battery qualifies only the ingestion slice. Gate 9A remains open until the same
authority/transaction discipline covers every canonical mutation path and the article-by-article
evidence matrix is independently reviewed.

## 9. Implementation ownership

- **Sol / contract and integration:** manifest/receipt types and framing, authority adapter,
  `remember_batch` compatibility integration, feature declarations/build checks, and this contract.
- **Terra / storage:** fresh initialization and format inspection, realm/epoch/allocator/nullifier/receipt schema,
  one-item LMDB transaction, retry lookup, rollback injection points, and reopen tests.
- **Astra / independent acceptance:** source review, exact-baseline verification, acceptance-battery
  execution, and closure assessment.

Recommended non-overlapping Rust ownership is `capability.rs` plus `ops.rs` for Sol and `store.rs`
for Terra. Shared changes to `Cargo.toml`, `lib.rs`, or common error/receipt types require an agreed
interface patch before either implementation branch edits them.
