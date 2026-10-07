# Gate 9A authority convergence plan

**Status:** implementation design; no Rust implementation or Gate 9A closure claim  
**Source baseline:** `981b0bfac7acefb383ef86ef64699e32545c7849` plus the uncommitted Gate 9A Slice 1 candidate  
**Decision:** preserve frozen PEB-15 Article 1 and H15-1; every canonical mutation consumes the
same `CommitCapability` issued through the PulseCompiler boundary  
**First convergence slice:** immutable non-World intake only

## 1. Problem statement

Slice 1 proves useful LMDB properties: typed local authority possession, payload-bound operation
identity, atomic record/posting/allocator/epoch/nullifier/receipt commit, and authenticated replay.
It does not yet prove the frozen authority topology. `ops.rs` currently issues
`IntakeCapability` directly after local policy checks. PEB-15 Article 1 and H15-1 instead require
the un-bypassable PulseCompiler to issue `CommitCapability`.

The solution is convergence, not a constitutional exception. Intake remains a deterministic
feasibility operation; it does not receive fabricated cognitive margin, risk, utility, or
epistemic scores. The existing scored arbitration path remains intact for cognitive candidates.

Merely adding `PulseCompiler::authorize_digest([u8; 32])` is insufficient. Such a method would
allow any in-crate caller to wrap an arbitrary digest in constitutional authority without proving
the operation kind, trusted issuer possession, scope, realm, epoch, operation identity, fixed
epistemic semantics, or correspondence between the digest and an immutable request.

## 2. One capability, two validated warrant bases

`CommitCapability` remains the only token that can cross the canonical mutation boundary. It
stays affine, non-serializable, non-cloneable, `!Send`, and `!Sync`.

Its private `VerifiedWarrant` gains a private basis enum:

```rust
enum WarrantBasis {
    Arbitrated {
        candidate_id: u64,
        composite_margin_bits: u64,
        estimated_risk_bits: u64,
        epistemic_status: EpistemicStatus,
        sequence_id: u64,
        token_digest: [u8; 16],
    },
    Feasibility {
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        authority_digest: [u8; 32],
        operation_kind: u8,
    },
}
```

Common immutable warrant fields are:

- `authorized_digest: [u8; 32]`;
- exact scope string;
- one private `WarrantBasis`;
- a private construction seal.

`VerifiedWarrant::mint_from_arbitration` continues to enforce K1, margin ≥ 0.85, and risk ≤ 0.10.
It constructs `WarrantBasis::Arbitrated`; its current behavior and tests remain unchanged.

The feasibility constructor is private to `pulse_compiler.rs`, either through a private helper in
`capability.rs` callable only by a narrow crate-private compiler function, or by moving the helper
behind a sealed compiler-owned type. It must not be public, serializable, or callable from the
harness. It creates `WarrantBasis::Feasibility` only after all checks in §4 pass.

No `IntakeCapability`, `SweepCapability`, `RelationCapability`, or maintenance-specific canonical
capability survives production convergence. Future operation families use the same
`CommitCapability` with distinct manifest domain separators, operation-kind tags, and compiler
validation functions.

## 3. Typed inputs

### 3.1 Immutable request

The existing `IntakeRequest` remains private-field and immutable. It binds:

- manifest and store format version;
- store realm;
- stable caller-owned operation ID;
- operation kind `remember`;
- authority version, credential class, issuer label, and exact scope;
- expected epoch and item ordinal;
- non-World import kind;
- exact content and source bytes;
- fixed Evidence class, Persistent status, confidence `1.0` bits;
- store allocation mode, logical `created_at == assigned id`, tokenizer identity, and vector-absent
  mode.

The compiler recomputes `IntakeRequest::digest()`. It never accepts a caller-supplied digest as
the thing to authorize.

### 3.2 Fresh authority possession

The compiler function accepts `&RatifiedChannel`, not an issuer-label string or stored descriptor.
It calls `request.authenticate(channel)` and validates the resulting canonical descriptor. This
proves fresh local typed possession at issuance and prevents receipt metadata from becoming an
authentication token.

### 3.3 Store-authenticated snapshot

The compiler must not accept loose caller-provided realm and epoch primitives. The production
integration will add a crate-private, immutable attestation created by `Store`:

```rust
pub(crate) struct AuthorizationSnapshot {
    realm_id: [u8; 16],
    epoch: u64,
    _private: (),
}
```

Only `Store::authorization_snapshot()` constructs it after reading and validating the format-v4
header in one LMDB read transaction. It exposes read-only getters. `ops.rs` may transport the
attestation to the compiler but cannot construct or modify it.

