# RECEIPT — W1_B4 claims & calibration acceptance demonstrated (2026-09-18)

**Status: evidence — acceptance demonstrated; row exit criteria met.** AI session
`221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Spec
`docs/specs/W1_B4_claims_belief_class.md`. Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_w1_b4_2026-09-18/` (3 files) |
| **SHA256SUMS** | `dea2091f06bd7e2b6dbdadac9befb7afd6a6fe0e06f3a1719882fa7edb657f8e` |
| Gen3 Binary | `target/release/wm-gen3` (sha256 `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| Simulation Test Suite | `WHITEMAGIC/WMv9/target/debug/deps/wm_simulation-1086e7febaed81a9` |
| Tools Test Suite | `WHITEMAGIC/WMv9/target/debug/deps/wm_tools-8ba6399ac8e6dfca` |
| Driver | `driver_w1_b4_claims.py` |
| Results Log | `claims.results.txt` |
| Tip at run | `6f29cfc` |

---

## 2. Acceptance Criteria Demonstrated (Spec §5)

| # | Item | Result |
|---|---|---|
| 1 | **Resolution completeness (§5.1)** | **PASS**: Every resolved claim carries a concrete validation event (`ValidationEvent`), date, and provenance source (`resolve_validated_credits_lead_weeks`, `resolve_falsified_is_recorded_as_miss`). Resolution evidence pointer rate is 100%. Resolution is irrevocable (`cannot_resolve_twice`), and miss outcomes are recorded explicitly as falsified claims without oracle confounding. |
| 2 | **Calibration reproducible (§5.2)** | **PASS**: Brier score (0.1350), calibration gap (−0.1000), hit rate (0.7500), mean confidence (0.6500), Wilson 95 score interval, and empirical-Bayes shrinkage weight ($w = n/(n+20) = 4/24 \approx 0.1667$) exactly match recomputed statistics from raw records to $10^{-12}$. Raw confidences are preserved unmodified on disk; calibrated values are reported alongside. |
| 3 | **No destructive sync fixture (§5.3)** | **PASS**: Independently recorded rows survive seeding/curation runs (0 rows deleted); v26 destructive deletion class is permanently excluded. |
| 4 | **Expiry universe (§5.4)** | **PASS**: Pinned statutory handling: expired claims are treated uniformly and never scored with contradictory ad-hoc penalties. |
| 5 | **Durability (write-through) (§5.5)** | **PASS**: Claims mutations (`add`, `resolve`) execute synchronous write-through to disk (`claims_write_through_persists_on_every_mutation`); an ungraceful process kill loses zero data. |
| 6 | **Universe labels & Anti-Bloat Canon (§5.6, §1.1)** | **PASS**: Calibration reports explicitly name the claims-ledger resolved set (distinguishing from self-model metric, v26 runtime ledger, and citta CRPS). Gen3 Part 1 Invariant 9 enforced: belief != evidence. All Gen3 static closure checks PASS. |

---

## 3. Adversarial Cases Demonstrated (Spec §3)

1. **Destructive sync (§3.1)** — PASS: independent rows survive; deletion count is zero.
2. **Degenerate calibration (§3.2)** — PASS: empty ledger yields identity calibration; all-validated/falsified sets disclose boundaries.
3. **Free-text validation (§3.3)** — PASS: free-text `validation_ref` or name regexes excluded; structured validation events required.
4. **Points reproducible (§3.4)** — PASS: lead time re-derives exactly from `(validation_date - source_date) / 7.0` in weeks.
5. **Oracle confound (§3.5)** — PASS: followed-guidance separable from outcome.
6. **Confidence bounds (§3.6)** — PASS: confidence validated in $[0, 1]$; out-of-range inputs fail-closed.
7. **Durability (§3.7)** — PASS: write-through verified; mutations persist before return.
8. **Read-only discipline (§3.8)** — PASS: status, list, and calibration are read-only.
9. **Universe naming (§3.9)** — PASS: reports name claims-ledger resolved set explicitly.

---

## 4. Disclosures

- **Boundary Characterization (Epistemic Accountability)**: B4 establishes epistemic accountability—the system distinguishes possessing an evidence record from asserting a falsifiable predictive proposition with stated confidence, verified or falsified by empirical reality without rewriting history.
- **Constitutional Invariant vs. Statutory Parameter**: The constitutional invariant is: *Never rewrite original belief; derive calibrated belief from resolved history.* The empirical-Bayes prior sample weight ($k = 20.0$, `CALIBRATION_PRIOR_SAMPLES`) is an explicitly **statutory policy parameter**, not an immutable law of Gen3 physics. It remains versioned, replaceable, and experimentally justifiable across domains, horizons, or sample sizes.
- **Empty-Data Semantics**: On an empty ledger ($n=0$), the identity transform ($f \rightarrow f$) mathematically represents a neutral no-op, epistemically interpreted as `calibration_status = insufficient_data`; it must never be cited as validation of raw confidence.
- **Validation Provenance Scope**: A concrete `ValidationEvent` requires an event description, an epoch date, and a traceable provenance pointer (`source`); it does not require external public web disclosure (local/private cryptographically traceable sources are fully admissible).
- **Build Provenance**: Gen3 binary `target/release/wm-gen3` (hash `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) was invariant across this implementation, proving that Gen3 core relies on the compile-side belief-class contract without unearned claims bloat.
- All 21 native Rust contract assertions (12 in `wm-simulation`, 9 in `wm-tools`) and 6 high-level test suites passed with 0 failures.
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK.

---

## 5. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `driver_w1_b4_claims.py`, verified all acceptance criteria and adversarial cases, generated the bundle with `SHA256SUMS`, and records this receipt.
