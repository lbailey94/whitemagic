# Gate 9B Packaged-Artifact Evidence — 2026-10-07

- **Date:** 2026-10-07
- **Lane:** `docs/gate9b-evidence` (worktree `wt-gate9b`), base `ef623fbd5e80d64a47c3335e99a34ea3b9bf7511`
- **Owner:** opencode (release-evidence engineering lane)
- **Closes/bounds:** open items 2 and 3 of `receipts/GATE_9B_CLOSURE_VERDICT_2026-10-07.md` §4
  (packaged-artifact M0–M8 evidence; legacy CLI audit)
- **Status:** evidence recorded; **no code edits**; H15-2 remains formally open at the
  preregistered driver-form scope (bounded below); operator ratification untouched
- **Rev 2 (2026-10-07, post-merge `d08e20c`):** command-presence count corrected to 63;
  §4a closure-scan finding updated — repaired by wave-3 `ef24101` (allowlist + boundary
  receipt); `wm at-rest`/`wm host-guard` CLI now covered (audit rev.2)
- **Errata 2026-10-07 (hash re-anchor):** merge base `80b34c2` → `d08e20c` after the
  public-history rewrite (internal runbook purge); referenced content unchanged.
- **Evidence bundle:** `receipts/gate9b_artifact_evidence_20261007/`
  (raw logs, `SHA256SUMS`, `summary.json`, release manifest, exact patch)

---

## 1. Artifacts under test

| Artifact | Version | sha256 | Size | Notes |
|---|---|---|---|---|
| Installed `wm10` (`/home/lucas/.local/bin/wm10`) | `10.2.0-alpha.6` | `fcd7f5a0f0353a482c85ba04b0fe7cd0d7e3db599947f9182ccdce58575819aa` | 48,855,880 B | locally installed build; **not byte-identical** to the published asset |
| Published release asset (`wm-linux-x86_64`, GitHub release `v10.2.0-alpha.6`) | `10.2.0-alpha.6` | `05de780c2500fa39a6783dfb821c1f8fa960f830732552a9e6efcffaafe4a852` | 48,791,336 B | **hash verified against `release-manifest.json`** (`supported_profile: curated`) |

The published-asset sha and size match the manifest exactly
(`receipts/gate9b_artifact_evidence_20261007/release-manifest-v10.2.0-alpha.6.json`).
The installed binary is the mission-specified artifact; because it is not byte-identical to the
published release asset, every check below was run against **both** artifacts. Results are
identical everywhere they overlap. All runs used isolated `/tmp` stores; no live WhiteMagic
store was opened for the packaged-artifact checks.

Host/toolchain: Linux x86_64 (8 vCPU), 38+ GiB free on `/`, cargo/rustc 1.98.0.

## 2. What M0–M8 are (and what their harness is today)

M0–M8 are the nine Gen3 research milestones operationalised by the PEB benchmark batteries
(PEB-0 … PEB-14C). Their receipts are `receipts/BENCHMARK_M0*.md`; their executable harnesses
are the Python drivers under `benchmarks/`. **Every PEB driver invokes `cargo test -p
wm-gen3-core` against `WMGEN3_ROOT` (default `/home/lucas/Desktop/WMgen3`); none accepts a
binary path, and CI does the same (`benchmarks.yml` runs the same cargo filters).**