For the compiler-only implementation round, use a sealed synthetic attestation constructor under
`cfg(test)`. Production issuance remains unavailable until `Store` implements the real constructor.

## 4. Minimal feasibility compiler

Add a crate-private function in `pulse_compiler.rs`:

```rust
pub(crate) fn authorize_intake(
    channel: &RatifiedChannel,
    request: &IntakeRequest,
    snapshot: &AuthorizationSnapshot,
) -> Result<CommitCapability, PulseError>;
```

This is a compiler path because it validates a typed proposed state transition against an
authoritative snapshot and emits the sole canonical commit token. It is not cognitive arbitration.

It performs every check below before capability issuance:

1. `request.authenticate(channel)` succeeds with fresh typed possession.
2. Authority version, credential class, issuer label, and scope are canonical and nonempty where
   required.
3. Scope equals `wm.gen3.remember.v1`; operation kind equals `remember`.
4. Request manifest/store format versions are supported.
5. Request realm exactly equals the sealed store snapshot realm.
6. Request expected epoch exactly equals the sealed store snapshot epoch.
7. Import kind is one of Reported, System, or Simulated; no World representation exists.
8. Fixed class/status/confidence/created-at/allocation/tokenizer/vector fields are the registered
   Slice 1 values.
9. Content/source framing is representable without arithmetic overflow; no new size policy is
   introduced.
10. Operation ID and item ordinal are exactly those bound by the immutable request.
11. The compiler recomputes the manifest digest and canonical authority-descriptor digest.

On success it privately creates a feasibility warrant and immediately returns
`CommitCapability::claim(warrant)`. No intermediate public warrant leaves the compiler function.

Statutory process-local gates retain their existing order before issuance: budget, declared noise
table, and exact duplicate. The compiler does not invent a second noise table or persistent budget.
The LMDB transaction rechecks durable duplicate state after issuance. A later refactor may move
statutory validation behind a sealed compiler input, but this convergence slice is not allowed to
change those policies.

## 5. Required capability accessors and validation

`CommitCapability` exposes read-only accessors needed by `Store` without exposing constructors:

- `authorized_digest()`;
- `scope()`;
- `feasibility_operation_id() -> Option<OperationId>`;
- `feasibility_realm_id() -> Option<[u8; 16]>`;
- `feasibility_expected_epoch() -> Option<u64>`;
- `feasibility_authority_digest() -> Option<[u8; 32]>`;
- `operation_kind()`.

The accessors return `None` for arbitrated warrants where the field does not apply. Storage rejects
an arbitrated warrant for an intake operation and rejects a feasibility warrant with a different
operation kind.

The current `nullifier_key()` remains for reference-model arbitration tests. It is not the
authoritative LMDB replay identity. Feasibility intake uses the exact 128-bit `OperationId` already
bound into the manifest and LMDB receipt ledger.

## 6. Replay and issuance ordering

The production call sequence is fixed:

1. Build immutable `IntakeRequest` using a store-authenticated realm/epoch snapshot.
2. Require fresh `&RatifiedChannel` possession.
3. Ask LMDB for an authenticated receipt using request plus fresh authority.
4. If the receipt matches, return it immediately without policy re-evaluation or capability
   issuance.
5. If no receipt exists, apply the current process-local budget/noise/duplicate gates.
6. Call `pulse_compiler::authorize_intake` with the request and the same sealed snapshot.
7. Consume the returned `CommitCapability` in `Store::commit_intake`.
8. Inside the LMDB write transaction, repeat receipt/nullifier lookup before epoch and mutation
   checks to close the race with another writer.

Replay-before-issuance matters. Reissuing a new capability for an already committed operation
creates unnecessary authority and can fail under a later epoch even though the correct behavior is
to return the original receipt.

## 7. LMDB owns canonical nullification

The authoritative LMDB transaction remains the sole owner of operation nullifier and receipt
durability. `Store::commit_intake` atomically commits:

- record and lexical postings;
- allocator and epoch;
- operation-ID nullifier bound to manifest digest;
- versioned receipt bound to compiler authority.

It must not call `NullifierSet::register`, `execute_transactional_commit`, or append to the
capability JSONL journal. Those mechanisms remain reference-model evidence. Pre-burning a file
nullifier before the LMDB transaction could create a permanently consumed capability with no
canonical effect, recreating the lost-effect failure that Slice 1 eliminated.

The LMDB consumer validates before mutation:

- capability operation kind is intake;
- capability scope is exact;
- capability operation ID, realm, expected epoch, authority digest, and authorized digest match
  the immutable request;
- request digest is recomputed;
- realm and current epoch match LMDB metadata;
- durable duplicate and tokenizer-derived postings checks succeed.

