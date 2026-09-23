# WhiteMagic

A local-first memory layer for MCP agents.

WhiteMagic gives an AI agent durable project memory over MCP: record
important context, find it after restart, and carry useful decisions into the
next session — without sending your memory store to any hosted service.

**You are an agent reading this repo?** Start with
[skill.md](skill.md) (five-minute operational onboarding) and
[llms.txt](llms.txt) (machine-readable index).

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

## Hosted lanes (read-only beta)

- **Remote MCP** — `https://mcp.whitemagic.dev/mcp` (streamable-http):
  read-only recall over a curated public corpus, keyless discovery, free
  evaluation keys, no SLA. Your local store is never uploaded.
- **Receipt verification API** — `https://api.whitemagic.dev`: stateless
  `POST /verify` for continuity-receipt bundles (`/health` and `/info`
  keyless).

## Status

**WhiteMagic v9.** Release channel: **open alpha** — public alpha for MCP
agents. The version number is a compatibility signal; the channel is
an evidence claim (beta and stable each require their own exit conditions,
not a version milestone).

- **Install path: Linux x86-64 and arm64** — fully static (musl) builds with no glibc or distribution requirements, selected automatically by the installer; dynamically linked builds remain available for glibc 2.39+ hosts, and releases also publish gzipped distributables (~58% smaller) that the installer prefers on slow links. macOS and Windows binaries are published in every release but are not yet install-gated.
- **Support window:** the current minor and the previous minor on the install-gated Linux line (x86-64 and arm64) receive fixes; older minors are archival. macOS and Windows remain published but unsupported — see [`SECURITY.md`](SECURITY.md).
- Trusted, local-first, single-user operation with Landlock containment and firebreak guards.

## What it does

The supported alpha contract:

- trusted, local, single-user operation;
- explicit MCP routes for dependable behavior;
- durable memory creation and lexical search without an external model;
- session record, replay, and cross-session continuity;
- a complete backup, verification, and restore path;
- no telemetry by default and no required WhiteMagic cloud service;
- truthful degradation when optional models or embeddings are unavailable.

## Install

