# Next Session Handoff — 2026-08-11 (morning)

State as of the morning 2026-08-11 session. Working tree has uncommitted
changes (claims ledger morning review, shadow-mode data collection, and a
bug fix) — see git status.

## Current State (v5.7.7)

- **15 crates, 229 tools, 3,391 tests (0 failed), ~131,000 LOC**
- 0 clippy warnings (`cargo clippy --all-targets`), fmt clean, cargo-deny all green
- 0 lock panics in production code (72 sites converted to graceful degradation)
- Live store: `~/Desktop/WMdata/live` — 58,617 memories / 10 galaxies
- **Phase-1 gap porting COMPLETE** (v26 parity): web (`web.fetch/deep_fetch/search/search_and_read`), research (`research.topic/repo/rabbit_hole`), session (`session.record/replay/continuity/handoff`)
- External merkle anchors: `karma.anchor` `publish_path` → chained JSONL at `anchors/karma_anchors.jsonl` (38 entries)
- Claims ledger versioned in repo: `docs/CLAIMS_LEDGER.json` + `.md` + `CLAIMS_LEDGER_REVIEW.json`; 32 claims (19 validated, 1 falsified, 12 pending); calibration mean Brier 0.078, **+0.215 overconfident**
- Conformal drift monitoring, Brier scorecard, GP/Bayesian optimization, MC suite, ACS compliance, self-play, imagination, learned router, mutable structures — all wired and persisting

## What was done this session (2026-08-11 morning)

1. **Morning claims review** — news sweep; all pending claims kept (0026/0027/0028
   got strong partial signals: Anthropic inference hooks, MCP 2026-07-28 hardened
   auth, PEAC signed-proof standard, CSA AIUC-1 — but none meet the falsification
   bar). Three new claims entered (live ledger + docs synced):
   - **claim-0029** (conf 0.65): org-injectable policy hooks become standard after Anthropic's inference hooks beta
   - **claim-0030** (conf 0.70): per-agent spending caps/wallets become standard after Cloudflare Wallets
   - **claim-0031** (conf 0.60): EU AI Act Art. 50 first significant enforcement within 12 months
2. **NLU shadow mode — first real data** (see `docs/notes/shadow-mode-analysis-2026-08-10.md`)
   - Deployed nomic-embed-text-v1.5 Q4_K_M via llama-server `--embeddings` (port 8081)
   - Collected 115 real NLU queries through the `wm` meta-tool (collector: `scripts/collect_shadow_data.py`)
   - **Verdict: NOT promotion-ready — 42.6% disagreement** (threshold 20%); embedding router loses to TF-IDF on core patterns, incl. dangerous misroutes (`karma.clear` for "show my karma")
   - **Bug fixed**: `nlu.shadow_report` was unreachable via `wm(route=...)` (only top-level registered); now registered inside the meta-tool routing registry + regression test
3. **Docs sync** — README/AGENTS/PROGRESS counts corrected to 229 tools / 3,391 tests

## Recommended next steps (in priority order)

1. **Embedding router improvement** (biggest open question in NLU):
   - Rewrite `tool_descriptions()` in `embedding_router.rs` with intent-anchored descriptions (verbs + example queries) — the router is only as good as these
   - Consider margin-based selection (best vs second-best gap) instead of plain top-1, falling back to TF-IDF on ties
   - Retest with the shadow collector; target < 20% disagreement
2. **Dispatch rate limiter review** — `wm-dispatch` `RateLimiter::default()` caps any tool at 60 RPM + 10 burst = 70 calls/min; the `wm` meta-tool is throttled in real use. Consider env-configurable limits
3. **Claims ledger** — evening review after this session; watch 0026/0027/0028 signals (agent-comms monitoring count, MCP/A2A signing, message-board governance)
4. **NLU promotion decision** — needs ≥1,000 organic queries from the live daemon run with `WM_EMBEDDER_ENDPOINT` set; only then decide on TF-IDF retirement

## Useful commands

```bash
# WMv5
cargo clippy --all-targets   # clippy without Julia deps
cargo test --workspace
wm doctor --store ~/Desktop/WMdata/live; echo "exit: $?"   # health check exit code
wm serve --store <path> --max-requests 10000 --rate-limit 600
wm daemon --watchdog-timeout 60

# Shadow-mode data collection (needs llama-server embedding endpoint)
llama-server -m ~/models/embedding/nomic-embed-text-v1.5.Q4_K_M.gguf --embeddings --port 8081 -c 16384 -np 8
WM_EMBEDDER_ENDPOINT=http://127.0.0.1:8081 WM_EMBEDDER_DIM=768 WM_EMBEDDER_TIMEOUT_MS=120000 wm serve --store <path>
python3 scripts/collect_shadow_data.py   # drives 115 NLU queries + shadow report

# Vault
ls ~/Desktop/WMdata    # live store, v26 SQLite, v4 LMDB, archives
ls ~/Desktop/WMdocs    # all documentation
```

## Repos

| Repo | Location | State |
|---|---|---|
| WMv5 (active) | `~/Desktop/WMv5` | working tree has this session's changes, uncommitted |
| v26 reference | `~/Desktop/WHITEMAGIC` | clean (docs/data moved out) |
| WMv4 snapshot | `~/Desktop/WHITEMAGIC/whitemagic-v4` | untracked, own git, superseded |

## Gotchas / notes

- Version aligned at **5.7.7** (Cargo.toml workspace, clap attribute, README, CHANGELOG).
- `nlu.shadow_report` now reachable ONLY via `wm(route="nlu.shadow_report")` (it is registered inside the meta-tool registry — do not move it back to top-level-only).
- Embedder init embeds ~229 tool descriptions in one HTTP batch — on CPU this takes ~45–60s; the 30s default `WM_EMBEDDER_TIMEOUT_MS` silently disables the router (falls back to TF-IDF). Use 120s+ on CPU.
- Dispatch pipeline rate limiter: 60 RPM/tool + 10 burst default — a data-collection run needs cooldowns between 60-query batches.
- `mutable_shadow_stats.json` persists to `<store>/lmdb/` (not store root).
- Fuzz corpus: only `seed_*` files tracked; never `git add -A fuzz/corpus/` after a run.
- The `fuzz/` crate is excluded from the workspace.