The token is consumed by value regardless of commit outcome. A caller retries with the stable
operation ID and receipt lookup, never by recreating or resubmitting the consumed token.

## 8. Receipt and format versioning

Receipt v2 adds the compiler authorization binding:

- `capability_class = feasibility`;
- compiler operation kind;
- exact scope;
- authority-descriptor digest;
- authorized manifest digest;
- operation ID, realm, pre/post epoch, target table, assigned record ID and existing effect digests.

The Slice 1 format-v3 candidate is uncommitted, fresh-store-only, and explicitly not a migration
baseline. The preferred implementation is to bump the store format to v4 when v2 receipts land,
reject v3 on normal open, and regenerate synthetic acceptance evidence. Do not silently decode v1
and v2 receipt layouts under one format version.

No migration, adoption, or repair path is added. If the team elects to preserve v3 receipts, it
must instead implement an explicit version-tagged decoder and state exactly whether v1 receipts are
replayable, read-only, or refused. That is a hard decision before production integration.

## 9. Files and ownership

First compiler-only round:

- `capability.rs`: private warrant-basis representation, private feasibility constructor,
  `CommitCapability` read-only accessors, compile-fail tests.
- `pulse_compiler.rs`: sealed authorization snapshot interface and `authorize_intake` validations.
- `intake.rs`: expose only the immutable getters/compiler validation constants needed by the
  compiler; no capability issuance.

Production integration round after interface review:

- `store.rs`: real sealed snapshot constructor, consume `CommitCapability`, v4 receipt schema,
  LMDB validation and atomic ledger. Terra ownership.
- `ops.rs`: replay → policy → compiler issuance → store consumption orchestration. Sol ownership.
- harness: no new authority mechanism; it continues to provide the trusted local
  `RatifiedChannel`. Sol ownership.

`contract.rs`, reference models, and public docs must be updated only after the authoritative path
works; they must not claim convergence from compiler-side types alone.

## 10. Acceptance tests

### Compiler-focused synthetic tests

1. Valid immutable Reported/System/Simulated requests receive `CommitCapability` without any
   arbitration score.
2. Wrong fresh channel, empty issuer, wrong scope/class, wrong realm, and stale epoch refuse before
   capability issuance.
3. World cannot be represented by `IntakeKind`.
4. Content, source, item ordinal, operation ID, epoch, realm, issuer, or kind changes alter the
   manifest digest and cannot match the issued capability.
5. Capability is not constructible, cloneable, serializable, `Send`, or `Sync`.
6. Scored arbitration tests remain unchanged and continue enforcing Law 8 thresholds.
7. A digest-only public or crate-wide mint function does not exist; static scan permits the
   feasibility constructor only at the compiler call site.

### Production integration tests

1. Authenticated replay returns before compiler issuance; an issuance counter/test hook remains
   unchanged.
2. Store rejects a capability bound to a different request, authority, scope, realm, epoch,
   operation ID, or operation kind with zero writes.
3. Every LMDB injected rollback point leaves no nullifier, receipt, epoch, allocator, record, or
   posting effect.
4. Concurrent identical operations yield one commit and one matching replay; concurrent changed
   payloads under one operation ID yield one commit and one conflict.
5. No capability JSONL journal is created or modified by LMDB intake.
6. Reopen returns the same receipt and validates its compiler binding.
7. Existing Slice 1 compatibility, epistemic, build-boundary, and closure scans remain green.

## 11. Explicit limits and unresolved choices

This plan does not authorize relation creation, lifecycle transitions, sweep, vectors, embedding
cache, migration, real stores, historical data, model calls, packaging, deployment, or release.

Hard choices still requiring resolution before production integration:

1. **Format transition:** adopt v4/v2 fresh-only receipts as recommended, or implement explicit
   mixed-version decoding.
2. **Statutory proof placement:** retain budget/noise/in-memory duplicate checks in `ops.rs` before
   compiler issuance for this slice, or design sealed statutory evidence. This must not change
   current policy behavior.
3. **Candidate identity compatibility:** legacy arbitrated warrants expose numeric candidate and
   sequence IDs; feasibility warrants expose `OperationId`. Generic accessors must avoid inventing
   fake candidate/sequence values.
4. **Compiler naming:** the current production compiler surface is `PulseTree`; the new narrow
   feasibility function may be module-level or live on a sealed `PulseCompiler` facade. Either way,
   only that module may invoke the private feasibility warrant constructor.

Passing compiler-only tests proves issuance topology, not authoritative integration. Gate 9A
authority convergence is achieved only after LMDB consumes and validates the compiler-issued
`CommitCapability` and the expanded adversary/acceptance battery passes.
