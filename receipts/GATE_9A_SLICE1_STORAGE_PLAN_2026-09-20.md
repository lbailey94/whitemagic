# Gate 9A Slice 1: durable-storage implementation plan

**Status:** planning artifact; source-inspected feasibility, no store was opened and no
runtime test was run for this plan.  **Baseline:**
`981b0bfac7acefb383ef86ef64699e32545c7849`.

## Decision

Slice 1 is feasible with the existing pinned `lmdb 0.8.0`, but the proposed
single-transaction named-database initialization is **not** implementable in this
crate's safe Rust surface.  `RwTransaction::create_db` is `unsafe` in lmdb 0.8.0;
`wm-gen3-core` forbids unsafe code.  Do not add an unsafe wrapper or silently replace
the dependency.  Use the safe, interruption-detecting protocol below and amend the contract's
"zero residual tables" claim accordingly.

`Environment::create_db` is safe, serializes its DBI-open operation, and commits one
write transaction per database.  Normal data mutation remains one ordinary LMDB RW
transaction and can atomically couple all Slice 1 effects.

## Safe opening and initialization protocol

1. A **fresh candidate** is only a missing path (created by the opener) or an existing
   empty directory.  A directory containing `data.mdb`, `lock.mdb`, or any other entry
   is an existing candidate.  This avoids treating an unknown filesystem layout as new.
2. Inspect an existing candidate through an LMDB read-only environment with normal
   reader locking. Do not assume a live store is safe to inspect with `NO_LOCK`. If
   its complete v3 header is absent, malformed, old, or future, return a typed refusal;
   do not call `create_db` and do not begin an RW transaction.  Slice 1 has no
   migration/adoption path.  Its preservation claim is specifically byte-identical
   `data.mdb` on isolated fixtures, to be verified by before/after SHA-256. This is an
   acceptance target, not an observed result; lock-file changes are outside that target.
   A subsequent writable open must revalidate the header before any writes.
3. On a fresh candidate, begin an RW transaction, re-read the default DB, and require
   it to contain neither metadata nor user entries.  Write `META_INITIALIZING = v1`
   and commit.  The writer lock serializes competing initializers; a second opener sees
   that marker and refuses.
4. In fixed order, call safe `Environment::create_db` for `records`, `relations`,
   `postings`, `embeddings`, `embed_cache`, `nullifiers`, and `receipts`.  Each call has
   its own committed metadata transaction.  A crash may therefore leave named DBs.
5. Re-open every required handle outside an application transaction; verify the marker.
   In one final RW transaction write realm ID, epoch `0`, next-record ID `0`, required
   counters, and then write the complete format-v3 header last while removing the
   marker.  `Store::open` accepts only this completed state.
6. `META_INITIALIZING`, partial handles, or partial header return
   `InterruptedInitialization`; Slice 1 performs no silent repair.  Explicit recovery
   is later work with its own preservation/authority contract.

The realm needs a direct, approved cryptographic-randomness dependency; none is a
direct current core dependency.  Add one deliberately before implementing a fresh
realm ID; do not rely on a transitive crate API.

## Slice 1 commit boundary

The replacement preserves `remember_batch` per-item outcomes. Each accepted item is
one authorized operation, as specified in `docs/GATE_9A_SLICE1_CONTRACT.md`.
After validating typed authority and request framing, one RW transaction must:

1. check `(operation_id, manifest_digest, realm_id, issuer/scope)` in `receipts` and
   return the matching cached receipt without mutation, or reject a mismatch as
   `IdempotencyConflict`;
2. for a new operation, check epoch, payload binding and durable duplicate policy,
   then allocate one zero-based record ID from `META_NEXT_RECORD_ID`;
3. write the record and its postings, update the counter and epoch exactly once;
4. write the operation nullifier and receipt (including assigned IDs); then commit.

Any error or dropped transaction leaves all of these effects absent.  Slice 1 must not
write an embedding vector outside this transaction. The bounded initial slice requires
vectors absent; supporting them requires a subsequent complete manifest extension.
The existing path writes a vector first and a record/postings transaction second, and
iterates items with per-item results. Preserve those results while replacing the partial
durable effect of each accepted item with one atomic transaction. Resolve committed
retries before new-operation epoch, budget or duplicate checks.

## Required acceptance evidence

Run only in disposable temporary environments and retain command/HEAD/test receipts:

- valid item and mixed-result batch: records, postings, next ID, epochs, nullifiers,
  and receipts match successful items, with no rollback of prior successes;
  reopen proves the same coherent state;
- identical authenticated retry returns the persisted receipt and changes neither epoch
  nor counters; same operation ID with a different manifest is refused;
- stale epoch, wrong digest, duplicate target, and invalid wire tags fail before any
  durable effect or nullifier burn;
- explicitly abort after staged record/posting/counter/nullifier/receipt writes; reopen
  shows epoch `0` and every table empty;
- force/construct each interruption point in initialization; every partial state refuses
  open and is never silently completed;
- construct a nonempty unversioned and a v2/v4 environment, hash `data.mdb`, attempt
  open, and prove the typed refusal plus identical hash;
- read-only open exposes no writable mutation path and opens all existing handles before
  an application read transaction.

## Ownership handoff

Terra owns the LMDB storage implementation/recovery tests after the shared contract is
frozen.  Sol owns the manifest, authority, receipt binding, and public-operation API.
Integration may begin only after both interfaces agree that IDs are zero-based logical
ingest IDs, per-item atomicity is preserved, and Slice 1 vectors are absent.
