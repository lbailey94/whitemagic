# Gate 9D Closure Verdict — Alpha Reality Test (Migration, Crash Cut-Points, Envelopes)

- **Draft Date:** 2026-10-07 (engineering closure recorded by opencode; operator ratification pending)
- **Target Architecture:** WhiteMagic Gen3 substrate (`crates/wm-gen3-core`: `compat`, `capability`, `pulse_compiler`, `store`; migration CLI in `wm-gen3-harness`)
- **Base Commit:** `2a923b4c60f97570551d4bcbb02c290ad474f77b` (10.2.0-alpha.5, `main`)
- **Operator / Authority:** Lucas (ratification pending)
- **Preregistration:** `docs/PREREGISTRATION_PEB15_AMENDMENT_GATE9D.md` (H9D-1…H9D-4, 5 write cut-points)
- **Status:** **ENGINEERING CLOSURE — CLOSED WITH SIMULATION CAVEATS, PENDING OPERATOR RATIFICATION**

---

## 1. Statutory Closure Verdict

Pursuant to `docs/CHARTER.md` and the Gate 9D amendment:

$$\boxed{ \textbf{GATE 9D (Alpha Reality Test) IS ENGINEERING-CLOSED — RATIFICATION PENDING} }$$

The reality battery passes under local re-execution on the base commit:
migration is faithful and strictly idempotent, corrupted Gen2 records are
quarantined with structured reasons and zero panics, capability replay after a
simulated crash is rejected fail-closed, a corrupted nullifier journal refuses
to open (`InvalidData`), and malformed/skewed envelopes are rejected. The
battery simulates abrupt termination with write-ahead fsync + reopen; a true
physical power-cut qualification is still not performed, and no CI-green run
has executed this battery on `main` yet.

## 2. Evidence

*Evidence class:* locally re-executed on the base commit (cargo 1.98.0 /
rustc 1.98.0, 2026-10-07T03:2xZ) plus CI run references.

| Verification | Command / scope | Result |
|---|---|---|
| **Local re-execution (9D battery)** | `cargo test --locked -p wm-gen3-core --features operator,reference-models --test gate9d_reality_battery -- --skip test_real_gen2_store_dry_run_and_idempotency_if_present` | **4 passed, 0 failed** (1 filtered: the host-specific real-store test, which self-skips when the path is absent); `test_h9d1_migration_fidelity_and_strict_idempotency`, `test_h9d2_cutpoint_cp1_to_cp5_crash_consistency`, `test_h9d3_dirty_store_tolerance_and_forensic_quarantine`, `test_h9d4_network_envelope_skew_and_protocol_defense` |
| **CI wiring** | `.github/workflows/ci.yml` step "Run gate batteries (reference-models)" | Present and mandatory; activates `adversary_contract` + this battery |
| **CI execution (alpha.5)** | [run 37562979314](https://github.com/lbailey94/whitemagic/actions/runs/37562979314) | `Tests (Linux)` terminated exit 143 (SIGTERM) during the preceding default-feature test step; **battery step skipped — not yet CI-green on `main`** |
| **Release integrity** | [run 37562982195](https://github.com/lbailey94/whitemagic/actions/runs/37562982195) | 10/10 jobs green for the same commit (not a battery execution) |
| **Static closures** | `bash scripts/check_closures.sh` (alpha.5 CI) | 3/3 PASS |

## 3. Hypothesis Results

- **H9D-1 (migration fidelity & idempotency): EVIDENCED.** 10/10 synthetic
  Gen2 records migrated with recall verified; re-run migrates 0 new records,
  reports 10 duplicates, and leaves the target epoch stationary.
- **H9D-2 (cut-point crash consistency CP1–CP5): EVIDENCED BY SIMULATION.**
  CP2 burned nullifier survives "crash" and replay fails with
  `ReplayAttackDetected`; CP3 independent burn; CP4 a truncated journal line
  makes `open_durable` fail closed with `InvalidData`; CP5 clean reopen
  restores epoch.
- **H9D-3 (dirty store & quarantine): EVIDENCED.** 4 clean migrated, 4
  damaged quarantined with `ContentHashMismatch`, `MsgPackDecodeError`,
  `InvalidKeyLength`, `EmptyContent`; zero panics.
- **H9D-4 (envelope skew defense): PARTIALLY EVIDENCED.** The test validates
  the rejection shape for unknown methods, forward version skew, and malformed
  JSON-RPC frames, and asserts no capability-less mutation path; it is not a
  live `wm serve` attack run.

## 4. Open Items & Caveats

1. **Crash testing is emulated, not physical.** Abrupt termination is
   simulated with drop + reopen and write-ahead `sync_data`; OS/power-loss
   durability on real hardware is not exercised. The 9A closure explicitly
   assigned "true physical power-loss qualification" to 9D — that stronger
   claim remains **open**.
2. **No CI-green battery execution yet** on `main` (alpha.5 CI run
   37562979314 died with exit 143 before the step; no assertion failure was
   recorded). Until a green run lands, the battery's CI status is "wired but
   unproven".
3. **H9D-4 is schema-shape validation**, not a live server fuzz; paired with
   the alpha.5 network hardening (bearer auth, loopback default, peer pinning)
   but not the same evidence.
4. **Real-store drill self-skips** when the WMv9 planning store is absent
   (the case on the CI runner); the local re-execution excluded it explicitly.
5. `migration_receipt.json` cryptographic strength ("cryptographic receipt")
   is hash-based provenance; it is not an Ed25519-signed artifact in the
   evidence reviewed here.

## 5. Transition

Gate 9B and Gate 9C verdicts are issued contemporaneously. Operator
ratification is the remaining statutory step; open items above are carried as
ratification conditions.