| Milestone | PEB battery | Driver | Receipt |
|---|---|---|---|
| M0 — substrate minimality / epistemic foundations | PEB-0, PEB-0.1, PEB-1.1 | `driver_peb0_primitive_minimality.py`, `driver_m01_holdout_stress.py` | `MILESTONE_0_EXECUTION_MANIFEST.md`, `BENCHMARK_M01_*` |
| M1 — Four Corners / contextualised Catuṣkoṭi | PEB-1, PEB-4 | `driver_peb1_four_corners.py`, `driver_peb4_continuous_dreaming.py` | `BENCHMARK_PEB1_*`, `BENCHMARK_PEB4_*` |
| M2 — homeostasis / reversible quarantine | PEB-5, PEB-8 | `driver_peb5_peb8_homeostasis_quarantine.py` | `BENCHMARK_M02_*` |
| M3 — causal cladistics / Pareto gating | PEB-6 | `driver_peb6_causal_cladistics.py` | `BENCHMARK_M03_*` |
| M4A — symbolic spectroscopy fidelity | PEB-7 | `driver_peb7_spectroscopy_fidelity.py` | `BENCHMARK_M04A_*` |
| M4B — attractor emergence / basin geometry | PEB-2, PEB-3 | `driver_peb2_peb3_attractor_emergence.py` | `BENCHMARK_M04B_*` |
| M5A / 5A.5 / 5B — consensus, proof-carrying parallelism, pulse compiler | PEB-9, PEB-9.5, PEB-10 | `driver_peb9_speculative_consensus.py`, `driver_peb9_5_proof_and_parallel_crossover.py`, `driver_peb10_declarative_pulse_compiler.py` | `BENCHMARK_M05A*`, `BENCHMARK_M05B_*` |
| M6A/M6B — sovereign mesh / conformal sovereignty | PEB-11, PEB-12 | `driver_peb11_sovereign_mesh.py`, `driver_peb12_conformal_sovereignty.py` | `BENCHMARK_M06A_*`, `BENCHMARK_M06B_*` |
| M7 — cognitive geometry / metric ladder | PEB-13 | `driver_peb13_cognitive_geometry.py` | `BENCHMARK_M07_*` |
| M8A/M8B/M8C — physical socket, relativity, holographic sangha | PEB-14A/B/C | `driver_peb14a_physical_socket.py`, `driver_peb14b_relativity_partition.py`, `driver_peb14c_hologram.py` | `BENCHMARK_M08A_*`, `BENCHMARK_M08B_*`, `BENCHMARK_M08C_*` |
| PEB-15 — production kernel (Mandala Kekkai) | PEB-15 | `driver_peb15_mandala_kekkai.py` (`cargo test --test mandala_kekkai_benchmark`) | `benchmark_peb15_mandala_kekkai.md` |

`GATE_9A_M0_M8_DISPOSITIONS.md` (archived) records 17/17 core drivers PASS on 2026-09-22 in
**driver form** and explicitly assigns packaged-CLI verification to 9B. The `driver_phase*`
drivers target the separate `wm-tools` workspace and are out of M0–M8 scope.

## 3. Checks executed against the packaged artifacts

All commands ran against isolated stores under `/tmp/opencode/g9b/`; raw output is in the
evidence bundle. `WM` = the artifact path; both artifacts were exercised.

| # | Check | Exact command (artifact = both) | Result |
|---|---|---|---|
| 1 | Version truth | `$WM --version` | `wm 10.2.0-alpha.6` (both) |
| 2 | Fresh init + status | `$WM init --store <tmp>`; `$WM status --store <tmp>` | rc=0; 6 seed records; `Epoch: 6`; `Journal Status: OK` |
| 3 | Selftest | `$WM selftest --json --store <tmp>` | `{"status":"ok","engine":"gen3","version":"10.2.0-alpha.6","persistence":"durable_reopen","scratch_store":"isolated_and_cleaned","host_status":"ok"}` (both) |
| 4 | Route/schema contract | `$WM contract --json --store <tmp>` | `kind=whitemagic-route-schema-manifest`, `format_version 1`, `version 10.2.0-alpha.6`, **44 routes / 40 declared / 4 undeclared** (both) |
| 5 | Apotheosis invariant audit | `$WM apotheosis --store <tmp>` | **Substrate invariants 9/9 PASS** (Articles 1–9), composite 0.9625, truth-drift 0.000, 27/27 declared executables, 0 phantom surfaces (both) |
| 6 | Constitution view | `$WM inspect --scope invariants --store <tmp>` | journal `ok:true`, `violations: 0`; tier-1 invariant set + hash present |
| 7 | Onboarding | `$WM grimoire --json --plan --store <tmp>` | `ready: true`; host/substrate/starter-galaxy/agent-clients/verification all `ok`; read-only plan (no files modified) |
| 8 | CLI mutation + recall | `$WM remember "gate9b cli pulse marker" --store <tmp>`; `$WM recall ...` | `Commit successful. Record ID: 7`; `Authority: RatifiedChannel(wm-cli-operator)`; `Contract: Article 1 MVCC Transaction Verified`; recall returns record #7 score 1.0000 |
| 9 | Mandala surfaces | `$WM mandala status --store <tmp>`; `$WM mandala triage --utility 0.9 --risk 0.1 --variance 0.05 --cost 0.02 --store <tmp>` | ledger 0 consumed JTIs, Article 1 closure 100% gated; triage `JEV Tensor Score 0.788750`, `ADMITTED` |
| 10 | Mesh / peer trust | `$WM mesh status --store <tmp>`; `$WM peer list --json --store <tmp>` | node identity + verifying key present; local peer `trust_tier: local`, capabilities `[sync, dispatch, telemetry, triage]` |
| 11 | Static-embedding shortlist | `echo 'recall my last session' \| $WM shortlist --store <tmp> --k 3` | top route `session.recall` 0.8538; gate `dispatch`; signed shortlist receipt written |
| 12 | MCP stdio surface | `$WM serve --store <tmp> --profile full` (JSON-RPC: `initialize`, `tools/list`, then `tools/call` `wm` → `memory.create`, `memory.search`, `session.continuity`) | `serverInfo {name: whitemagic-gen3, version: 10.2.0-alpha.6, profile: full}`; **44 tools, `wm` at index 0**; create→search round-trip finds the marker; `session.continuity` returns checkpoint/queue/turn fields; **server rc=0** (both) |
| 13 | Command-presence inventory | `for c in <63 names>; do $WM $c --help; done` | 30 v9-only commands absent from the tested `wm10` alpha.6 artifacts (basis for the legacy audit); shared names retained: `serve`, `contract`, `selftest`, `status`, `grimoire`, `session`, `ingest`, `migrate` (log `10-command-presence.txt`; merged main adds `at-rest`/`host-guard`/`compact` — see audit rev.2) |

