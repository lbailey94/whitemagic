# Gate 9A convergence independent verification — 2026-09-21

Status: independent verification of the **uncommitted in-flight authority-convergence candidate**.
This is not Gate 9A closure, not an acceptance of the sweep/relation work, and not a qualification
of the M0–M8 packaged-regression obligation. No implementation file was modified by this pass.

Base commit: `981b0bfac7acefb383ef86ef64699e32545c7849` (unchanged; all work below is working-tree only).
Verifier: external agent (opencode / deepseek-v4.1-flash), at the operator's request, acting in the
independent verification-lead role described in `docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md`.
Toolchain: `rustc 1.98.0 (88d9e12ae 2026-08-18)` / `cargo 1.98.0 (797e8a9bc 2026-08-05)`.

## Why this pass was run

The Slice 1 receipt (`receipts/GATE_9A_SLICE1_ACCEPTANCE_2026-09-21.md`) qualified an earlier
candidate whose production intake issued a local `IntakeCapability`. After that receipt, the
working tree changed: intake was converged onto the compiler-issued `CommitCapability` path
(`ops.rs` → `pulse_compiler::authorize_intake` → `store::commit_intake`), the local
`IntakeCapability` type was removed, and counter hardening landed. Those changes were not yet
verified as an integrated candidate. This pass re-ran the documented battery against the current
tree.

## Checks and results

All commands run from the repository root, offline and locked, on the working tree identified by
the source manifest below.

| Check | Command | Result |
|---|---|---|
| Release harness build | `cargo build --release --offline --locked -p wm-gen3-harness` | Passed |
| Filtered workspace suite | `cargo test --workspace --offline --locked --features wm-gen3-core/reference-models -- --skip projection::tests --skip ops::gated_tests` | **180 passed, 0 failed**, 1 ignored, 5 filtered |
| Storage suite | `cargo test --offline --locked -p wm-gen3-core store::tests -- --nocapture` | 6 passed, 0 failed |
| Default core build | `cargo check --offline --locked -p wm-gen3-core --no-default-features` | Passed |
| Production feature tree | `cargo tree --offline --locked -p wm-gen3-harness -e features` | `operator` enabled; `reference-models` absent |
| Closure static scans | `bash scripts/check_closures.sh` | Both scans passed |
| Process-boundary scenarios | `python3 scripts/check_slice1_harness.py target/release/wm-gen3` | **8 of 8 passed** (same eight scenario names as the Slice 1 receipt) |
| Whitespace | `git diff --check` | Passed |

Suite composition: 165 core unit + 3 adversary-contract integration + 1 public-API intake
integration + 2 harness unit + 9 documentation tests. The one ignored test is
`projection::a3_diagnostic::a3_diagnostic_ungated_cosine`; the five filtered tests are the four
`ops::gated_tests` projection-gate tests plus `projection::tests::genericity_battery` (the
model/projection-dependent group).

All PEB benchmark tests (PEB-0 through PEB-14C) executed inside the filtered workspace suite and
passed on this tree, including `test_peb0_minimality_benchmark_execution`,
`test_peb14a_benchmark_battery_execution`, `test_peb14b_benchmark_battery`, and
`test_peb14c_benchmark_battery`. The Python drivers in `benchmarks/` were not executed as drivers;
they invoke these same `cargo test --lib` targets (see the coverage map for the full mapping).

## Observations

- **Doc-test count drift is explained.** The Slice 1 receipt reported 13 doctests; this tree runs 9.
  The four missing doctests were the `intake::IntakeCapability` compile-fail blocks, removed together
  with that superseded type. `CommitCapability` retains its four compile-fail doctests
  (`capability.rs:277–296`), and constitution/evidence doctests are unchanged. No protection was
  silently dropped.
- **Binary identity changed as expected.** Slice 1 binary `8e277776…`; this tree rebuilds to
  `6ac82a41…`. The old binary no longer represents the tree.
- **One new API hazard worth review (AMBER).** `VerifiedWarrant` accessors
  (`candidate_id`, `composite_margin`, `estimated_risk`, `epistemic_status`, `sequence_id`,
  `token_digest`) now `.expect(...)` on `Option` fields that are `None` for feasibility warrants.
  Calling them on an intake warrant panics instead of refusing. No current production caller does
  this, but the public surface is panic-prone by construction (`capability.rs:198–237`).
- **Masked error path (AMBER, pre-existing).** `ops.rs:1314` still evaluates
  `self.store.alloc_sweep().unwrap_or(0)` before the `sweep_enabled` check. With the now fail-closed
  counter, a store refusal would be silently substituted with sweep ID 0, and a disabled sweep still
  consumes an ID. This is the sweep gap, restated with its current behavior.

## What this pass does and does not establish

- Establishes: the current tree compiles in release and default configurations, the filtered suite
  is green on the converged ingestion path, the storage suite is green, static closure scans pass,
  and the eight synthetic process-boundary scenarios pass against the rebuilt binary.
- Does not establish: sweep/relation authorization or atomicity, derived-cache boundaries,
  executable coverage for every Evil Gana attempt, the M0–M8 obligation against a packaged release
  artifact, unfiltered model-suite qualification, migration/power-loss behavior, or Gate 9A closure.
- The candidate remains uncommitted; the base hash alone does not identify it.

## Candidate and evidence hashes

- Release binary `target/release/wm-gen3`: SHA-256 `6ac82a4135970f9f17dd698a19e4dd8d2e561f4d2d8f53cce201319fc0c337d0`.
- [Source manifest](gate9a_convergence_20260921/source-manifest.sha256) (23 files, working tree):
  SHA-256 `feeaec71ccd153a75237ce7add5746908f502051dbba05317d636dd7d137df6a`.
- Working-tree diff digest (`git diff | sha256sum`): `29e7d917ac4a8486f9ebbc55aaaa240faea942d2a6857023dc94e4b2d8049e5a`.

| Evidence log | SHA-256 |
|---|---|
| [workspace-tests.log](gate9a_convergence_20260921/workspace-tests.log) | `acc7207acf57e2a7ad1de27323588d6254d84b46f8d7e33f38cf0fb6692632be` |
| [store-tests.log](gate9a_convergence_20260921/store-tests.log) | `3f991cae94a1eb0e4fdfb1472e672db5344c271b8e9b55551b73cc195a11194a` |
| [release-build.log](gate9a_convergence_20260921/release-build.log) | `15e50e1eb145986e98ff1d40c6d53b89a68a04d71d6e22cbee26fbd4eca896b6` |
| [harness-smoke.log](gate9a_convergence_20260921/harness-smoke.log) | `caa758976b0e9f01d6b6217df63a4f3ea561ce7811a0cd83db769cf98802bfa1` |
| [default-core-check.log](gate9a_convergence_20260921/default-core-check.log) | `a5887e1c4948c7b416c989ef310d2120aff52ab7094dcb1cb9b829543d9a1b3b` |
| [harness-features.log](gate9a_convergence_20260921/harness-features.log) | `6b4e395d7d2ed982f2dff1493c542452035e1898593f831509cc621b7e73cd3c` |
| [closures.log](gate9a_convergence_20260921/closures.log) | `6d4b8340d7515de8333105610008bdaa5892eaaec5f8c427f0566f670c891d2e` |

Raw logs are local evidence files (gitignored `*.log`) and must travel with this receipt.
