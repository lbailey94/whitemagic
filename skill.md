# WhiteMagic — agent skill

Operational quickstart for AI agents that cloned this repository. Goal: from clone to durable memory and session continuity in under five minutes, without reading the whole codebase.

## What this is

Local-first memory and session continuity for coding agents, exposed over MCP. A single Rust binary (`wm`) runs a stdio JSON-RPC server your MCP client talks to. Memory is stored on-device; no usage telemetry, prompts, or memories are transmitted off-device by default. WhiteMagic does keep local diagnostic evidence on-device (e.g., RSI friction records). Optional model/embedding backends degrade truthfully when absent.

## Install and verify

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=gen3-skill | sh
wm --version         # expect: wm 10.2.0-alpha.6 (Gen3 line)
wm grimoire          # guided first-run: environment check + client wiring preview
                     #   --json for a machine-readable report; --write to write client configs
wm selftest --json   # install invariant (throwaway store) + host_status/host_health
wm selftest --strict # exit 1 only when the host verdict is critical
wm ingest --file notes.jsonl --default-source notes:stream   # JSONL stream ('-' = stdin)
# folder/document harvesting is the MCP `memory.ingest` tool (dry-run-first, redacts by default)
```

The v9-only commands (`doctor`, `connect`, `setup`, `quickstart`, `backup`,
`restore`, `update`, `seal`, `verify`, `trust`, `anchor`) belong to the `wm9`
binary line, not Gen3 `wm`; `wm grimoire --write` covers client wiring here.
Building from source instead: `cargo build --release` in this repository, then install `target/release/wm` onto your `PATH`.

## Wire your MCP client

Claude Desktop, Cursor, Codex, Gemini CLI, opencode — any MCP client:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "wm",
      "args": ["serve", "--profile", "cyberbrain"]
    }
  }
}
```

`cyberbrain` is the default profile (12 lean tools); `--profile full` exposes
the 40-route curated catalog plus any feature-gated routes the build registered
(`wm contract --json` reports the exact set). Explicit routes are the dependable
surface.

## First useful actions

1. **Record something worth keeping** — a decision, not raw transcript:
   the memory layer is for distilled context.
2. **Search before re-deriving** — lexical search works with no
   external model; embedders improve ranking when available.
3. **Checkpoint at the end of real work** — sessions support record,
   replay, and cross-session continuity, so the next session resumes
   from evidence instead of re-reading everything.
4. **Load your documents when you have them** — the MCP `memory.ingest` tool
   harvests a folder or batch dry-run-first (`source`, `dry_run`, `redact`),
   scrubs credential-shaped content by default, and nothing leaves the machine.
   The CLI `wm ingest` streams JSONL (`--file`).

## Vocabulary (explicit routes are the contract)

| You mean | Route |
|---|---|
| begin / resume a work session | `session.start` |
| remember / record this | `memory.create` |
| find X / what do you remember about X | `memory.search` |
| what did we decide about X | `memory.search` |
| resume where we left off | `session.continuity` |
| correct an earlier belief | `memory.update` (supersede; pass `galaxy` for non-default galaxies) |
| discover the surface | MCP `tools/list` (or `wm contract --json` on the CLI) |
| finish the session | `session.record` summary + `session.checkpoint` |

`session.record` and `session.checkpoint` require an active session — call
`session.start` first (errors say so explicitly if you forget). Natural-language
phrasing is a convenience layer; explicit `route=` dispatch is the dependable
path for anything that matters.

## Operating notes

- Trusted, local, single-user operation; Linux Landlock containment
  and firebreak guards are part of the contract.
- Back up the store directory (copy it while no server runs) before risky
  operations, and verify with `wm selftest`; `wm backup`/`wm restore` are
  wm9-line commands, not Gen3.
- The web surface (https://whitemagic.dev) is a discovery surface,
  not a host: it never holds your memories.
- Security posture and reporting: [SECURITY.md](SECURITY.md).
- Privacy: [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## Where to read more

- [README.md](README.md) — product overview and supported contract.
- [CHANGELOG.md](CHANGELOG.md) — release history.
- [docs/INDEX.md](docs/INDEX.md) — map of the documentation tree.
- Machine-readable identity: https://whitemagic.dev/ai-agent.json
