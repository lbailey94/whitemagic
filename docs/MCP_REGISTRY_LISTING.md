# MCP Registry Listing Kit

**Version**: 5.8.0

Copy for the official MCP registry and server directories.

## One-liner

> Local-first memory and session continuity for AI agents — one MCP server
> that remembers project context, finds it after restart, and carries work
> across sessions without sending data to a hosted service.

## Short description

WhiteMagic gives coding agents persistent, auditable memory. It stores
memories in a local LMDB database with fast full-text search (Tantivy BM25),
records conversation turns with session replay and cross-session continuity,
and ships safety by default: destructive tools require explicit confirmation,
read-only mode coexists with other processes, and private memories never leak
into agent responses. One binary, no cloud, no telemetry.

## Feature bullets

- Persistent memory with BM25 full-text search, hybrid recall, and metadata filtering
- Session recording, replay (full/selective/progressive), continuity, and handoff
- Transactions: snapshot the whole store and roll back byte-exact records
- Self-grading claims ledger (Brier scorecard + calibration) for calibrated predictions
- Privacy flags: private memories excluded from responses; model-exclude from reasoning
- Fail-closed compartments and a store-wide read-only mode
- Curated release profile (46 tools) with JSON schemas and safety annotations
- Optional semantic routing via any OpenAI-compatible embeddings endpoint
- Single static Rust binary; works on Linux, macOS, Windows
- MIT licensed

## Tags

memory, sessions, context, agent, mcp, local-first, rust, lmdb, tantivy

## Quality prep (before submitting)

- [ ] Binary released with per-platform sha256 checksums
- [ ] `wm doctor` and the curated smoke test pass against the release binary
- [ ] Tool annotations present (readOnlyHint/destructiveHint in tools.list)
- [ ] README quickstart verified on a clean machine
- [ ] All benchmark/feature claims cite a fresh run against the release commit
- [ ] SECURITY.md, PRIVACY_POLICY.md, and TERMS_OF_SERVICE.md present
- [ ] Version string matches the release tag

## Launch narrative

Frame around token economics and continuity:

> Models don't need to be bigger — they need to stop wasting tokens on
> housekeeping. WhiteMagic remembers decisions, replays only the turns that
> matter, and hands context across restarts. Your agent stops re-deriving
> project state and starts building on it.

Lead with session continuity: it is the feature users feel on day one.
