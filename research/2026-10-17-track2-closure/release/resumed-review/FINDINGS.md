# v10.4.0 release and dependency review

Audit date: 2026-10-17. This is a read-only review of public release `v10.4.0` and its exact public HEAD, `19169fa8c2fccfb51fc1b1b6e0c762257288a65`. It does not alter release assets, tags, signing identity, source, or Cargo targets.

## Disposition

The signed release artifacts and their install/download integrity checks match the published manifest. The v10.4.0 open-alpha release record does not publish a test count or benchmark result (`tests` and `benchmarks` are `null`), which is the right boundary for the evidence found here. However, the current public main CI and the PEB-10 timing workflow both fail on this exact source revision. The timing result is still below the retained 1.4x floor and must remain unqualified. The separate release-health record reports distribution availability, artifact integrity, and npm/Docker self-install certification; it does not include CI or PEB-10 status, so `status: healthy` must be read within that narrower scope.

## Identity, signature, and artifact bytes

- Public source: `lbailey94/whitemagic`, main and tag `v10.4.0`, both at `19169fa8c2fccfb51fc1b1b6e0c762257288a65`.
- Release is marked prerelease and identifies channel `open alpha`.
- Downloaded `release-manifest.json` SHA-256 is `1a05ca3d369dccf0fd092698aeadf98b7333a89c28207bf8d6e608d72f6d2075`; its Ed25519 signature verifies against the repository release public key. The release-health record independently records the same manifest hash and `manifest_signature_valid: true`.
- All three manifest target binaries match the exact signed size and SHA-256 and their `.sha256` sidecars: Linux x86-64 `e080bc056c9da611b126a223601b6e4fcb34bd79f59c8ac95d889b9d67e0512a` (50,283,992 bytes); Linux aarch64 `01e59a1e5eedf77bba94d61a0f34650c51e572030561b57327ada18ed31752bd` (49,029,888 bytes); macOS aarch64 `c49afb2b717bb2f84e88b31cb691cb492fcb2f4f59bee50928c1c549c934077b` (44,153,824 bytes). Compressed asset sidecars also matched their compressed bytes.
- The signed manifest lists `minimum_store_schema: 7`, `supported_profile: curated`, three `install_gated` targets, and `tests: null` / `benchmarks: null` (the last two fields are absent from this schema-1 manifest; the generated site release record also has null test/benchmark facts).
- Release-health artifact SHA-256: `a1c850aee6562244fd2c4f44005e7bfa60b789334ebec1898ad2cf1e69cbefbb`.

Downloaded assets and records are preserved in `assets/`; release-health and manifest URLs are the v10.4.0 GitHub Release assets. This proves published-byte identity and signature integrity, not clean installation by an unaffiliated user on every listed platform.

## CI and qualification checks at the exact public HEAD

