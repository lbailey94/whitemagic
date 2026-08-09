# Next Session Handoff — 2026-08-08 (evening)

State as of the end of the evening 2026-08-08 session. Working tree has
uncommitted changes (this session's hardening) — see git status.

## Current State (v5.3.0)

- **15 crates, 195 tools, 3,240 tests (0 failed), ~131,000 LOC**
- 0 clippy warnings (`cargo clippy --all-targets`), fmt clean, cargo-deny all green
- 0 lock panics in production code (72 sites converted to graceful degradation)
- Live store: `~/Desktop/WMdata/live` — 58,617 memories / 10 galaxies
- Conformal prediction shipped (v5.2.2, `wm-conformal` crate + 7 tools)
- Daemon handles SIGTERM + has a stall watchdog + panic resilience

## What was done this session (hardening batch, all 4 items)

1. **MCP boundary enforcement** — the validation layer (`validate_request` /
   `validate_tools_call`) existed but was **dead code**: SSRF, path traversal,
   injection and the 64KB params cap were never enforced on the live path.
   Now wired into `handle()`: malformed → `-32602`; SSRF/traversal → rejected;
   oversized params → rejected. Added `RequestBudget` (default 10k
   requests/connection, `--max-requests` flag on `wm serve`) and bounded
   stdin reads (1MB line cap, sync + async).
2. **Daemon watchdog** — stall detection thread (default 60s timeout,
   `--watchdog-timeout` / `[daemon] watchdog_timeout_secs`): logs CRITICAL,
   grace window for state save, force-exits for supervisor restart. All five
   heavy cycles wrapped in `catch_unwind` — component panics no longer kill
   the daemon.
3. **Fuzz corpus seeds committed** — 76 curated `seed_*` files across all 7
   targets (previously only auto-generated nlu_classify inputs, untracked).
   Fixed `fuzz/Cargo.toml` (missing `serde` — json_rpc_parse didn't compile)
   and `wm-polyglot` (jlrs enabled without a Julia version feature — broke
   `clippy --all-features`; added `julia-1-10`).
4. **`wm doctor` conformal health** (section 10) — reports classifier/
   regressor/APS fitted status, sample counts, alphas from
   `<store>/conformal_store.json`; guides calibration when absent.

Also: doc count correction 192 → **195 tools** (doctor was right all along),
doctest fix in wm-conformal (pre-`&[f64]` example didn't compile), version
bumped 5.2.2 → **5.3.0**.

## Known environment constraint

- `cargo clippy --all-targets --all-features` requires **Julia dev headers**
  (`julia_version.h`) because `wm-polyglot`'s `julia` feature builds
  jl-sys C shims. On machines without Julia, use
  `cargo clippy --all-targets` (the repo's own `just verify` recipe uses
  `--all-features` — will fail without Julia installed).

## Recommended next steps (in priority order)

### A. Phase 1 gap porting (from GAP_ANALYSIS.md §5) — the open work
All four hardening items from the handoff are done. Phase 1 porting is now
the highest-value work. Start with web + research:
1. **Web**: `web_fetch`, `web_search`, `web_search_and_read`, `deep_fetch` (keyless, dependency-light — v26 had them as Python httpx tools)
2. **Research**: `research_topic`, `research_repo`, `rabbit_hole_research`
3. **Session**: `session.record`/`replay`/`continuity`/`handoff_transfer`

Pattern: v26 sources are at `~/Desktop/WHITEMAGIC/core/whitemagic/tools/registry_defs/` (definitions) + handlers; docs at `~/Desktop/WMdocs/docs-2/api/tools/`. Port as new tools in `crates/wm-tools/src/expansion/` following the conformal.rs pattern (struct + Tool impl + register fn + tests). New tools will bump the count past 195 — update README/AGENTS/CHANGELOG counts when done.

### B. Net-new features
- **Brier scorecard** (`simulation.calibrate` equivalent) — complements conformal
- **GP/Bayesian optimization** (`mc.surrogate`, `mc.optimize`) — Rust-native
- Wire `CoverageReport` into selfmodel for live drift alerts (conformal monitoring)
- Auto-persist conformal store on server shutdown (`conformal_store.json`) so
  `wm doctor` sees live calibration without manual export

### C. More hardening ideas (not done)
- Request **rate limiting** (time-windowed tokens) beyond the hard request cap
- Conformal state persistence hook in `save_mutable_state()`
- Fuzz corpus regression: run each target briefly in CI with the committed seeds

## Useful commands

```bash
# WMv5
just verify          # fmt + clippy (needs Julia headers) + tests + deny
cargo clippy --all-targets   # clippy without Julia deps
cargo test --workspace
wm doctor --store ~/Desktop/WMdata/live
wm serve --store <path> --max-requests 10000   # request budget
wm daemon --watchdog-timeout 60                # stall watchdog

# Fuzz (from fuzz/ dir)
cargo fuzz run --fuzz-dir . <target> -- -runs=1000   # seeds in fuzz/corpus/<target>/

# Vault
ls ~/Desktop/WMdata    # live store, v26 SQLite, v4 LMDB, archives
ls ~/Desktop/WMdocs    # all documentation
```

## Repos

| Repo | Location | State |
|---|---|---|
| WMv5 (active) | `~/Desktop/WMv5` | working tree has this session's hardening, uncommitted |
| v26 reference | `~/Desktop/WHITEMAGIC` | clean (docs/data moved out) |
| WMv4 snapshot | `~/Desktop/WHITEMAGIC/whitemagic-v4` | untracked, own git, superseded |

## Gotchas / notes

- Version aligned at **5.3.0** (Cargo.toml workspace, clap attribute, README,
  CHANGELOG, PROGRESS, GAP_ANALYSIS).
- `fuzz/corpus/` is partially gitignored: only `seed_*` files are tracked;
  libFuzzer-regenerated sha1 files stay ignored — never `git add -A fuzz/corpus/`
  after a fuzz run.
- `wm doctor`/`stats` need `--store ~/Desktop/WMdata/live` to see the migrated memories.
- The `fuzz/` crate is excluded from the workspace (`exclude = ["fuzz"]`).
- Tool count is **195** (was misreported as 192 in v5.2.2 docs).
