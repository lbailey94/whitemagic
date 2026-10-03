# Gate 9A Slice 1 synthetic acceptance receipt

Status: implemented, source-reviewed, built, and synthetically checked as an **uncommitted working-tree candidate**. This is not Gate 9A closure, historical activation, power-loss qualification, migration approval, or release approval.

Base commit: `981b0bfac7acefb383ef86ef64699e32545c7849`. The base hash alone does not identify this candidate; use the source manifest below. Sol implemented the contract/integration, Terra implemented storage, and the coordinating agent reviewed and corrected the combined implementation and independently ran final checks.

## Implemented behavior

- Ordinary ingestion requires an installed typed local `RatifiedChannel`. The harness explicitly enables `operator` and installs that authority. This is trusted local possession, not cryptographic or remote authentication.
- Each accepted item atomically commits its record, lexical postings, allocator, epoch, operation nullifier, and receipt in LMDB. Batch results remain per-item, ordered, with zero-based IDs and logical `created_at == id`.
- Caller-supplied operation IDs on `memory.intake_authorized` support receipt replay across process restarts. Authenticated replay precedes new-operation budget, duplicate, noise, and epoch checks. Changed requests conflict. The dedicated RPC performs no sweep.
- Fresh stores use a serialized initialization marker and final format-v3 publication. Existing unsupported, incomplete, or malformed stores refuse; there is no adoption, migration, or automatic repair.
- Model storage types and the legacy ingestion helper require `reference-models` outside unit tests. The closure canary uses an isolated nonpersistent evidence model and marks its journal event accordingly.
- Accepted writes consume the process-local budget before fallible postcommit view hydration. Durable duplicate detection preserves `duplicate_exact` even with a stale in-memory identity view.

## Reproducible verification

Commands were run from the repository root, offline and locked for Cargo. Runtime scenarios used disposable synthetic stores with projection and automatic sweep disabled. No real or historical store was opened by this acceptance battery.

| Check | Result |
|---|---|
| `cargo test --workspace --offline --locked --features wm-gen3-core/reference-models -- --skip projection::tests --skip ops::gated_tests` | 181 passed, 0 failed: 162 core unit, 3 reference integration, 1 public API integration, 2 harness unit, 13 documentation tests. 1 ignored, 5 filtered out. |
| `cargo test --offline --locked -p wm-gen3-core store::tests -- --nocapture` | 5 passed after additional assertions were added inside the storage tests; these overlap the workspace count. |
| `cargo test --offline --locked -p wm-gen3-core --doc` | 13 passed, including capability compile-fail examples; overlaps workspace count. |
| `cargo build --release --offline --locked -p wm-gen3-harness` | Passed. |
| `cargo check --offline --locked -p wm-gen3-core --no-default-features` | Passed. |
| `cargo tree --offline --locked -p wm-gen3-harness -e features` | Core default and operator enabled; reference-models absent. |
| `bash scripts/check_closures.sh` | Both static scans passed. |
| `python3 scripts/check_slice1_harness.py target/release/wm-gen3` | All 8 process-boundary scenarios passed. |
| `git diff --check` | Passed. |

The ignored test is `projection::a3_diagnostic::a3_diagnostic_ungated_cosine`; the five exclusions are the explicitly named projection/gated test groups. This is not a claim that the unfiltered model suite passed.

The supplemental storage run checks rollback after record, postings, counters, nullifier, and receipt staging, then reopens and verifies no partial effect or consumed ID. It also checks incomplete initialization after each 0–7 named-database creation states, malformed metadata widths, unsupported and unversioned stores, both one-sided ledger corruptions, and refusal preservation. These are deterministic injected/constructed cut points, not physical power-loss testing.

Harness scenarios: ordered mixed batch successes/refusals; reopened allocation and postings; read-only write refusal with unchanged data.mdb; replay before exhausted budget; cross-process receipt replay without budget charge; replay after a later epoch and altered-request refusal; retry-only unchanged data.mdb with no sweep; four competing initializers producing a coherent reopenable store. Contenders may refuse incomplete initialization; universal contender success is not required.

## Remaining boundaries

Gate 9A remains open. Sweep, relation mutation, and other durable writer paths are not covered by this ingestion receipt protocol. The legacy batch RPC retains its separate post-ingestion sweep behavior. Projection-enabled authorized ingestion refuses; vector authorization is not implemented. There is no historical/model execution qualification, migration, crash-repair workflow, arbitrary SIGKILL/power-loss proof, performance qualification, or signed external identity. Durable duplicate checking scans records. Receipt validation does not continuously re-hash the entire evolving postings index.

Next bounded work: inventory the remaining durable writers, define their exact authorized effects and transaction boundaries, and add corresponding synthetic acceptance evidence before considering gate closure.

## Candidate and evidence hashes

- Release binary: `target/release/wm-gen3`, SHA-256 `8e277776eddfd1ddc960f182b2183606a7c6532d5e549d0439d070c28089b428`.
- [Source manifest](gate9a_slice1_20260921/source-manifest.sha256), SHA-256 `6d34cf2bb1bab4871ad52d61a2966754d12c1a05521fc921ee75bf81af150fff`.

Raw logs are local evidence files (ignored by Git); retain them with this receipt when sharing the candidate.

| Evidence | SHA-256 |
|---|---|
| [closures.log](gate9a_slice1_20260921/closures.log) | `6d4b8340d7515de8333105610008bdaa5892eaaec5f8c427f0566f670c891d2e` |
| [default-core-check.log](gate9a_slice1_20260921/default-core-check.log) | `502af120784ca75cd0627109842b7ae1d101005fd70392372fddf6812ae1b93c` |
| [doctests.log](gate9a_slice1_20260921/doctests.log) | `fe1997b1e835c35fa350a2a695c2a8708f059bc1700f5020010f54c8a6243bcd` |
| [harness-features.log](gate9a_slice1_20260921/harness-features.log) | `6b4e395d7d2ed982f2dff1493c542452035e1898593f831509cc621b7e73cd3c` |
| [harness-smoke.log](gate9a_slice1_20260921/harness-smoke.log) | `caa758976b0e9f01d6b6217df63a4f3ea561ce7811a0cd83db769cf98802bfa1` |
| [release-build.log](gate9a_slice1_20260921/release-build.log) | `5d5fc078491038455b4ec542ae62c321dca89a001a8baface76113e7827d201b` |
| [store-tests.log](gate9a_slice1_20260921/store-tests.log) | `5f2393027de5b28f921868d66240b0e81dc735ab5927746f9db18b55efe029cb` |
| [workspace-tests.log](gate9a_slice1_20260921/workspace-tests.log) | `3476b5bd7941d7cd7e87dbbfcfd77db38af0152685b267a8520b037389fdb939` |