Download the binary and its checksum from the
[latest release](https://github.com/lbailey94/whitemagic/releases), then:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm
mkdir -p ~/.local/bin && mv wm ~/.local/bin/
```

If `~/.local/bin` is not on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Or use the install script (resolves the latest release and verifies the
checksum automatically):

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=readme | sh
```

### Other channels

```bash
npx whitemagic-mcp serve                     # npm (no global install)
cargo install whitemagic                     # crates.io
docker run -i lbailey94/whitemagic:9 serve   # Docker Hub
```

Adoption snapshot (2026-09-13): 759 npm downloads/30d · 1,846 Docker pulls ·
67 crates.io downloads. Package installs are independent of the installer and
grew without any website CTA — the memory layer chooses its own doors.

Verify the installation and see the product work end to end:

```bash
wm --version    # wm 9.2.7
wm quickstart   # 30-second two-process continuity demo (isolated store)
wm grimoire     # guided first-run: host, memory layer, agent wiring, vocabulary, continuity
```

`wm doctor` is a troubleshooting tool, not a setup step — run
`wm doctor --deep` when something looks wrong.

## Everyday commands

```bash
wm status         # is WhiteMagic ready? (store, counts, index, last backup)
wm selftest       # 5-second end-to-end invariant check (throwaway store)
wm connect        # wire every detected MCP client (dry run first; add --write)
wm setup          # list clients / per-client setup (wm setup <client> --write)
wm update check   # is a newer signed release available? (notify-only)
```

## Connect an MCP client

Point any MCP client at:

```bash
wm serve --profile curated
```

The server communicates over stdio and exposes the `wm` meta-tool plus a
discrete lifecycle catalog — 9 MCP tools in the curated profile
(`memory.create/search/read/list/hybrid_recall`,
`session.start/record/continuity`). Those nine are the client-visible tool
schemas; the `wm` meta-tool provides explicit access to a larger curated
route catalog (61 routes: update, delete, digest, export/import, claims,
transactions, …) without expanding the client's schema.
Direct handles for the common lifecycle calls, with NLU routing still available.
Explicit routing is the dependable contract:

- `wm(route="memory.create", args={...})`
- `wm(route="session.start", args={...})`
- `wm(route="tools.list", args={})`

`--profile curated` selects the supported memory/session surface and is the
default when no profile is specified. Pass `--profile full` for the research
archive surface (see below).

## Privacy and data

- Your store lives locally at `~/.local/share/whitemagic`. Nothing is sent to
  WhiteMagic-operated services; there is no telemetry by default (any future
  sharing is opt-in, previewable, and schema-bound).
- Privacy flags exclude memories from responses and reasoning. **They are
  access controls, not encryption** — anyone who can read the store files can
  read the contents. Do not store credentials in memories.
- Conversation capture happens through explicit tool calls, not automatically.

## Backup and restore

Back up the **whole store root** (LMDB database, search indexes, and all
session/state files — not just the `lmdb/` subdirectory):

```bash
# Stop the server first, then:
wm backup                                  # writes ~/whitemagic-backups/<timestamp>/
wm backup --out /path/to/external/disk     # keep copies OFF the live machine
```

Each backup contains the full store plus a `SHA256SUMS` manifest. Restore
after a failure (this replaces the target store):

```bash
wm restore --backup ~/whitemagic-backups/whitemagic-backup-<timestamp> --force
wm doctor                                  # confirm health after restore
```

Restore verifies every file against the manifest before touching anything,
and refuses tampered or incomplete backups. Notes:

- `wm seal` / `wm verify` detect *integrity drift*; they do not recover data.
  Only a backup recovers data.
- Transaction rollback (`transaction.rollback`) is an in-store, short-lived
  undo — not a substitute for backups.
- Keep at least one backup on a different disk or machine.

## Research surface (not part of the alpha contract)

The codebase contains a larger research system beyond the product boundary:
autonomous cycles, dream consolidation, bicameral reasoning, an imagination
engine, self-play training loops, polyglot sidecars (Julia/Haskell/Zig/Koka),
a signed multi-agent mesh, holographic memory coordinates, and the full
research archive (~300 routes; the generated
`docs/contract/route-schema-manifest.json` is the authority) reachable via
`wm serve` without a profile restriction. These are
research surfaces without product acceptance evidence; they may change or be
removed. Only surfaces documented in this README are part of the product
contract.

## Building from source

Requires Rust 1.85+:

```bash
cargo build --release
cargo test          # full test suite
cargo clippy --all-targets
```

## Documentation

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — the two-process continuity demo
- [`docs/QUICKSTART.es.md`](docs/QUICKSTART.es.md) — guía rápida (Español)
- [`docs/QUICKSTART.pt-BR.md`](docs/QUICKSTART.pt-BR.md) — guia rápido (Português BR)
- [`docs/QUICKSTART.fr.md`](docs/QUICKSTART.fr.md) — guide de démarrage (Français)
- [`docs/TRANSLATIONS.md`](docs/TRANSLATIONS.md) — translation index and help-wanted languages
- [`docs/MCP_CONFIG_GUIDE.md`](docs/MCP_CONFIG_GUIDE.md) — client configuration
- [`docs/MULTI_LAPTOP.md`](docs/MULTI_LAPTOP.md) — moving between machines (backup/restore, session carry)
- [`continuity-receipt`](https://github.com/lbailey94/continuity-receipt) — signed, offline-verifiable records of governed tasks (separate spec repo, Apache-2.0)
- [`CHANGELOG.md`](CHANGELOG.md) — release notes
- [`SECURITY.md`](SECURITY.md) — reporting vulnerabilities

## Migrating from v26 (legacy Python)

If you ran the retired Python version:

```bash
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies --dry-run   # preview
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies              # migrate
```

## The stack

> Local memory → governed execution → verifiable continuity

- [`whitemagic`](https://github.com/lbailey94/whitemagic) — local-first memory and session continuity for AI agents
- [`continuity-receipt`](https://github.com/lbailey94/continuity-receipt) — portable, offline-verifiable evidence for governed tasks (Apache-2.0)
- [`mandalaos-gate-lite`](https://github.com/lbailey94/mandalaos-gate-lite) — bounded agent execution that emits receipts (review snapshot)
- [`whitemagic-plugins`](https://github.com/lbailey94/whitemagic-plugins) — client integrations and adapters

Each repository stands on its own: WhiteMagic does not require MandalaOS, and
Continuity Receipt does not require WhiteMagic. Three entrances — **use it** →
`whitemagic`; **review a protocol** → `continuity-receipt`; **attack the
security architecture** → `mandalaos-gate-lite`.

## License

[MIT](LICENSE) © Lucas Bailey and WhiteMagic Contributors

## Support and security

- Support: open an issue at
  <https://github.com/lbailey94/whitemagic/issues>
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security: email <lbailey94@protonmail.com> (please do not open public
  issues for security reports)
