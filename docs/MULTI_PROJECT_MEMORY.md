# Multi-Project Memory Isolation

**Scope:** per-project stores, mode disclosure, and hygiene conventions for
running WhiteMagic across several projects without cross-project pollution.

## Problem this solves

One store per machine means every project shares one memory. Observed in
practice before isolation:

- `session.continuity` returned unrelated projects' sessions — wasted context
  and confused handoffs.
- Agents could not tell they were on a read-only server until a write was
  refused, burning turns.
- Failed dispatches on a read-only server left no telemetry.

## The fix: one store per project

| Scope | Store | Mode | Config |
|---|---|---|---|
| unconfigured fallback | the default store (or a scratch store) | read-only | global client config |
| each project | `data/WMdata/projects/<name>` | writable | `<project>/opencode.jsonc` |

Rules of the layout:

1. **The global fallback is read-only** against a scratch or default store.
   An unknown project gets safe recall-only memory; it cannot pollute anything.
2. **Each project overrides the `whitemagic` entry** with its own `--store`
   path and no `--readonly`.
3. **Set `WM_PROJECT=<name>`** in the server environment. The label is
   disclosed to agents at handshake so they can confirm scope.
4. One server per project session: project configs disable any generic
   fallback when they provide their own (`{"enabled": false}`).

### Adding a new project (copy-paste)

Create `<project>/opencode.jsonc`, replacing `<wm-binary>`,
`<project-store>`, and `<name>`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "whitemagic": {
      "type": "local",
      "command": [
        "<wm-binary>",
        "serve",
        "--profile",
        "curated",
        "--store",
        "<project-store>"
      ],
      "enabled": true,
      "environment": {
        "RUST_LOG": "warn",
        "WM_PROJECT": "<name>"
      }
    }
  }
}
```

Restart the client (config is loaded once at startup). Verify with a
handshake: the `initialize` instructions must say `Mode: writable` and name
the project; `session.continuity` must return zero turns on first use.

## Server-side disclosure

`McpServer` carries `store_path` and `project` (from `WM_PROJECT`) and
discloses both in two places:

- **`initialize.instructions`** — after the session rhythm, a mode line
  (`READ-ONLY — do not retry writes` vs `writable`) and a scope line
  (`project '<name>', store <path>`). This text is what MCP clients inject
  into agent system prompts, so the agent knows the boundary before acting.
- **`tools/list` description** — same mode + scope summary inline.

Read-only write refusals are actionable on both dispatch paths (direct
JSON-RPC error and `wm`-routed `{"status":"error"}` payloads): they append a
hint naming the read-only server and pointing at the writable alternative.

## The `wm connect` warning

Client-global wiring (`wm connect`, `wm setup <client>`) writes entries that
all point at the default store. That is correct for a single-project machine
and wrong for several: sessions and memories cross-contaminate silently.
WhiteMagic therefore prints a project-isolation warning when the working
directory is a git repository without project-scoped wiring — the fix is the
per-project config above.

## Hygiene conventions

- Tag memories with `project:<name>` when a store's history predates
  isolation or when deliberately importing across stores.
- `session.export` / `session.import` move full sessions (ids, timestamps,
  and tags preserved) between stores when history needs re-homing.
- Back up each project store; a store without a verified backup is one
  mistake away from gone (`wm backup` + `wm restore` verify checksums).
