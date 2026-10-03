# Gate 9A ratification reconciliation — 2026-09-22

Status: external decision-support artifact, prepared by the verifier (opencode) for the
coordinator/operator. It does not decide policy, modify code, or change gate status. It reconciles
the four sweep ratifications recorded 2026-09-21 evening (see
`receipts/GATE_9A_SWEEP_DECISIONS_OPTIONS_2026-09-21.md`) with the coordinator's direction in
`receipts/GATE_9A_MORNING_DISPATCH_2026-09-22.md` and the continuation state in
`docs/GATE_9A_FINISHING_GUIDE.md`. Read all three together with
`docs/GATE_9A_CLOSURE_CHECKLIST.md` (same 1–4 numbering) before implementing.

## Verified working-tree state (read-only, 2026-09-22 mid-morning)

- HEAD `981b0bf`; all work uncommitted: 11 modified files, +2465/−215, plus new
  `crates/wm-gen3-core/src/intake.rs`, `crates/wm-gen3-core/src/sweep.rs`, tests, docs, receipts.
- `receipts/gate9a_handoff_20260922/source-manifest.sha256`: 16/16 hashes verify against the
  current working tree.
- `crates/wm-gen3-core/src/sweep.rs:21` `PRODUCTION_SWEEP_PROFILE_AVAILABLE = false`;
  `SweepLimits` has the eight dimensions including `max_raw_record_bytes` and
  `max_single_record_bytes` (sweep.rs:28–37).
- `crates/wm-gen3-core/src/ops.rs:1314` still calls `self.store.alloc_sweep().unwrap_or(0)` before
  the enabled check — the D4 no-regret fix is NOT applied.
- No fresh integrated suite was run for this reconciliation; test counts across receipts overlap
  and must not be summed (per finishing guide).

## Ratification ↔ lane state

| Ratified 2026-09-21 (opencode) | Lane state (guide / dispatch) | Disposition |
|---|---|---|
| **D1** Hard constants + refusal, never truncation; bind values into policy/version digest; oversize refuses with no canonical mutation and no consumed operation ID | Guide step 1: Terra proposes profile, coordinator reviews. Sizing receipt proposes 8-dim review-only starting ceilings (256 records, 16 KiB aggregate raw bytes, 1 KiB record, 2 KiB postings, 1,024 token occurrences, 256 relations, 8,192 pairs, 1,024 effects) | **ALIGNED in mechanism; values pending.** Operator ratifies or amends the numeric profile, records refusal semantics, and keeps configurable boundary tests separate from production maxima. Until ratified, the profile-available flag must stay false. |
| **D2** Exclude usage-driven lifecycle transitions from this slice (recommended), or hybrid demotion-only; any exclusion disclosed in the closure verdict | Dispatch: "Preserve current usage-dependent lifecycle semantics with explicitly volatile, trusted process-local snapshot evidence. Never substitute age-only demotion." Guide §2: same, with explicit restart-lineage disclosure | **DIVERGENT — operator decision required before planner work.** Either (a) keep the ratification: planner commits only durable-state-derived transitions; usage-driven promotion/demotion moves to a separately registered follow-on operation and the verdict discloses the partial scope; or (b) amend D2 to the volatile-snapshot design: behavior preserved, but receipts must disclose process-local evidence that is lost on restart, and no verdict may imply durable usage history. Do not implement the planner under ambiguous policy. |
| **D3** Fresh-only store v4 + receipt v2, explicit version discriminator, no migration/adoption of existing stores | Guide step 3 / dispatch: fresh-only **v5** tagged intake/sweep envelope, explicit version/kind, reject v4 and older, no mixed decoding; one operation-ID namespace per realm; nullifier stays the operation ID | **SUBSTANCE RETAINED; version superseded.** Amend the ratification wording to "fresh-only, version bumped when the common intake/sweep envelope lands (currently proposed v5); v4 and older refuse; no migration." Note the v5 envelope is proposal-only and NOT implemented — the store is still v4. |
| **D4** Disabled = journaled volatile no-op with no allocation (allocate after enabled check, propagate counter errors, never mask to ID 0); legacy auto-sweep removed from production routes (compatibility calls an explicit sweep with its own operation ID and authority) | Guide step 4 / dispatch: same direction — typed no-op, errors propagate never ID zero; auto-sweep either becomes an explicitly identified child operation/retry contract or returns documented `not_requested` | **ALIGNED; not applied.** Apply the two-line no-regret fix first (`ops.rs:1314` + no-mask test from the coverage map), then settle the auto-sweep disposition explicitly. |

## Second-order constraints the ratifications must respect

- Serialized plan bytes are not a validated replay implementation; no `Deserialize` on sealed
  authority types; decode inert data and require fresh authority at the replay boundary
  (guide hints 5–6). This constrains how D3's sweep receipt/plan binding is designed.
- Counts, effects and usage observations must be derived by the trusted planner; a digest only
  proves binding, not that the claimed observation occurred (hint 2). D1's policy digest and D2's
  usage binding are only meaningful if this holds.
- Enabled-but-empty sweep must be specified separately from disabled: even zero relation effects
  can advance sweep age and affect later lifecycle decisions (hint 7). This feeds D4's receipt and
  counter rules and D2's lifecycle policy.
- Receipts must carry the usage evidence/policy needed for audit (hint 9). Under D2 option (b)
  this means the volatile snapshot digest and the disclosure that it is not restart-persistent.
- Abort-after-each-stage and reopen tests must cover counters, epoch, nullifier and receipt
  (acceptance list in the guide), which the D3 schema must anticipate.

## Suggested resolution order

1. **D4 no-regret fix** — operational, no schema dependency; unblocks fail-closed behavior now.
2. **D3 wording amendment** to the fresh-only v5 direction — unblocks envelope implementation.
3. **D1 numeric profile ratification** — from `receipts/GATE_9A_SWEEP_SIZING_2026-09-22.md`.
4. **D2 decision (a) vs (b)** — before any trusted-planner implementation.
5. Then, per the finishing guide: trusted bounded planner → atomic v5 `commit_sweep` + validated
   replay → ops/harness wiring → fresh integrated evidence (exact hashes/features/results) →
   new closure verdict explicitly superseding historical headlines.

Ownership per the guide remains: Sol — sweep/compiler/types; Terra — bounded Store reads,
transaction/recovery; coordinator — integration and verdict; independent reviewer — evidence.
This receipt changes no code and no gate status.
