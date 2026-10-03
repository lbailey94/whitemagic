# Gate 9A ratification amendment — 2026-09-22

Status: **operator-ratified amendment** (Lucas, 2026-09-22) to the four sweep ratifications recorded
2026-09-21 (`receipts/GATE_9A_SWEEP_DECISIONS_OPTIONS_2026-09-21.md`) and reconciled in
`receipts/GATE_9A_RATIFICATION_RECONCILIATION_2026-09-22.md`. This amendment supersedes D1 and D2
of those records as follows; D3 (fresh-only v5 tagged envelope) and D4 (typed disabled no-op,
explicit auto-sweep disposition) stand as reconciled. It does not itself close Gate 9A.

## A1. D1 — Slice 1 qualification profile v1 (RATIFIED)

The eight-dimension profile from `receipts/GATE_9A_SWEEP_SIZING_2026-09-22.md` is ratified as
**Slice 1 qualification profile v1**:

| Dimension | Ratified value |
|---|---:|
| records scanned | 256 |
| raw record bytes (aggregate) | 16 KiB |
| raw bytes per record | 1 KiB |
| posting bytes decoded | 2 KiB |
| token occurrences | 1,024 |
| relations scanned | 256 |
| pair examinations | 8,192 |
| emitted effects | 1,024 |

Attached semantics (binding):

- Hard refusal only, never truncation. Typed `SweepTooLarge`/limit error; **no canonical
  mutation and no consumed operation ID** on refusal.
- The eight values are bound into the request and receipt policy digest as profile `v1`. Changing
  any value requires a registered profile bump plus fresh sizing evidence; never silently raise a
  constant.
- **Scope: qualification, not capacity.** These ceilings will refuse most real content (1 KiB
  per record, 16 KiB aggregate). That is expected fail-closed behavior for this slice and must not
  be represented as production capacity in 9B/9C or user-facing copy.
- The eight dimensions are floors, not the whole bound: the planner must also bound temporary
  candidate/index collections, repeated pair visits (not only unique pairs retained), and usage
  snapshot entries before allocation (guide hint 3).
- Acceptance requires at-bound success and one-over refusal for **every** dimension, including
  oversized single payloads, with reopen proving no durable effects after refusal.

## A2. D2 — usage-dependent lifecycle preserved with volatile evidence (RATIFIED: option b)

Lifecycle behavior is preserved as implemented (`ops.rs:1455–1488`: used Candidate promotes; used
Persistent stays; unused Persistent with age ≥ 3 sweeps demotes), carried by an explicitly
volatile, trusted process-local usage snapshot, under these binding conditions:

1. **Evidence persists with the plan.** The sealed original request (already carrying the bounded
   usage snapshot entries, process identity, sequence and digest via `sweep.rs`
   `VolatileUsageSnapshot`) is persisted in the receipt/ledger (`SweepReceipt.sealed_request`) so
   an auditor can reconstruct the decision after restart even though the process lineage is gone.
   The usage entry list must be explicitly bounded by the profile (see A1) before production
   availability — current `SweepRequest::validate` does not bound it.
2. **Replay never recomputes.** Replay retrieves the original sealed plan by operation ID, decodes
   it inertly (no `Deserialize` authority shortcuts), validates receipt/plan/ledger binding, and
   commits it as-is. A new process's fresh usage identity must neither block replay of a committed
   operation nor cause re-planning from new usage. A differing concurrently-planned request for
   the same operation ID is a replay/conflict outcome, not corruption.
3. **Disclosure is explicit.** Receipts carry
   `evidence_basis = process_local_volatile`, `restart_persistent = false`, and the process
   identity/sequence. Receipts must not imply durable usage history.
4. **Restart sensitivity is tested and disclosed.** A Persistent relation whose only usage
   evidence predates a restart can be demoted once the durable age threshold is met. This is
   documented slice behavior, covered by an executable test, and stated in the closure verdict.
   The verdict must describe lifecycle as a function of canonical state plus process-local
   observation: attributable via receipt, not independently reproducible after restart.
5. **Durable usage lineage is out of scope.** Any durable usage record/writer is a separately
   registered follow-on operation (e.g. `wm.gen3.lifecycle.v1`), not this slice; no silent new
   canonical usage writer may be introduced.

## A3. What this unblocks

- A production `SweepProfileV1` constant set in `sweep.rs` (replacing the review-only posture),
  while `PRODUCTION_SWEEP_PROFILE_AVAILABLE` may only flip once the trusted planner exists.
- The trusted bounded planner (coherent read snapshot, planner-derived observations/effects,
  bounds checked before allocation, usage snapshot from the process-local issuer).
- The v5 fresh-only store integration, validated replay recovery, and ops/harness wiring per
  `docs/GATE_9A_FINISHING_GUIDE.md`.

Operator: Lucas. Recorded by the verifier lane (opencode) as decision support; implementation
ownership remains per the finishing guide. No code was changed by this amendment.
