# Gate 9B Closure Verdict — Compatibility Shell (`wm` CLI & Production Daemon)

- **Draft Date:** 2026-10-07 (engineering closure recorded by opencode; operator ratification pending)
- **Evidence Addendum:** 2026-10-07 — packaged-artifact evidence and legacy CLI audit,
  base `ef623fbd5e80d64a47c3335e99a34ea3b9bf7511` (10.2.0-alpha.6, branch `docs/gate9b-evidence`);
  pointers `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`,
  `docs/LEGACY_CLI_AUDIT_2026-10-07.md`
- **Target Architecture:** WhiteMagic Gen3 `wm` binary (`crates/wm-gen3-harness`, `crates/wm-gen3-core/src/compat.rs`)
- **Base Commit:** `2a923b4c60f97570551d4bcbb02c290ad474f77b` (10.2.0-alpha.5, `main`)
- **Operator / Authority:** Lucas (ratification pending)
- **Preregistration:** `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md` §4 (GATE 9B), H15-2; boundary vs 9A in §8.2
- **Status:** **ENGINEERING CLOSURE — CLOSED WITH OPEN ITEMS, PENDING OPERATOR RATIFICATION.**
  2026-10-07 addendum: packaged-artifact evidence recorded on the installed and the
  manifest-verified published alpha.6 artifacts; H15-2 strictly bounded (see §3–§4); legacy CLI
  audit delivered and closed. No status upgrade to ratification-ready.

---

## 1. Statutory Closure Verdict

Pursuant to `docs/CHARTER.md` and the Gate 9B terms of
`docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`:

$$\boxed{ \textbf{GATE 9B (Compatibility Shell) IS ENGINEERING-CLOSED — RATIFICATION PENDING} }$$

The production `wm` binary declares itself the Gate 9B shell (`wm.rs:1-7`),
builds for all shipped targets, is install-certified against the published
release, and its Gen2 compatibility path (census → migrate → quarantine) is
exercised by the Gate 9D battery. The tracked legacy-CLI audit table
(Preserve/Translate/Deprecate/Remove) now exists
(`docs/LEGACY_CLI_AUDIT_2026-10-07.md`), and the packaged artifacts have been
directly exercised at the CLI/MCP/invariant-audit surface
(`receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`). The strict preregistered
H15-2 driver battery remains structurally out of reach (the 18 PEB drivers are
cargo-test harnesses against the source crate) and no CI-green run of the
reference-models batteries has completed on `main`; those items remain open
below.

## 2. Evidence

*Evidence class:* CI-fetched (GitHub Actions runs, cited by ID/URL) plus
locally re-executed tests on the base commit (cargo 1.98.0 / rustc 1.98.0,
2026-10-07T03:2xZ). Run URLs:
`https://github.com/lbailey94/whitemagic/actions/runs/<id>`.

