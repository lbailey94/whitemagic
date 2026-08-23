# Multi-Project Memory Isolation

**Status:** live as of 2026-08-22 (verified end-to-end against the release
binary)
**Scope:** per-project stores, mode disclosure, and hygiene conventions for
running WhiteMagic across many side projects without cross-project pollution.

## Problem this solves

Before isolation, every opencode session on the machine shared one store
(`WMdata/opencode-v5`) through a single global read-only MCP server. The
results, all observed in practice on 2026-08-22:

- `session.continuity` from the WMv5 repo returned five NEON (unrelated game
  project) sessions — wasted tokens and context confusion.
- Agents could not tell they were on a read-only server until a write was
  refused (`governance violation: server is read-only`), burning turns.
- Friction logging is suppressed in read-only mode, so failed dispatches left
  no telemetry — the RSI pipeline was blind exactly where agents struggled.

## The fix: one store per project

| Project | Store | Mode | Config file |
|---|---|---|---|
| any unconfigured | `WMdata/projects/default` | read-only | global `~/.config/opencode/opencode.jsonc` |
| WMv5 | `WMdata/opencode-v5` (historical) | writable | `~/Desktop/WMv5/opencode.jsonc` (server name `whitemagic-dev`, per AGENTS.md) |
| NEON | `WMdata/projects/neon` | writable | `~/Desktop/NEON/opencode.jsonc` |
| whitemagic-site | `WMdata/projects/whitemagic-site` | writable | `~/Desktop/whitemagic-site/opencode.jsonc` |

Rules of the layout:

1. **Global fallback is read-only** against a scratch store. An unknown
   project gets safe recall-only memory; it cannot pollute anything.
2. **Each project overrides the `whitemagic` entry** (or enables
   `whitemagic-dev` for WMv5) with its own store and no `--readonly`.
3. **Every project sets `WM_PROJECT=<name>`** in the server environment. The
   label is disclosed to agents at handshake so they can confirm scope.
4. One server per project session: project configs disable the generic
   fallback when they provide their own (`{"enabled": false}`).

### Adding a new project (copy-paste)

Create `<project>/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "whitemagic": {
      "type": "local",
      "command": [
        "/home/lucas/Desktop/WMv5/target/release/wm",
        "serve",
        "--profile",
        "curated",
        "--store",
        "/home/lucas/Desktop/WMdata/projects/<name>"
      ],
      "enabled": true,
      "environment": {
        "RUST_LOG": "warn",
        "WM_DISPATCH_TOOL_RPM": "600",
        "WM_DISPATCH_GLOBAL_RPM": "3000",
        "WM_DISPATCH_BURST": "50",
        "WM_PROJECT": "<name>"
      }
    }
  }
}
```

Restart opencode (config is loaded once at startup). Verify with a handshake:
the `initialize` instructions must say `Mode: writable` and name the project;
`session.continuity` must return zero turns on first use.

## Server-side disclosure (implemented 2026-08-22)

`McpServer` now carries `store_path` and `project` (from `WM_PROJECT`) and
discloses both in two places:

- **`initialize.instructions`** — after the session rhythm, a mode line
  (`READ-ONLY — do not retry writes` vs `writable`) and a scope line
  (`project '<name>', store <path>`). This text is what MCP clients inject
  into agent system prompts, so the agent knows the boundary before acting.
- **`tools/list` description** — same mode + scope summary inline.

Read-only write refusals are now actionable on both dispatch paths (direct
JSON-RPC error and `wm`-routed `{"status":"error"}` payloads): they append
`(hint: this MCP server was started with --readonly — point this project's
config at a writable server …)`.

Tests: `tools_list_discloses_mode_store_and_project`,
`initialize_instructions_disclose_mode_and_scope`,
`readonly_write_refusal_is_actionable` (wm-mcp/src/server.rs).

## Session-resolution lottery (fixed 2026-08-22, bonus find)

`session.record` and `session.continuity` resolved "most recent session"
positionally over an LMDB scan — but LMDB iterates by UUID key, which is
random for v4, so turns were silently misfiled into arbitrary sessions
whenever more than one start existed. Reproduced live: a fresh session's
first record landed inside an old NEON session in the same store.

Fix: both tools now resolve by `created_at`
(wm-tools/src/expansion/session_ops.rs). Regression tests:
`record_defaults_to_newest_start_by_time_not_key_order`,
`continuity_picks_newest_prior_by_time_not_key_order`.

## Hygiene conventions

- Tag memories with `project:<name>` when a store's history predates
  isolation or when deliberately importing across stores.
- Backfill done 2026-08-22: the seven NEON-origin memories in
  `WMdata/opencode-v5` are tagged `project:neon` + `migrated:opencode-v5`.
- Historical sessions cannot be re-homed (no session export/import yet); they
  remain in `opencode-v5`. Continuity bleed from old NEON turns is accepted
  there until session scoping lands.

## Known gaps / follow-ups

1. **Friction blind spot in read-only mode** — friction auto-log, karma,
   audit journal, and stats persistence are all gated on `!readonly`, so RO
   servers record nothing about the failures agents hit. Consider a sidecar
   JSONL friction sink for RO mode.
2. **No session export/import** — needed to re-home historical sessions.
3. **Tantivy lag on RO search** — a read-only open does not observe writes
   made after it started; restart RO servers after writing to a store.
4. **Stray `wm serve` processes hold the Tantivy lock** — if a writable open
   fails with `LockBusy`, check `pgrep -af "wm serve"` before assuming
   corruption.
5. **Soft scoping (tier 2)** — `WM_PROJECT` is currently disclosure-only;
   stamping it onto memories/sessions and filtering continuity by it would
   make recall project-aware inside a shared store if ever needed again.
