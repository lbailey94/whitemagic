# Gate 9A Terra morning prep — 2026-09-21

**Status:** night-close planning only. No source implementation, test execution, real store,
model, migration, or benchmark was performed. This is not a limit ratification or a Gate 9A
closure claim.

## Why the current sweep is not resource-bounded

`Substrate::think_sweep` allocates a sweep before it checks `sweep_enabled`
(`crates/wm-gen3-core/src/ops.rs:1312-1336`). When enabled, it materializes all records,
retokenizes every record into `BTreeMap<String, Vec<u64>>`, and reads every posting list through
`df` before the current mutable `Policy::pair_budget` is applied (`1338-1357`, `39-66`). It then
materializes all relations into a duplicate-pair set (`1359-1365`), and, with projection enabled,
all vectors (`1370-1378`). The pair cap is only reached after lexical candidate enumeration begins
(`1391-1425`), while lifecycle then reads every relation a second time (`1455-1485`). Existing
errors are also converted to empty inputs or ID zero at these boundaries. Therefore an effect-only
or pair-only limit cannot support a bounded-read/materialization claim.

The first storage slice must remain projection-disabled. It must never use age alone for demotion:
the present rule demotes only when `!used && age >= 3`; `used` is the volatile recall map updated
at `ops.rs:1237-1241`. An age-only substitute would demote relations current behavior preserves.

## Small synthetic sizing matrix and measurement

Generate deterministic temporary LMDB fixtures, with projection disabled and no model inputs.
Vary one dimension at a time around small, medium, and stress values; then combine the two most
amplifying dimensions (token expansion and shared-posting fan-out).

| Dimension | Fixture control | Capture before issuance |
|---|---|---|
| Records scanned | number of fixed-shape records | count and serialized record bytes |
| Content bytes | fixed record count, short/medium/long content | total and max content bytes |
| Token expansion | repeated, distinct, and adversarial token-rich content | token occurrences and unique terms |
| Postings | controlled shared-term fan-out | bytes decoded and posting IDs examined |
| Relations | candidate/persistent/cold relations | relations decoded, bytes, and lifecycle candidates |
| Pairs/effects | deterministic shared tokens and preexisting pairs | lexical pairs, examined pairs, ordered effects |

Instrumentation belongs in an in-memory preflight measurement object, not the LMDB schema: exact
counts/bytes, peak collection lengths, elapsed preflight time, and an effect digest. Persist only
the ratified limits/policy digest and accepted measurement summary in the eventual receipt. Select
provisional values only after repeated synthetic runs establish a stated machine envelope and a
conservative headroom rule; no present source evidence justifies numeric constants. The current
`pair_budget = 200_000` is mutable workload configuration, not evidence for any constitutional
maximum.

## First implementation step after ratification

Implement a pure, projection-disabled sweep **preflight** that returns either a measured,
canonical-order `SweepRequest` or `SweepTooLarge`, with no Store writes. It must count/refuse:
records, postings bytes, token occurrences, relations, pair examinations, and effects. On every
refusal it returns before compiler issuance and consumes no operation ID. Do not add
`commit_sweep` until the request/receipt encoding is agreed.

Sol dependencies: immutable private-field `SweepRequest`; canonical `SweepLimits`; framed digest
over operation ID, realm, epoch, ordered effects, policy/limits digest, and usage-snapshot digest;
compiler `authorize_sweep` using the existing `CommitCapability` with a distinct scope/kind; and
a v4-compatible, explicitly discriminated sweep receipt. The volatile snapshot must bind process
instance ID, monotonic sequence, and canonical ordered relation usage counts; it remains
process-local evidence and must say so in the receipt. No `SweepCapability`, age-only demotion,
or invented receipt version/limit belongs in the first patch.

## Morning acceptance cases

1. Each one-over preflight limit (including posting bytes and token occurrences) refuses with no
   counter, epoch, relation, nullifier, or receipt change after reopen.
2. A just-under deterministic fixture yields identical measurement and ordered-effect digests on
   repeated runs; preexisting relation pairs are excluded deterministically.
3. Projection enabled is refused for this slice before scan/issuance; no vector/cache reads are
   used by the accepted path.
4. Usage snapshot semantics preserve the current truth table: used candidate promotes; used old
   persistent does not demote; unused old persistent may demote only when its bound volatile
   snapshot says zero.
5. Disabled sweep and every preflight read/decode error return a typed result with no canonical
   mutation. The existing `SweepStats { sweep: u64 }` compatibility decision is still open.

**Blocking choices:** frozen numerical limits and headroom method; receipt/manifest discriminator
within format v4; disabled/error API and legacy harness auto-sweep behavior; whether process-local
usage is acceptable for lifecycle or lifecycle is deferred pending durable usage evidence. These
must be ratified before storage transaction code.
