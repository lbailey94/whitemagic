# Gen3 developer guide

Current guide for the `wm` 10.2 alpha line (Gen3 substrate). It replaces the
stale v9.2-era developer notes: commands, paths and knobs below are taken from
the code and the CI workflow at `main` `2a923b4` (10.2.0-alpha.5), not from the
old `justfile` (which still describes the v5 tree and must not be trusted).
Version numbers live in the release surfaces (`Cargo.toml` workspace version,
`scripts/version_truth.py`), never in this guide.

Related documents: [`INDEX.md`](INDEX.md) (map of `docs/`),
[`STORE_LAYOUT.md`](STORE_LAYOUT.md) (on-disk store), [`CHARTER.md`](CHARTER.md)
(constitutional contract), [`../INSTALL.md`](../INSTALL.md) (install paths),
[`SELFTEST_AND_HOST_HEALTH.md`](SELFTEST_AND_HOST_HEALTH.md) (`wm selftest`).

## 1. Workspace layout (6 crates)

The workspace root is `Cargo.toml`; the whole workspace shares one version
(`[workspace.package] version`). There is no root library crate — `wm` is a
binary inside the harness crate.

| Crate | Role |
|---|---|
| `crates/wm-gen3-core` | The substrate: constitution/law, evidence records, capability + `pulse_compiler`, LMDB `store`, `ops` (`Substrate`), `sweep`, `recipe` (28 stateless Gana transform policies), `projection`, `mesh`, `transport`, `mandala`, journal |
| `crates/wm-gen3-harness` | MCP/JSON-RPC bridge (`bridge.rs`, `mcp_server.rs`) and the production `wm` binary (`src/bin/wm.rs`, "Gate 9B Compatibility Shell") |
| `crates/wm-gen3-shm` | POSIX shared-memory sub-symbolic transport (`/dev/shm`), sub-microsecond inter-agent frames |
| `crates/wm-gen3-systemone` | Optional System One typed-decision organ (wraps the pure-Rust `laya` crate) |
| `crates/wm-gen3-zeropointfive` | System 0.5 retrieval organ: static-embedding shortlist + deliberator cascade |
| `crates/wm-gen3-vault` | Tacit continuity vault miner (cold storage / archive indexing) |

Cargo features that matter:

- `wm-gen3-core/operator` — operator-side construction paths (e.g.
  `RatifiedChannel::mint`). **Never enabled by the adaptive layer.**
- `wm-gen3-core/reference-models` — activates `tests/adversary_contract.rs` and
  the Gate 9D reality battery. Test-only; does not pull extra dependencies
  (both features are empty marker features).

## 2. Build, test, lint (what CI actually runs)

```bash
cargo build --release --bin wm                 # production binary
cargo fmt --all -- --check                     # formatting gate
cargo clippy --workspace --all-targets         # lint gate (not yet -D warnings)
cargo test --workspace                         # default suite
cargo test --workspace --features wm-gen3-core/reference-models \
  -- --skip projection::tests --skip ops::gated_tests   # gate batteries
bash scripts/check_closures.sh                 # 3 static closure rules
python3 scripts/version_truth.py --check       # version-truth surfaces
python3 -m unittest discover -s scripts/tests -v  # release-tooling tests
(cd npm/whitemagic-mcp && node --test)         # npm launcher tests
```

Notes:

- `clippy.toml` + workspace lints apply; CI currently tolerates warnings
  (`cargo clippy --workspace --all-targets`) because ~180 warnings were still
  inventoried on 2026-10-06 (`.github/workflows/ci.yml` TODO).
- The reference-models run is the only place Gate 9A `adversary_contract` and
  the Gate 9D battery compile; `projection::tests` / `ops::gated_tests` are
  skipped there because the default run covers them.
- `justfile` is stale (v5). Use the commands above.
- `wm selftest --json` is the artifact-level smoke used by CI and installers;
  `--strict` exits non-zero on critical host findings (see
  `docs/SELFTEST_AND_HOST_HEALTH.md`).

## 3. Environment knobs that matter (read by code)

