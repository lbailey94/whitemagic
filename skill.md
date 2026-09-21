# WhiteMagic — agent skill

Operational quickstart for AI agents that cloned this repository. Goal: from clone to durable memory and session continuity in under five minutes, without reading the whole codebase.

## What this is

Local-first memory and session continuity for coding agents, exposed over MCP. A single Rust binary (`wm`) runs a stdio JSON-RPC server your MCP client talks to. Memory is stored on-device; no usage telemetry, prompts, or memories are transmitted off-device by default. WhiteMagic does keep local diagnostic evidence on-device (e.g., RSI friction records), and update checks fetch a public, static release manifest. Optional model/embedding backends degrade truthfully when absent.

## Install and verify

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-skill | sh
wm --version         # expect: wm 9.2.2
wm grimoire          # guided first-run (when present); --json for a machine-readable report
# builds without grimoire: use the step-by-step path below
wm quickstart        # throwaway demo store — a decision survives a restart
wm selftest --json   # 8 end-to-end invariants on a throwaway store
wm connect --write   # detect installed MCP clients and wire each (dry-run first: wm connect)
wm setup             # per-client view: wm setup <client> [--write]
wm ingest --source <folder> --dry-run   # preview: walk notes/docs into a galaxy (local-only)
```

`wm doctor` is the troubleshooting tool — run it when something misbehaves, not on a healthy fresh install.
Building from source instead: `cargo build --release` in this repository, then install `target/release/wm` onto your `PATH`.

## Wire your MCP client

Claude Desktop, Cursor, Codex, Gemini CLI, opencode — any MCP client:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "wm",
      "args": ["serve", "--profile", "curated"]
    }
  }
}
```

The `curated` profile is the supported surface: explicit, dependable routes instead of an unbounded tool catalog.

## First useful actions

1. **Record something worth keeping** — a decision, not raw transcript:
   the memory layer is for distilled context.
2. **Search before re-deriving** — lexical search works with no
   external model; embedders improve ranking when available.
3. **Checkpoint at the end of real work** — sessions support record,
   replay, and cross-session continuity, so the next session resumes
   from evidence instead of re-reading everything.
4. **Load your documents when you have them** — `wm ingest` is
   dry-run-first, scrubs credential-shaped content with `--redact`, and
   resumes on re-run (per-file SHA-256 ledger; nothing leaves the machine).

## Vocabulary (explicit routes are the contract)

| You mean | Route |
|---|---|
| begin / resume a work session | `session.start` |
| remember / record this | `memory.create` |
| find X / what do you remember about X | `memory.search` |
| what did we decide about X | `memory.search` |
| resume where we left off | `session.continuity` |
| correct an earlier belief | `memory.update` (supersede; pass `galaxy` for non-default galaxies) |
| discover the surface | `tools.list` |
| finish the session | `session.record` summary + `session.checkpoint` |

`session.record` and `session.checkpoint` require an active session — call
`session.start` first (errors say so explicitly if you forget). Natural-language
phrasing is a convenience layer; explicit `route=` dispatch is the dependable
path for anything that matters.

## Operating notes

- Trusted, local, single-user operation; Linux Landlock containment
  and firebreak guards are part of the contract.
- Backup/verify/restore exists and is a first-class path — use it
  before risky operations.
- The web surface (https://whitemagic.dev) is a discovery surface,
  not a host: it never holds your memories.
- Security posture and reporting: [SECURITY.md](SECURITY.md).
- Privacy: [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## Where to read more

- [README.md](README.md) — product overview and supported contract.
- [CHANGELOG.md](CHANGELOG.md) — release history.
- [docs/](docs/) — architecture and operations documentation.
- Machine-readable identity: https://whitemagic.dev/ai-agent.json
