# RECEIPT — W1_A2 read-only discipline + starvation/route disclosure, implemented + demonstrated (2026-09-17)

**Status: DEMONSTRATED — 2026-09-17.** Implementation freeze, then wrapper-side demonstration.
AI session `c7ab9666-b4cc-4e87-a062-299467db4026` (opencode) implemented, ran, and attests.
Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Spec | `docs/specs/W1_A2_evidence_disclosure.md` (frozen; sha256 `aa84a5ac…`), adversarial cases 7, 8, 9 |
| Implementation freeze | commit `e3c6c6d` — `store.rs` + `ops.rs` + harness `main.rs` + `docs/PHASE2_RUN_JOURNAL.md` (+252/−33) |
| Binary demonstrated | `target/release/wm-gen3` sha256 `e6e7ee06a935f2c0868abbba33aa6140b5a846a2104494ce9a774d4f3f52c828` |
| Evidence bundle | `receipts/impl_a2_discipline_2026-09-17/` — two drivers, five journals, results/stderr captures, `SHA256SUMS` (11 entries) |
| Rung evidence | EXECUTED→EFFECTFUL (refusals typed; store bytes unchanged by reads; route fields per decision) |

## 2. What was implemented

- **Read-only discipline (case 8):** `Store::open_readonly` (`MDB_RDONLY | MDB_NOLOCK` — the
  9.1.8 inspection pattern: no lock-file interaction, safe against a live or wedged writer);
  write guards on every mutator (`ensure_writable`); `Substrate::open_readonly`; harness
  `--readonly` (write routes `memory.batch_create` / `gen3.canary` / `sandbox.set_limits`
  refused per-route).
- **Starvation-vs-refusal (case 9):** verified by fixture — a budget refusal
  (`write budget exceeded (fail-closed)`) blocks nothing: reads stay open, and an empty read
  discloses `insufficient_evidence` (a token distinct from the refusal). Gen3 has no stress
  governor beyond the budget; the substrate states that honestly (no `WM_HOMEOSTASIS_FROZEN`
  analog to claim).
- **Degraded-route honesty (case 7):** `selection.decision` gains additive
  `projection_ran` / `projection_error` fields; `docs/PHASE2_RUN_JOURNAL.md` carries the
  additive-disclosure note (required fields and joins unchanged); the `projection.error`
  event remains the error carrier.

## 3. Demonstration

**Read-only** (`driver_readonly.py`): writer ingests 2 records and stays alive; read-only reader
→ recall succeeds (1 hit), write route refused, canary refused, **store bytes unchanged**
(hash before = after); writer SIGKILLed; read-only reader still succeeds (no lock interaction).

**Starvation + route** (`driver_starve_route.py`): budget 1 → second item refused
(`["write budget exceeded"]`); reads open (`alpha` 1 hit, `zulu` 0 hits); journal shows one
typed refusal and one `insufficient_evidence` (tokens distinct); projection on → latest
decision `{projection_ran: true, projection_error: false, semantic_candidates: 1}`.

## 4. Tests and gates (at the freeze commit)

- `cargo test --offline`: **38 passed / 0 failed / 1 ignored** — new:
  `readonly_substrate_reads_and_refuses_writes`, `budget_refusal_does_not_block_reads_and_stays_typed`,
  `projection_off_discloses_route`, `projection_on_discloses_route` (cache-gated skip);
  doc-tests **5 passed**.
- `cargo fmt --all -- --check` clean under the pinned 1.98.0; `check_closures.sh` **PASS**.

## 5. Disclosed limitations (not claimed)

- **NO_LOCK snapshot semantics:** safe against a live **idle** or wedged writer (demonstrated);
  coherence against a writer mid-commit is not guaranteed by MDB_NOLOCK — the WMv9 inspection
  trade-off, disclosed, not hidden. A future hardening could use read transactions with lock
  registration if torn-state concerns arise.
- **Journal schema note:** additive fields (required set unchanged); runs remain
  join-compatible; recorded in `PHASE2_RUN_JOURNAL.md` with date and rationale.
- **A2 case 2 (drift) is folded into A1's fixtures** — Gen3 has no separate derived index; its
  analog is transaction atomicity, scheduled with A1's crash-drift unit.
- **A2 case 6 (cold record):** no cold tier exists in the substrate; the disclosure lives on the
  Gen2 link side (`unavailable_cold_record`). Declared N/A here, not silently skipped.
- No ordering changes in this unit.

## 6. Consequences

- A2 acceptance status: cases 1 (floors, `IMPL_A2_FLOOR_BOUNDS`), 7, 8, 9 (this receipt)
  **demonstrated**; case 3 folded into A1; case 2 folded into A1; 4/5 are statute/wrapper
  obligations already wired; case 6 N/A. **The A2 row's substrate acceptance is complete.**
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger 8 claims.

## 7. Attestation

AI session `c7ab9666` implemented the changes (commit `e3c6c6d`), ran the tests, gates, and both
wrapper-side demonstrations, and prepared this receipt. Spec ratification is recorded in
`receipts/W1_SPEC_A2_FREEZE_2026-09-17.md`.