| Verification | Command / scope | Result |
|---|---|---|
| **Release workflow (alpha.5)** | [run 37562982195](https://github.com/lbailey94/whitemagic/actions/runs/37562982195), tag `v10.2.0-alpha.5` | **10/10 jobs green**: version-truth gate, SBOM (CycloneDX), builds `aarch64-apple-darwin` / `aarch64-unknown-linux-gnu` / `x86_64-unknown-linux-gnu`, GitHub Release published (34 assets, prerelease), `install.sh` certified on all three gated targets, registries published (crates.io/npm/Docker/MCP) |
| **CI on alpha.5 (main push)** | [run 37562979314](https://github.com/lbailey94/whitemagic/actions/runs/37562979314) | Format, Clippy, Version Truth, Python Tests, npm, macOS advisory, Build Release Binary green; **Tests (Linux) terminated with exit 143 (SIGTERM) mid workspace tests**; the reference-models battery step was therefore **skipped** (see §4) |
| **Closure static scans** | `bash scripts/check_closures.sh` (alpha.5 CI, step 7) | **3/3 PASS** (no Gen2 deps; plastic layer never names the mutation surface; zero thread spawns outside physical transports) |
| **Release-build smoke** | `cargo build --release --bin wm` + `target/release/wm --version` + `selftest --json` (CI `build-release`) | Green |
| **Gen2 compatibility (migration)** | Gate 9D battery, local re-execution 2026-10-07: `cargo test --locked -p wm-gen3-core --features operator,reference-models --test gate9d_reality_battery -- --skip test_real_gen2_store_dry_run_and_idempotency_if_present` | **4 passed, 0 failed** (migration fidelity/idempotency, dirty-store quarantine, CP1–CP5, envelope defense) |
| **CLI/bridge unit tests** | `cargo test --workspace` (alpha.4 CI [run 37537977637](https://github.com/lbailey94/whitemagic/actions/runs/37537977637) and alpha.5 CI, default features) | Green; includes `legacy_mount_reads_and_refuses_writes`, `legacy_catalog_is_the_read_only_surface`, `session_start_appends_lane_marker`, `last_session_lane_reads_tail`, `mesh_cli_dial_allowlist_refuses_empty_and_unlisted_peers`, `selftest_fails_closed_when_temp_root_cannot_create_scratch`, `bounded_jsonrpc_reader_drains_oversized_line_then_reads_next_frame` |
| **Install certification** | `certify-install` jobs (alpha.5 release run) | Green on aarch64-macos, aarch64, x86_64 against the published assets |
| **Packaged-artifact checks** (addendum) | installed `wm10` alpha.6 (sha `fcd7f5a0…`) and manifest-verified published `wm-linux-x86_64` alpha.6 (sha `05de780c…`), isolated `/tmp` stores: `init`, `status`, `selftest --json`, `contract --json`, `apotheosis`, `inspect`, `grimoire`, `remember`/`recall`, `mandala status/triage`, `mesh status`, `peer list`, `shortlist`, stdio MCP probe (`initialize` / `tools/list` / `memory.create` / `memory.search` / `session.continuity`) | **Green on both artifacts** (13 check families; 9/9 invariant audit; 44 tools; server rc=0). Detail: `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md` |
| **Legacy CLI audit** (addendum) | `wm9` 9.3.4 `--help` / `help --all` vs `wm10` 10.2.0-alpha.6 `<cmd> --help`; command-presence log in the evidence bundle | 30 v9-only commands dispositioned (Preserve/Translate/Deprecate/Remove) + 8 shared names with semantic drift: `docs/LEGACY_CLI_AUDIT_2026-10-07.md` |

The `wm` binary root carries `#![recursion_limit]` but not its own
`#![forbid(unsafe_code)]` (the harness library does); `rg unsafe` over
`wm.rs` returns zero occurrences.

## 3. Hypothesis Results

- **H15-2 (Packaging Invariance): SUBSTANTIALLY EVIDENCED, STRICTLY OPEN.**
  Packaging, release, installation and smoke paths are green, and the
  packaged artifacts are now directly exercised at the CLI/MCP/invariant-audit
  surface on both the installed build and the manifest-verified published
  release asset (`receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`). The
  preregistered wording — re-running the M0–M8 driver battery (PEB-0…PEB-14C)
  against the packaged artifact — remains **not executable as written**: all
  18 PEB drivers invoke `cargo test -p wm-gen3-core` against `WMGEN3_ROOT`
  with no binary path, so engine-internal assertions are unreachable from the
  CLI. Closing it requires an explicit scope amendment to the process-boundary
  surface (as Gate 9A already applied) or a new Gen3-native packaged battery.
- **CLI-as-sovereign-pulses: EVIDENCED for mutation commands** (all writes
  flow through `Substrate`/pulse compiler; e.g. the packaged CLI `remember`
  reports `RatifiedChannel(wm-cli-operator)` / `Article 1 MVCC Transaction
  Verified`; the only compatibility surface is the explicitly read-only
  `wm serve --legacy-store` mount). The Preserve/Translate/Deprecate/Remove
  audit table now exists (`docs/LEGACY_CLI_AUDIT_2026-10-07.md`).
- **9A/9B boundary (§8.2):** core encapsulation stayed in 9A; this verdict
  covers the shell and migration only.

## 4. Open Items & Caveats

1. **No CI-green execution of the reference-models batteries on `main` yet.**
   The step exists (`.github/workflows/ci.yml`, "Run gate batteries
   (reference-models)") and was added in the alpha.5 cycle, but the only run
   that reached it (37562979314) had `Tests (Linux)` killed by SIGTERM
   (exit 143) during the preceding default-feature step, so the battery step
   was skipped. No assertion failure is recorded.
2. **M0–M8 vs the packaged artifact: bounded in the 2026-10-07 addendum.**
   The packaged artifacts pass 13 CLI/MCP/invariant check families (both the
   installed alpha.6 and the manifest-verified published asset), but the
   preregistered driver-form re-run is structurally impossible — the 18 PEB
   drivers are `cargo test -p wm-gen3-core` harnesses against the source crate
   with no binary path (exact blockers in the addendum §4). Requires an H15-2
   scope amendment or a Gen3-native packaged battery to close.
3. **Legacy CLI audit: CLOSED (addendum).** 30 v9-only commands dispositioned
   plus 8 shared names with semantic drift — `docs/LEGACY_CLI_AUDIT_2026-10-07.md`.
   The audit surfaces follow-on gaps (no Gen3 `backup`/`restore`; `wm at-rest`
   CLI pending; memory source-trust curation partial), recorded there.
4. **`wm host-guard` CLI wiring is pending** (core engine landed in
   alpha.5; see CHANGELOG 10.2.0-alpha.5 "Added").
5. The Gate 9D real-store test self-skips when the WMv9 planning store is
   absent; it did not run in any cited CI execution.
6. **v9-era bench scripts do not speak the Gen3 CLI.** `curated_smoke_test.py`,
   `longmemeval_bench.py`, `memorastrict_bench.py`, and `eval_matrix.sh` pass
   the removed `serve --max-requests/--rate-limit` flags (and the smoke also
   asserts the v9 MCP payload contract), so they cannot gate the packaged v10
   artifact without a Gen3 port; `scripts/eval_all_tools.py` does not exist at
   this base. Evidence: addendum §4.2–§4.4.
7. **Artifact provenance caveat:** the locally installed `wm10` is not
   byte-identical to the published alpha.6 asset (sha/size differ); both were
   tested, with identical results. Published-asset hash verification used the
   release manifest (`05de780c…`).
8. **Closure static scan is RED at the addendum base (`ef623fb`).**
   `bash scripts/check_closures.sh` passes rules 1–2 but fails rule 3 on
   `crates/wm-gen3-harness/src/bin/wm_node.rs:1036,1159` — the Geth Phase 2
   `wm-node` Unix-socket accept loop is a physical-I/O transport site but is
   missing from the scanner allowlist (`transport.rs`/`mesh.rs`/`mcp_server.rs`
   only). CI runs this script on push, so the tracked closure gate fails at this
   base; the "3/3 PASS" citation above is alpha.5-era. Fix = scanner allowlist
   entry + boundary receipt (code/script edit, not made by this docs lane).
   Evidence: `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md` §4a,
   `logs/13-closure-scan-base.txt`.

## 5. Transition

Gate 9C and Gate 9D verdicts are issued contemporaneously
(`receipts/GATE_9C_CLOSURE_VERDICT_2026-10-07.md`,
`receipts/GATE_9D_CLOSURE_VERDICT_2026-10-07.md`). Operator ratification of
the 9B/9C/9D closures is the remaining statutory step; open items above are
carried as ratification conditions. The 2026-10-07 addendum
(`receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`,
`docs/LEGACY_CLI_AUDIT_2026-10-07.md`) removes the packaged-evidence and audit
gaps; the remaining ratification conditions are items 1, 4, 5, 8, and the
H15-2 closure decision in item 2.