## 4. What could not be run against a packaged artifact — exact blockers

1. **M0–M8 / PEB-15 drivers are cargo-bound.** All 18 PEB drivers construct `cargo test -p
   wm-gen3-core …` with `cwd=$WMGEN3_ROOT` and no binary argument
   (e.g. `driver_peb0_primitive_minimality.py:34-39`, `driver_peb15_mandala_kekkai.py:29-33`).
   The asserted quantities (pulse-compiler internals, transport bytes, conformal pools) are not
   exposed over the `wm` CLI, so no patch to a single argument can redirect them at an installed
   binary. Closing H15-2 in its strict preregistered form requires either a **Gen3-native
   packaged-battery driver** (CLI/MCP-level assertions) or an **H15-2 scope amendment** to the
   process-boundary surface — the same demarcation Gate 9A already applied in
   `GATE_9A_M0_M8_DISPOSITIONS.md` ("packaged CLI verification is 9B per PEB-15 §8.2").
2. **`scripts/curated_smoke_test.py` is a v9-era gate.** (a) It passes
   `serve --max-requests 100 --rate-limit 0`, which `wm10 serve` rejects
   (`error: unexpected argument '--max-requests'`); (b) after patching only the flags
   (exact patch saved at
   `receipts/gate9b_artifact_evidence_20261007/patched/curated_smoke_test.flags.patch`), it
   still fails because it asserts the **v9 MCP contract**: a different `serverInfo` shape,
   a "curated" tool description, `tools.list` returning JSON-in-text, and a
   `wm docs quickstart` subcommand that Gen3 does not ship. A flags-only patch is therefore
   **insufficient**; the script needs a Gen3 port (or must run against `wm9` for v9 stores).
3. **`scripts/eval_all_tools.py` does not exist** anywhere in the tree at `ef623fb`
   (content search and `git ls-files` both empty).
4. **`scripts/longmemeval_bench.py`, `scripts/memorastrict_bench.py`, and
   `scripts/eval_matrix.sh`** accept `--binary`/`WM_BINARY`, but the server launcher passes
   `--max-requests 0 --rate-limit 0` (`longmemeval_bench.py:282-289`,
   `memorastrict_bench.py:165-171`), so the packaged v10 binary exits at startup; the harness
   then dies on a broken pipe (`logs/08-longmemeval-blocker.txt`). Patch required: drop the two
   flags from the launcher (longmemeval also expects the v9 `tools.list` payload and would then
   need the same Gen3 port as item 2 — out of 9B scope to confirm here).