CI run [39058427612](https://github.com/lbailey94/whitemagic/actions/runs/39058427612) used exact HEAD `19169fa8c2fccfb51fc1b1b6e0c762257288a65` and concluded failure.

- Passing jobs: Linux workspace tests (including reference-model gate batteries), Python tests, release binary build and `--version` execution, version-truth check, npm launcher tests, and macOS tests. Static closure scans in the Linux job passed.
- Failing jobs: **Clippy** and **Format Check**. Both are ordinary jobs with no `continue-on-error` in `.github/workflows/ci.yml`; both fail the CI workflow. Whether branch protection marks these checks as required is a separate repository setting not verified here.
- Clippy runs `cargo clippy --workspace --all-targets -- -D warnings`. Exact diagnostics from Rust/Clippy 1.98:
  1. `crates/wm-gen3-harness/src/bridge.rs:4007`: `compact_agent_context` has too many arguments `(9/8)` (`clippy::too_many_arguments`). Minimal maintainable fix: group the closely related context parameters into a small named input struct and update its call sites, preserving behavior. Avoid suppressing the workspace-wide deny unless there is a documented reason.
  2. `crates/wm-gen3-harness/src/bridge.rs:7835`: `&[a.clone()]` triggers `clippy::cloned_ref_to_slice_refs`; Clippy's direct suggestion is `std::slice::from_ref(&a)`.
- `cargo fmt --all -- --check` reports formatting-only diffs at `crates/wm-gen3-core/src/ops.rs:285`, `crates/wm-gen3-core/src/ops.rs:1862`, and `crates/wm-gen3-harness/src/bridge.rs:9671`. Minimal fix: rustfmt the files and inspect the resulting diff, then rerun the check. The raw CI log with ANSI removed only at display time is preserved as `logs/ci-failed-full.log`.

Security workflow run 39058427556 passed, including dependency audit and closure/security scans. Earlier in this bounded slice, the dependency repair was independently checked: the published graph uses vendored `candle-core 0.9.2` with `zip 9.0.4`; `cargo deny check advisories` passed (one pre-existing no-match allow warning); NPZ reader/writer tests, PyTorch pickle reader tests, and `cargo check -p wm-gen3-systemone` passed. Those focused commands ran before this resumed read-only audit and were not rerun against the public release in this pass.

## PEB-10 timing gate

Benchmarks run [39058427484](https://github.com/lbailey94/whitemagic/actions/runs/39058427484) used the same source revision and failed at “Qualify PEB-10 timing (repeated release-mode samples).” The uploaded `benchmark-artifact/peb10-timing.json` is preserved with SHA-256 `a022734596d9e6f004540c3c1686b125ee23380a7d83eaed9352acdd23e7deb0`.

The JSON states `qualification: repeatable wall-clock comparison; DAG baseline is emulated`, Linux x86-64 Azure, Rust 1.98.0, seven repeats, and the compiler-source hash. The raw `speedup_x` samples are:

`1.114017109938, 1.083083465136, 1.101908304498, 1.197109677273, 1.120952899106, 1.138141822918, 1.104045413013`.

Median is `1.114017109938x` (min `1.083083465136x`, max `1.197109677273x`) against the retained `1.4x` floor. Thus the result fails by `0.285982890062x`; do not call PEB-10 qualified, lower the floor, discard samples, or retry until green. The script exits nonzero below the floor. On push/tag events that step is not advisory (`continue-on-error` absent), so it fails the Benchmarks workflow and causes the subsequent PEB-0/PEB-0.1 release tests to be skipped. Only the separate PR/base raw comparison job is explicitly titled advisory. The published `docs/PEB10_TIMING_QUALIFICATION.md` accurately states the 1.4x median floor and that the Gen2 DAG baseline is emulated rather than historical production. Keep the failed evidence visible as an unqualified result.

## Release-health scope and labeling

Release-health run [39058928563](https://github.com/lbailey94/whitemagic/actions/runs/39058928563) succeeded on the release workflow's `workflow_run` event. Its trigger listens to **Release**, not the CI or Benchmarks workflows. The produced `release-health.json` has `status: healthy`, all six crates.io packages, npm, Docker and MCP-registry entries live, GitHub release integrity verified, and both npm and Docker install certifications passing against the same signed manifest hash. The two certifications report runtime selftest pass, durable reopen, isolated/cleaned scratch store, and verified manifest binding.

This is good evidence for the dimensions it probes. It is not an overall source qualification record: the schema and gate in `scripts/release_health.py` / `.github/workflows/release-health.yml` check distribution surfaces, signed artifact integrity, and the two install paths; they do not ingest CI status or the PEB-10 benchmark result. Since the Release workflow succeeded independently, the health workflow could label v10.4.0 `healthy` while current main CI and Benchmarks were failing. The successful release-health workflow itself therefore does not supersede those failures. Minimal truthful options for follow-up: label the record/UI explicitly as “distribution health” and surface CI/timing as separate gate fields, or make the top-level aggregate incorporate the required source/benchmark gates. Do not imply that this review changed that published status.

## Claim boundaries and remaining public-copy mismatch

- The GitHub release body and manifest identify v10.4.0 as an open-alpha release, limit install-gated binaries to Linux x86-64, Linux aarch64, and macOS aarch64, and state other platform support remains on Gen2 stable. The release's test/benchmark facts are null; no v10.4.0 performance result is claimed there.
- The public site has stronger explicit qualification boundaries: its current research page separates the public c300 24-case corpus from the later 32-case candidate suite and states the latter is clue-guided authored-case evidence, not unseen/autonomous discovery. `llms-full.txt` explicitly says no v10.4.0 test count is asserted and the signed release record does not establish performance or complete invariant coverage. The site also omits historical performance from its generation comparison. These are appropriately bounded descriptions.
- The repository README still has a “Reproducible Task Evaluation (24 Scenarios)” block with prior metrics (96.9%, 100%, 87.5%) while the v10.4.0 release body and changelog describe the new 32-scenario suite. That section is not currently labeled as historical or pinned to its earlier release/source. It may be read as current 10.4 evidence. Minimal copy fix is to date/pin it as historical and link the new 32-case scope with the same limitations the site gives; avoid copying 32-case results into the README without exact scored evidence.
- The release-health word `healthy` is accurate only as “all checked distribution surfaces and npm/Docker install certifications are healthy.” The unqualified timing and failing CI make it inaccurate if shown without this scope as an overall release qualification badge.

## Review boundary

This audit is read-only with respect to source and release assets. It did not change the 1.4x threshold or timing script, and did not modify tags, signatures, binaries, deployment state, or Cargo targets. It does not establish new-user install success across all supported platforms, stable/beta readiness, historical-production speedup, or an overall green CI state.
