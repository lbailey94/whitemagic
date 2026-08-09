# Next Session Handoff — 2026-08-08

State as of the end of the 2026-08-08 session. Everything is committed and
clean in both repos.

## Current State (v5.2.2)

- **15 crates, 192 tools, 3,212 tests (0 failed), ~131,000 LOC**
- 0 clippy warnings, fmt clean, 0 dependency vulnerabilities (cargo-deny all green)
- 0 lock panics in production code (72 sites converted to graceful degradation)
- Live store: `~/Desktop/WMdata/live` — 58,617 memories / 10 galaxies
- Conformal prediction shipped (new `wm-conformal` crate + 7 tools)
- Daemon now handles SIGTERM (Docker/systemd graceful shutdown)

## What was done this session

1. **Repo consolidation**: v26 reference repo → code-only; all docs → `~/Desktop/WMdocs`; all data/DBs/memories → `~/Desktop/WMdata`; git history pruned of blobs >5MB.
2. **v26→v5 gap analysis** (`docs/GAP_ANALYSIS.md`): 849 v26 tools vs 192 v5; ~86 worth porting in 10 capability gaps; ~720 definitively skip.
3. **Hardening**: pyo3 0.22→0.29 + tantivy 0.22→0.26 (2 vulns → 0); cargo-deny + fuzz CI; 72 lock panics → graceful; SIGTERM handling; fuzz infra fixed.
4. **Net-new feature**: conformal prediction with statistically verified coverage guarantees.

## Recommended next steps (in priority order)

### A. Phase 1 gap porting (from GAP_ANALYSIS.md §5)
The highest-value work. Start with web + research:
1. **Web**: `web_fetch`, `web_search`, `web_search_and_read`, `deep_fetch` (keyless, dependency-light — v26 had them as Python httpx tools)
2. **Research**: `research_topic`, `research_repo`, `rabbit_hole_research`
3. **Session**: `session.record`/`replay`/`continuity`/`handoff_transfer`

Pattern: v26 sources are at `~/Desktop/WHITEMAGIC/core/whitemagic/tools/registry_defs/` (definitions) + handlers; docs at `~/Desktop/WMdocs/docs-2/api/tools/`. Port as new tools in `crates/wm-tools/src/expansion/` following the conformal.rs pattern (struct + Tool impl + register fn + tests).

### B. Net-new features
- **Brier scorecard** (`simulation.calibrate` equivalent) — complements conformal
- **GP/Bayesian optimization** (`mc.surrogate`, `mc.optimize`) — Rust-native
- Wire `CoverageReport` into selfmodel for live drift alerts (conformal monitoring)

### C. More hardening ideas (not done)
- MCP input size limits / request budget enforcement at the boundary
- Daemon watchdog / auto-restart on critical failure
- Fuzz corpus seeds committed for faster CI fuzzing
- `wm doctor` reporting conformal calibration health

## Useful commands

```bash
# WMv5
just verify          # fmt + clippy + tests + deny
just audit           # cargo deny check
cargo test --workspace
wm doctor --store ~/Desktop/WMdata/live
wm migrate --v2-dir ~/Desktop/WMdata/v26/state/users/local/galaxies  # v26 → v5 migration

# Vault
ls ~/Desktop/WMdata    # live store, v26 SQLite, v4 LMDB, archives
ls ~/Desktop/WMdocs    # all documentation
```

## Repos

| Repo | Location | State |
|---|---|---|
| WMv5 (active) | `~/Desktop/WMv5` | clean, 4 commits ahead of fork |
| v26 reference | `~/Desktop/WHITEMAGIC` | clean (docs/data moved out) |
| WMv4 snapshot | `~/Desktop/WHITEMAGIC/whitemagic-v4` | untracked, own git, superseded |

## Gotchas / notes

- v5 git history has 3 commits: fork → refactor → hardening → conformal+docs. All committed.
- The `fuzz/` crate is excluded from the workspace (`exclude = ["fuzz"]`); run fuzz targets with `cargo fuzz run --fuzz-dir . <target>`.
- `wm doctor`/`stats` need `--store ~/Desktop/WMdata/live` to see the migrated memories.
- Version aligned at **5.2.2** everywhere (Cargo.toml, clap attribute, README, CHANGELOG). Bump to 5.3.0 on the next feature commit.
- The `models/` symlinks in the v26 repo point at the vault; the v26 `bitmamba.cpp` stub was removed.