5. **`scripts/check_slice1_harness.py`** (the 9-scenario process-boundary check cited by Gate 9A
   receipts) is **not tracked** at `ef623fb`; only its receipts remain, so it cannot be re-run
   from this tree.
6. The locally installed `wm10` is **not the published asset** (sha/size differ); the published
   asset was therefore fetched, manifest-verified, and exercised separately (all overlapping
   checks identical).

## 4a. Base-tree side finding — closure scan (rev.2: resolved on main)

`bash scripts/check_closures.sh` at `ef623fb` (docs-only working tree) **failed rule 3**:

```
CLOSURE SCAN FAILED: thread spawn outside the physical-I/O transport:
crates/wm-gen3-harness/src/bin/wm_node.rs:1036:  std::thread::spawn(...)
crates/wm-gen3-harness/src/bin/wm_node.rs:1159:  std::thread::spawn(...)
```

Rules 1–2 passed. The sites belong to the Geth Phase 2 `wm-node` Unix-socket listener
(added in 10.2.0-alpha.6); the scanner's allowlist covered only `transport.rs`, `mesh.rs`,
and `mcp_server.rs`. Line 1036 is the accept loop dispatching per-connection handlers — a
physical-I/O transport site in intent (Article 4-compliant), so this was a **scanner
allowlist gap**, not evidence of a semantic breach. **Resolution (rev.2):** wave-3 `ef24101`
extended the scanner allowlist and added the ratified boundary receipt
`receipts/BOUNDARY_WM_NODE_TRANSPORT_SPAWNS_2026-10-07.md`; re-run at merge base `d08e20c`
reports `closure static scans: PASS` (3/3). Original log:
`receipts/gate9b_artifact_evidence_20261007/logs/13-closure-scan-base.txt`.
`python3 scripts/version_truth.py --check` passes (`10.2.0-alpha.6` agrees on all surfaces).

## 5. Verdict movement

- **Item (b) legacy CLI audit: CLOSED.** `docs/LEGACY_CLI_AUDIT_2026-10-07.md` tables all 30
  v9-only commands with Preserve/Translate/Deprecate/Remove dispositions, rationale, and the
  Gen3/`wm9` replacement, plus the drifted shared names (notably `serve`).
- **Item (a) M0–M8 vs packaged artifact: PRECISELY BOUNDED.** The packaged artifact now has
  direct, reproducible CLI/MCP/invariant-audit evidence on both the installed build and the
  manifest-verified published release asset (13 check families, all green). The preregistered
  "re-run all PEB drivers against the packaged artifact" remains **not executable as written**
  for the reason in §4.1; H15-2 stays **partially evidenced → substantially evidenced**, and
  closure requires a scope amendment or a new packaged-battery driver.
- **Gate 9B overall:** remains **engineering-closed, ratification pending**. This receipt
  removes the "no packaged-artifact evidence" gap and closes the audit gap; it does **not**
  close the strict H15-2 wording. Rev.2: the §4a closure-scan finding was repaired on main by
  `ef24101` (re-run at merge `d08e20c`: 3/3 PASS), and wave-3 `88ac66a` closes the
  `wm at-rest`/`wm host-guard` CLI gaps; the only remaining verdict §4 conditions are the CI
  reference-model battery, the 9D real-store skip, and the H15-2 closure decision.

## 6. Reproduction

```bash
WM=/home/lucas/.local/bin/wm10          # or the manifest-verified release asset
S=$(mktemp -d /tmp/gate9b-XXXX); $WM init --store "$S"
$WM status --store "$S"; $WM selftest --json --store "$S"
$WM contract --json --store "$S" | python3 -c 'import json,sys; print(json.load(sys.stdin)["counts"])'
$WM apotheosis --store "$S"
$WM grimoire --json --plan --store "$S"
$WM remember "repro marker" --store "$S"; $WM recall "repro marker" --store "$S"
# MCP probe: see receipts/gate9b_artifact_evidence_20261007/logs/05-mcp-probe.txt
```

Evidence bundle checksums: `receipts/gate9b_artifact_evidence_20261007/SHA256SUMS`.
