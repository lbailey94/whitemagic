# Next Session Handoff — 2026-08-08 (late session)

State as of the end of the late 2026-08-08 session. Working tree has
uncommitted changes (this session's features) — see git status.

## Current State (v5.6.0)

- **15 crates, 204 tools, 3,335 tests (0 failed), ~131,000 LOC**
- 0 clippy warnings (`cargo clippy --all-targets`), fmt clean, cargo-deny all green
- 0 lock panics in production code (72 sites converted to graceful degradation)
- Live store: `~/Desktop/WMdata/live` — 58,617 memories / 10 galaxies
- Conformal prediction + drift monitoring, Brier scorecard, GP/Bayesian optimization, MC suite complete
- ACS compliance surface (`dharma.acs` report/export/import) + prescience claims ledger (`claims.*`) shipped
- Daemon: SIGTERM graceful shutdown + stall watchdog + panic resilience
- MCP boundary: validation enforced, request budget, rate limit, bounded reads

## What was done this session (4 work streams)

1. **Conformal drift monitoring** — `conformal.monitor` tool evaluates
   empirical coverage (sets or intervals + truths) and feeds a new
   `ConformalCoverage` self-model metric; alert engine fires drift alerts
   (< 0.85 warning / < 0.80 critical by default). Conformal state now
   **auto-persists** to `<store>/conformal_store.json` on shutdown and
   restores on startup — the `wm doctor` loop is closed.
2. **Brier scorecard** — new `wm-simulation::calibration` module with the
   full Murphy decomposition (reliability / resolution / uncertainty /
   Brier skill score). `simulation.calibrate` tool: record / resolve /
   scorecard; state persists to `<store>/calibration_store.json`.
3. **GP + Bayesian optimization** — new `wm-simulation::bayesian` module
   (pure Rust: Cholesky GP, EI acquisition, BayesianOptimizer, tiny safe
   `Expr` evaluator with correct `-x^2 = -(x^2)` precedence). Tools:
   `mc.surrogate`, `mc.optimize` (`fitness_expr` like `"-(x[0]-3)^2+5"`).
4. **Hardening** — time-windowed `RateWindow` rate limiting at the MCP
   boundary (`wm serve --rate-limit`, default 600/min); `wm doctor` now
   returns real issue counts with exit code 1 on problems; CI fuzz workflow
   replays the committed seed corpora before timed runs.
5. **MC suite completion** — `mc.rare_event` (subset simulation with proper
   MH acceptance + importance sampling), `mc.sde` (Euler/Milstein, GBM/OU,
   two-level MLMC), `mc.superforecaster` (LHS → PCE/Sobol' → BO).
6. **GP hyperparameter fitting** — `log_marginal_likelihood` +
   `fit_hyperparameters` (BO over log-hyperparameters, dogfooding);
   `mc.surrogate fit_hyperparameters: true`.
7. **Brier → self-model** — new `BrierScore` metric (lower better, 0.15/0.3
   alert thresholds); `simulation.calibrate` scorecard records Brier and
   fires drift alerts. The feedback triangle is complete.

## Known environment constraint

- `cargo clippy --all-targets --all-features` requires **Julia dev headers**
  (`julia_version.h`) because `wm-polyglot`'s `julia` feature builds
  jl-sys C shims. On machines without Julia, use
  `cargo clippy --all-targets` (the repo's `just verify` recipe uses
  `--all-features` — fails without Julia installed).

## Recommended next steps (in priority order)

### A. Phase 1 gap porting (from GAP_ANALYSIS.md §5) — the open work
All handoff hardening items are done, plus the net-new Brier/GP/BO features.
Phase 1 porting is the highest-value remaining work. Start with web + research:
1. **Web**: `web_fetch`, `web_search`, `web_search_and_read`, `deep_fetch`
2. **Research**: `research_topic`, `research_repo`, `rabbit_hole_research`
3. **Session**: `session.record`/`replay`/`continuity`/`handoff_transfer`

Pattern: v26 sources at `~/Desktop/WHITEMAGIC/core/whitemagic/tools/registry_defs/`
+ handlers; docs at `~/Desktop/WMdocs/docs-2/api/tools/`. Port as new tools in
`crates/wm-tools/src/expansion/` (struct + Tool impl + register fn + tests).
New tools bump the count past 199 — update README/AGENTS/CHANGELOG counts.

### B. Remaining net-new from the gap list
- `mc.rare_event` (subset simulation), `mc.sde` (Euler-Maruyama/Milstein)
- `mc.superforecaster` (LHS→PCE→Sobol→BO orchestrator) — the bayesian module
  is now a solid foundation for this
- Session tools are the only Phase-1 gap with real data-model work

### C. More hardening ideas (not done)
- Conformal `CoverageReport` drift alert → wire into `wm doctor` health
  (currently only reads calibration state, not live coverage)
- Fuzz corpus regression already in CI; could add a `just fuzz` recipe
- Brier scorecard → self-model metric integration (like ConformalCoverage)

## Useful commands

```bash
# WMv5
cargo clippy --all-targets   # clippy without Julia deps
cargo test --workspace
wm doctor --store ~/Desktop/WMdata/live; echo "exit: $?"   # health check exit code
wm serve --store <path> --max-requests 10000 --rate-limit 600
wm daemon --watchdog-timeout 60

# Fuzz (from fuzz/ dir)
cargo fuzz run --fuzz-dir . <target> -- -runs=1000   # seeds in fuzz/corpus/<target>/

# Vault
ls ~/Desktop/WMdata    # live store, v26 SQLite, v4 LMDB, archives
ls ~/Desktop/WMdocs    # all documentation
```

## Repos

| Repo | Location | State |
|---|---|---|
| WMv5 (active) | `~/Desktop/WMv5` | working tree has this session's features, uncommitted |
| v26 reference | `~/Desktop/WHITEMAGIC` | clean (docs/data moved out) |
| WMv4 snapshot | `~/Desktop/WHITEMAGIC/whitemagic-v4` | untracked, own git, superseded |

## Gotchas / notes

- Version aligned at **5.6.0** (Cargo.toml workspace, clap attribute, README,
  CHANGELOG, PROGRESS, GAP_ANALYSIS).
- `fuzz/corpus/` is partially gitignored: only `seed_*` files are tracked;
  libFuzzer-regenerated sha1 files stay ignored — never `git add -A fuzz/corpus/`
  after a fuzz run.
- `wm doctor`/`stats` need `--store ~/Desktop/WMdata/live` to see migrated memories.
- The `fuzz/` crate is excluded from the workspace (`exclude = ["fuzz"]`).
- Tool count is **202**.
- `conformal_store.json` and `calibration_store.json` live at the **store root**
  (parent of `lmdb/`), not inside it — doctor and server agree on this path.
