# RECEIPT — W1_A2 explicit insufficiency vocabulary implemented + demonstrated (2026-09-17)

**Status: DEMONSTRATED — 2026-09-17.** Implementation freeze, then wrapper-side demonstration
(freeze-before-runs). AI session `c7ab9666-b4cc-4e87-a062-299467db4026` (opencode) implemented,
ran, and attests. Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Spec | `docs/specs/W1_A2_evidence_disclosure.md` (frozen; sha256 `aa84a5ac…`) |
| Implementation freeze | commit `a588ae1` — `crates/wm-gen3-core/src/ops.rs` (+63/−1) |
| Binary demonstrated | `target/release/wm-gen3` sha256 `0f8474330366a5131517ef5080357634dfbd241090280723a94db8d97770dbbf` (supersedes `09aefc42…` — A1 gate included) |
| Evidence bundle | `receipts/impl_a2_2026-09-17/` — `driver.py`, `responses.jsonl`, `journal.jsonl`, `SHA256SUMS` |
| Rung evidence | EXECUTED (abstention events) · EFFECTFUL (empty returns carry exactly one event; legacy token gone) |

## 2. What was implemented

- Closed reason vocabulary: `selection.decision.reason ∈ {no_query_tokens,
  insufficient_evidence}`; the legacy `no_candidates` token now appears only as
  `cause`, never as `reason` (the mapping recorded here, per the frozen spec).
- **Floor exclusion disclosed:** when declared floors exclude every candidate, recall returns
  zero hits **and** emits exactly one `insufficient_evidence` event with
  `cause = no_results_above_floors` (floors + candidate counts included). Previously this path
  emitted a reason-less empty (`abstained: true` only) — the silent-absence class the spec
  forbids.
- No ranking-path changes; floors still filter on `support`; **out-of-range floor validation
  remains unimplemented** (disclosed below).

## 3. Demonstration (wrapper-side, harness over stdio JSON-RPC)

Command: `python3 receipts/impl_a2_2026-09-17/driver.py target/release/wm-gen3 /tmp/opencode/a2-demo`

| Step | Result |
|---|---|
| Ingest `alpha beta gamma` | success, id 0 |
| Query `alpha zulu`, `min_score 0.9` | 0 results; journal `insufficient_evidence` / `no_results_above_floors`, `lexical_candidates: 1`, floors recorded |
| Query `zulu` (no candidates) | 0 results; journal `insufficient_evidence` / `no_candidates` |
| Control query `alpha` (floors 0) | 1 result (id 0) — disclosure fires only when needed |
| Legacy check | no `reason == "no_candidates"` anywhere in the journal |

`SHA256SUMS` (bundle): `driver.py` `7000465b…` · `responses.jsonl` `95efc6fe…` · `journal.jsonl`
`664ef6e6…`; binary `0f847433…`.

## 4. Tests and gates (at the freeze commit)

- `cargo test -p wm-gen3-core --offline`: **32 passed / 0 failed / 1 ignored** (new:
  `floors_exclusion_is_disclosed_as_insufficient_evidence`,
  `no_candidates_discloses_insufficient_evidence`); doc-tests **5 passed**.
- `scripts/check_closures.sh`: **PASS**.
- `cargo build --release --offline`: clean.

## 5. Disclosed limitations (not claimed)

- **Out-of-range floor validation not implemented** (A2 adversarial case 1): the recall API
  returns `Vec<Hit>` and carries no structured-error channel; a `Result`-shaped surface is
  required first. Open unit.
- **Read-only/starvation adversarial cases not exercised** in this slice (scheduled with the
  disclosure acceptance wiring).
- **fmt drift**: pre-existing (repo-wide under local `rustfmt 1.9.0-stable`); not touched.

## 6. Consequences

- A2's first two contract points (explicit insufficiency; one vocabulary) are implemented and
  demonstrated; remaining A2 acceptance items stay open (floor bounds; read-only; starvation;
  degraded-route honesty).
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger 8 claims.

## 7. Attestation

AI session `c7ab9666` implemented the change (commit `a588ae1`), ran the tests, gates, and the
wrapper-side demonstration, and prepared this receipt. Spec ratification is recorded in
`receipts/W1_SPEC_A2_FREEZE_2026-09-17.md`.