| Variable | Read by | Effect |
|---|---|---|
| `WM_STORE` | `wm.rs:909` | Default store path when `--store` is absent |
| `WM_MAP_SIZE_GB` | `store.rs` (`configured_map_size`) | LMDB map size; code default **16 GiB**, production service env sets **32 GiB** (see `STORE_LAYOUT.md`) |
| `WM_GEN3_PROJECTION` | `ops.rs` | Enable dense projection (`1`); CLI `--projection` also sets it |
| `WM_GEN3_PROJECTION_GATED` | `ops.rs`, `wm.rs` | Gate projection behind calibration |
| `WM_GEN3_SWEEP` | `ops.rs` | `0` disables relation candidacy (A1 ablation switch) |
| `WM_GEN3_NOISE` | `ops.rs` | Noise filtering switch |
| `WM_GEN3_DISPERSION` | `ops.rs` | Dispersion switch |
| `WM_GEN3_ARBITRATION` | `ops.rs` | Arbitration mode selection |
| `WM_GEN3_JOURNAL` | `ops.rs` | Journal path override (default `<store>/journal.jsonl`) |
| `WM_GEN3_EMBED_CACHE` | `ops.rs`, `wm.rs` | fastembed cache directory (model layer is opt-in) |
| `WM_SERVE_TOKEN` | `mcp_server.rs:436` | Bearer token for `wm serve --transport http\|sse` |
| `WM_SERVE_ALLOW_REMOTE` | `mcp_server.rs:439` | Required (with token) to bind non-loopback |
| `WM_NODE_ID` | `mesh.rs` | Node identity fallback (after env, hostname) |
| `WM_MESH_PEER_ALLOWLIST` | `mesh.rs` | Pinned peers; empty = loopback only |
| `WM_MESH_SYNC_ALLOWLIST` | `mesh.rs`, `wm.rs` | Gates all dial paths, including the CLI |
| `WM_MESH_ALLOW_REMOTE` | `mesh.rs` | Mesh remote opt-in |
| `WM_MESH_MAX_CONNS` | `mesh.rs` | Connection cap |
| `WM_GEN3_DIAG_PAIRS` | `ops.rs` | Dump diagnostic candidate pairs |
| `WM_GEN3_JOURNAL_HASH_OUT` | `ops.rs` | Dump journal hash evidence |
| `WM_COLD_QUERY` / `WM_COLD_LIMIT` / `WM_SYNC_LIMIT` | tooling/examples | Cold-store query defaults |
| `WM_SANGHA_BIN` / `WM_SYSTEMCTL_BIN` | `wm.rs` | Override external binaries used by sentinel/host tooling |
| `WM_LANDLOCK_CHILD_WORKER`, `WM_TEST_WS`, `WM_TEST_OUTSIDE` | mandala/test helpers | Sandbox worker and test paths — test/tooling only |

Keep `WM_GEN3_*` overrides store-local; `docs/STORE_AND_DATA_HYGIENE.md`
explains why no code path may silently point at the real WMv9 tree.

## 4. Dispatch and authority model (what is actually wired)

- **All canonical mutations** enter through the pulse compiler and a
  `CommitCapability` (linear, payload-digest-bound, `!Send`/`!Sync`); the only
  commit entry points are `SubstrateStore::commit` and
  `KernelStore::commit_mutation`. Raw LMDB writers are `pub(crate)` or behind
  `#[cfg(any(test, feature = "reference-models"))]`.
- **CLI writes** (`wm remember`, `migrate`, `ingest`, `session checkpoint`,
  `mandala …`) dispatch as sovereign pulses; the production path fails closed
  without local intake authority (`RatifiedChannel`) and mints it only on the
  operator side.
- **Concurrent mutation is impossible by design**: `CommitCapability` cannot be
  sent to a thread, and `scripts/check_closures.sh` keeps every `thread::spawn`
  inside physical transports (`transport.rs`, `mesh.rs`, `mcp_server.rs`).
- **Network surfaces are loopback by default**: `wm serve` refuses non-loopback
  binds without `WM_SERVE_ALLOW_REMOTE=1` + `WM_SERVE_TOKEN`; mesh dial paths
  require peer/sync allowlists. Peer identity is Ed25519, never socket/IP.
- **Compatibility**: `wm census`, `wm migrate`/`migrate-all`, `wm quarantine`
  read legacy Gen2 LMDB read-only and write only into a Gen3 target;
  `wm serve --legacy-store <dir>` is a read-only mount.
- **Honest gaps**: `wm host-guard` has a core policy engine and CLI wiring is
  still pending (CHANGELOG 10.2.0-alpha.5); the MCP stdio loop is the primary
  integration surface for agents. There is no authoritative background loop —
  dream/sweep/sentinel work runs only when explicitly invoked or on transport
  turns.

## 5. Release process

- `scripts/release.sh <version>` orchestrates: version bump → release commit →
  push → wait for CI green → signed tag → verify channels → site/hub tails.
- `.github/workflows/release.yml` (tag-triggered) owns the channels: builds
  x86_64/aarch64 Linux + aarch64 macOS + Windows, signs the manifest (Sigstore),
  emits SBOMs, creates the GitHub Release, certifies `install.sh` against the
  published assets, and publishes registries (crates.io, npm, Docker Hub, MCP
  registry).
- `scripts/version_truth.py` lists the surfaces that must agree with
  `Cargo.toml`; `CHANGELOG.md` must carry a dated section for the target
  version. CHANGELOG is not itself a version surface.
- Do not hand-upload artifacts; re-run the workflow instead (provenance rule in
  `release.sh`).

## 6. Session and claims conventions

- Record work with `wm session checkpoint` (CLI) or the `session.*` MCP tools
  (`session.start`, `session.record`, `session.checkpoint`,
  `session.continuity`); sessions are lanes keyed by session id so a resumed
  agent can read the last lane without replaying everything.
- Before editing a shared checkout, check the Sangha board claims
  (`sangha claims` / `sangha inbox --unread`) and take a scoped claim
  (`sangha claim --scope <tree> --intent "…"`), release it when done. One
  writer per checkout; claims are advisory coordination, not authority.
- Board lint rides in `sangha brief` (`lint: 0 errors · N warnings`); keep
  errors at 0 after board-touching work. Never post credentials.
- The agent-facing onboarding lives in `skill.md` and the `sangha-whiteboard` /
  `whitemagic` skills; host-specific session rhythm is operator-local and not
  part of this repository.
