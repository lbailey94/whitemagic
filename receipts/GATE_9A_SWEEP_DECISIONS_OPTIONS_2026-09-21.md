# Gate 9A sweep decisions — options memo — 2026-09-21

Status: external decision-support artifact, prepared by the verifier (opencode) for the
coordinator/operator. It does not decide policy, modify code, or change gate status. It assumes
`docs/GATE_9A_SWEEP_TRANSACTION_PLAN.md` (Terra) and `docs/GATE_9A_AUTHORITY_CONVERGENCE_PLAN.md`
(Sol) as the current design baseline, and cites the current working tree only.

The four blocking decisions from `docs/GATE_9A_CLOSURE_CHECKLIST.md` are addressed below with
concrete options, source facts, and consequences. Recommendations are marked; each remains an
operator/coordinator ratification, not an inference from current defaults.

## D1. Hard candidate/effect bound for one sweep transaction

Source facts: `Policy::pair_budget` is mutable and has no maximum; lifecycle iterates every durable
relation (`ops.rs:1314–1490`); the plan already rejects an unbounded one-transaction claim.

Options:
1. **Hard constants + refusal (recommended for v1).** Register frozen `MAX_SWEEP_EFFECTS` and
   `MAX_PAIR_EXAMINATIONS` in the sweep policy/version digest; if the computed effect list or
   examination count exceeds either, return `SweepTooLarge` with **no canonical mutation** and no
   consumed operation identity. Simple, fail-closed, auditable; large stores sweep only after the
   bound is raised by a registered policy change.
2. **Deterministic truncation.** Same constants, but truncate by the existing sorted candidate
   stream and ascending relation ID, committing the truncated list. Retains progress on large
   stores, but silently changes sweep coverage per epoch and needs its own receipt semantics
   ("truncated" flag and continuation identity).
3. **Bounded windowing across multiple operations.** Each operation covers a deterministic slice
   with its own operation ID; completeness is only reached after N operations. Most complex;
   defer unless (1) proves operationally insufficient.

Consequences to record either way: the chosen constants must be ratified (the current
`pair_budget = 200_000` default is not a bound), included in the policy digest so replay/read-set
validation covers them, and tested for oversize refusal without partial mutation.

## D2. Lifecycle evidence (promotion/demotion)

Source facts: promotion/demotion currently read `self.usage`, an in-memory map incremented by
recall and never persisted; recall itself is not a canonical mutation (`ops.rs:1455–1485`).
Journal events are audit side effects, not evidence.

Options:
1. **Durable usage snapshot bound to the manifest.** Define what durable state counts as "used"
   (for example, a committed usage record written through an authorized operation, or a signed
   operator-supplied snapshot), bind its digest into the sweep request, and validate it in the
   transaction. Preserves behavior, but introduces a new evidence source that needs its own
   registration and write authority before it can be trusted.
2. **Exclude usage-driven transitions from this slice (recommended for the immediate slice).**
   Commit only transitions derivable from durable canonical state; leave promotion/demotion as a
   separately registered follow-on operation (for example `wm.gen3.lifecycle.v1`) with an explicit
   evidence contract. Honest and implementable now, but the closure verdict must state that
   usage-driven lifecycle is excluded and the gate remains partial for that behavior.
3. **Hybrid: durable rule for demotion, excluded promotion.** Demotion ("unused for K sweeps") can
   be expressed from durable `created_sweep` + current sweep ID alone; promotion ("used") cannot.
   Gives a real lifecycle transition inside the bounded slice without volatile evidence, at the
   cost of asymmetric semantics that must be documented.

Note: the checklist's warning stands — disabling a required behavior is not proof the full gate
passed. Any exclusion under option 2 or 3 must appear in the closure verdict and in the 9B/9C
follow-on register.

## D3. Receipt schema and compiler binding compatibility

Current direction (execution plan): fresh-only store format **v4** and receipt **v2** with explicit
compiler bindings; v3 stores refuse; no migration, no silent reinterpretation.

Concrete schema requirements to ratify:
- Receipt v2 carries an explicit version discriminator plus the operation kind, so a v3-era receipt
  byte string can never decode as v2.
- Intake receipt v2 fields: operation ID, realm ID, expected/committed epoch, authority descriptor
  digest, manifest digest, operation kind (`remember`), record ID, disposition, effect digest.
- Sweep receipt fields per the plan: pre/post epoch, assigned sweep ID, ordered relation-ID range or
  explicit IDs, effect count/digest, per-effect outcome digest, policy digest, bounds decision.
- Capability binding fields stay exactly those revalidated in `store.rs:493–525` (digest, scope,
  operation ID, realm, expected epoch, authority digest, operation kind) plus the sweep-specific
  fields; no wildcard scope.
- Nullifier key stays the operation ID; one-sided nullifier/receipt state remains
  `CorruptCommitState`.

Consequences: existing v3 stores refuse to open through the supported path (acceptable; migration
is 9D), and the refusal-preservation test must cover v3 stores byte-for-byte as Slice 1 did for
unsupported formats. The decision between "additive receipt v2 in a v4 store" and "v4 + v2 only"
should be made once, in the contract, before either implementer writes bytes.

## D4. Disabled sweep semantics and legacy automatic sweep

Source facts: `ops.rs:1314` allocates `META_SWEEP` via `unwrap_or(0)` **before** checking
`sweep_enabled`; a disabled sweep still consumes an ID and a store refusal is masked to ID 0
(the counter is now fail-closed, so `unwrap_or(0)` hides a typed error). The harness batch route
runs `think_sweep` after `remember_batch` (`crates/wm-gen3-harness/src/main.rs:286`); the
authorized intake route does not sweep.

Options:
1. **Disabled sweep = journaled volatile no-op, no allocation (recommended).** Move allocation
   after the enabled check and propagate counter errors. Requires compatibility approval because
   it changes current pre-disabled bump behavior; matches the plan's stated intent.
2. **Legacy automatic sweep: remove from production routes (recommended for the shell).** The
   compatibility layer calls the explicit sweep operation with its own operation ID and authority
   when it wants a sweep; no post-ingest side effect.
3. **Legacy automatic sweep: keep, but as a separately authorized operation.** Requires a distinct
   operation kind and compiler-issued authority supplied by the caller; must never reuse the intake
   operation's authority or run unreceipted.

Minimum no-regret fix independent of the policy choice: replace `alloc_sweep().unwrap_or(0)` with
an error-propagating call placed after the enabled check, and add the no-mask test from the
coverage map (missing tests item 7).

## Suggested ratification order

D3 (schema) and D4 (disabled/legacy semantics) unblock Sol's authority framing and the harness
compatibility wrapper; D1 (bounds) and D2 (lifecycle evidence) unblock Terra's transaction and the
sweep acceptance cases. If only one can be ratified now, ratify D4 first — it is a two-line code
change with an immediate fail-closed improvement and no schema dependency.
