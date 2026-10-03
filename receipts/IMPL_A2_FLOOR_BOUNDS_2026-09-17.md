# RECEIPT — W1_A2 floor bounds fail-closed, implemented + demonstrated (2026-09-17)

**Status: DEMONSTRATED — 2026-09-17.** Implementation freeze, then wrapper-side demonstration.
AI session `c7ab9666-b4cc-4e87-a062-299467db4026` (opencode) implemented, ran, and attests.
Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Spec | `docs/specs/W1_A2_evidence_disclosure.md` (frozen; sha256 `aa84a5ac…`), adversarial case 1 |
| Implementation freeze | commit `41532c6` — `ops.rs` + harness `main.rs` (+124/−33, includes the churn of the signature change) |
| Binary demonstrated | `target/release/wm-gen3` sha256 `c6f87d623397ce8b28e67aac6f7b5aefb02c4875f0fc01a2ad85862e11fa4187` |
| Evidence bundle | `receipts/impl_a2_bounds_2026-09-17/` — `driver.py`, `responses.jsonl`, `journal.jsonl`, `SHA256SUMS` |
| Rung evidence | EXECUTED→EFFECTFUL (structured refusals; zero selection events for caller errors) |

## 2. What was implemented

- **`recall` is now Result-shaped:** `pub fn recall(&mut self, q: &RecallQuery) ->
  Result<Vec<Hit>, RecallError>`; `RecallError::InvalidFloor { field, value }` with `Display`
  ("must be within [0, 1] (fail-closed)").
- **Validation precedes selection:** out-of-range `min_score`/`min_coverage` (including `NaN`
  and `±Infinity`) are refused **before** tokenizing — so a caller error emits **no** journal
  events; in-range behavior is byte-identical (all prior tests pass unchanged in behavior).
- `recall_expect` (`#[cfg(test)]`, `#[track_caller]`) kept the test suites readable; the harness
  maps `Err` to `{"status": "error", "error": …}` — the structured caller error is surfaced,
  never silently filtered.
- The A2 receipt's previously disclosed gap ("a `Result`-shaped surface is required first") is
  closed.

## 3. Demonstration

Command: `python3 receipts/impl_a2_bounds_2026-09-17/driver.py target/release/wm-gen3 /tmp/opencode/a2b-demo`

| Step | Result |
|---|---|
| `min_score 1.5` | `status: error` — `invalid floor min_score=1.5: must be within [0, 1] (fail-closed)` |
| `min_score -0.1` | `status: error` — same shape, field named |
| `min_coverage 2.0` | `status: error` — `min_coverage=2` named |
| Control query (floors 0) | `status: success`, 1 result |
| Journal | exactly **1** `selection.decision` (the control); invalid calls journaled none |

## 4. Tests and gates (at the freeze commit)

- `cargo test --offline`: **34 passed / 0 failed / 1 ignored** (new:
  `floor_bounds_fail_closed` — boundary table `−0.01 / 1.01 / NaN / ±∞` refused, `0.0 / 0.5 /
  1.0` accepted; `invalid_floors_emit_no_selection_events`); doc-tests **5 passed**.
- `cargo fmt --all -- --check`: clean under the pinned 1.98.0; `check_closures.sh`: **PASS**.

## 5. Disclosed limitations (not claimed)

- **API is source-breaking** for downstream callers (`recall` returns `Result`); all in-repo
  call sites are updated (tests + harness). External consumers do not exist yet.
- **Caller errors are not journaled** — deliberate: they precede selection; adding a journal
  event for them would extend the frozen A2 vocabulary and requires a spec revision.
- Remaining A2 acceptance items stay open: read-only/starvation adversarial cases and
  degraded-route honesty (scheduled with the disclosure acceptance wiring).
- No ordering change (validation path only); ordering ablation still scheduled separately.

## 6. Consequences

- A2 adversarial case 1 (**out-of-range floors fail closed**) is implemented and demonstrated;
  the "silently disables the floor" defect class is structurally excluded.
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger 8 claims.

## 7. Attestation

AI session `c7ab9666` implemented the change (commit `41532c6`), ran the tests, gates, and the
wrapper-side demonstration, and prepared this receipt. Spec ratification is recorded in
`receipts/W1_SPEC_A2_FREEZE_2026-09-17.md`.
