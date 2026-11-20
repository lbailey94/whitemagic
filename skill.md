# WhiteMagic — agent skill

Operational quickstart for AI agents that cloned this repository. Goal: from clone to durable memory and session continuity in under five minutes, without reading the whole codebase.

## What this is

Local-first memory and session continuity for coding agents, exposed over MCP. A single Rust binary (`wm`) runs a stdio JSON-RPC server your MCP client talks to. Memory is stored on-device; no usage telemetry, prompts, or memories are transmitted off-device by default. WhiteMagic does keep local diagnostic evidence on-device (e.g., RSI friction records). Optional model/embedding backends degrade truthfully when absent.

## Install and verify

On Linux x86-64 or ARM64 with glibc 2.39 or newer, or Apple Silicon macOS:

```sh
curl -fsSL 'https://www.whitemagic.dev/install.sh?ref=gen3-skill' | sh -s -- --version v11.2.1 --dir "$HOME/.local/bin"
"$HOME/.local/bin/wm" --version
"$HOME/.local/bin/wm" grimoire --plan
```

Use the full path in the same shell. Grimoire previews what the client setup
would use. For Windows and Intel macOS, use the [Gen 2 fallback](https://www.whitemagic.dev/install#fallback)
and that release's client instructions.

To verify persistence before configuring a client, save a sample note and
recall it in a second process using a temporary store.

```sh
wm_demo_store=$(mktemp -d) &&
  "$HOME/.local/bin/wm" --store "$wm_demo_store" remember 'The demo project is Juniper.' &&
  "$HOME/.local/bin/wm" --store "$wm_demo_store" recall 'Juniper'
```

For these optional commands, add the install directory to this shell's PATH.

```sh
export PATH="$HOME/.local/bin:$PATH"
wm selftest --json   # install invariant (throwaway store) + host_status/host_health
wm selftest --strict # exit 1 only when the host verdict is critical
wm wiki --out ./wiki # export store into a Merkle-anchored Holographic Wiki (_index.md)
wm backup ./backup   # snapshot store + SHA256SUMS manifest (--json)
wm restore ./backup  # verify SHA256SUMS and restore store (--force, --json)
wm ingest --file notes.jsonl --default-source notes:stream   # JSONL stream ('-' = stdin)
# folder/document harvesting is the MCP `memory.ingest` tool (dry-run-first, redacts by default)
```

The v9-only commands (`doctor`, `connect`, `setup`, `quickstart`,
`update`, `seal`, `verify`, `trust`, `anchor`) belong to the `wm9`
binary line; `wm backup`, `wm restore`, `wm wiki`, and `wm verify-receipt` are natively supported in `wm 11.2.1`. Gen3 `grimoire --plan` reports client config targets
without writing them; add the `serve` command shown below to the client config.
Building from source instead: `cargo build --release` in this repository, then install `target/release/wm` onto your `PATH`.

## Wire your MCP client

Use the [client setup recipes](https://www.whitemagic.dev/install#clients)
for Claude Code, Cursor, Codex CLI, and OpenCode. For other clients, use the
format their settings require. The client launches `serve` itself.

For clients with an `mcpServers` configuration, substitute the installed
binary's absolute path and the absolute path to the Gen 3 store:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "/absolute/path/to/wm",
      "args": ["--store", "/absolute/path/to/whitemagic/gen3", "serve", "--profile", "cyberbrain"]
    }
  }
}
```

`cyberbrain` is the default lean MCP profile; `--profile full` exposes the
extended catalog plus any feature-gated routes the build registered. The
running server's `tools/list` and `wm contract --json` report their respective
surfaces. Explicit routes are the dependable surface.

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
- Back up the store directory using `wm backup <dest_dir> --json` (or copy it while no server runs) before risky
  operations, and verify with `wm selftest` and `wm status`.
- The web surface (https://www.whitemagic.dev) is a discovery surface,
  not a host: it never holds your memories.
- Security posture and reporting: [SECURITY.md](SECURITY.md).
- Privacy: [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## Where to read more

- [README.md](README.md) — product overview and supported contract.
- [CHANGELOG.md](CHANGELOG.md) — release history.
- [docs/INDEX.md](docs/INDEX.md) — map of the documentation tree.
- Machine-readable discovery: https://www.whitemagic.dev/.well-known/mcp/server-card.json · https://mcp.whitemagic.dev/.well-known/agent-card.json
