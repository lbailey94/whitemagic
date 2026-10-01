# WhiteMagic

[![whitemagic.agent](https://dmv.agentcommunity.org/badge?id=UNIT-FA2-46DL)](https://dmv.agentcommunity.org/c/UNIT-FA2-46DL/whitemagic)

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

## Hosted services (separate from the local package)

- **Remote MCP** — `https://mcp.whitemagic.dev/mcp` (streamable-http):
  read-only recall over a curated public corpus; keyless discovery; evaluation
  keys with a published 50 recalls/day allowance; OAuth 2.1; x402 session lease
  options published as $0.01 for 5 minutes or $0.50 for 24 hours, with a
  published 10,000 RPM limit; and `memory.search_batch` for up to 10 queries in
  one MCP call. These limits and options are described by the [live server
  card](https://mcp.whitemagic.dev/.well-known/mcp/server-card.json); the batch
  tool is also present in the live `tools/list` response. Your local store is
  not uploaded to this read-only recall lane.
- **Receipt verification and agent trust API** — `https://api.whitemagic.dev`:
  stateless `POST /verify` for continuity-receipt bundles (`/health` and `/info`
  keyless), plus a published `/erc8004/validate` adapter targeting Base. See the
  API's [live service metadata](https://api.whitemagic.dev/info) and [endpoint
  documentation](https://api.whitemagic.dev/docs) for the advertised contract.
- **Memory Crystal client and API** — [`scripts/crystal_client.py`](scripts/crystal_client.py)
  seals and opens crystal envelopes locally with AES-256-GCM or
  ChaCha20-Poly1305 (install the optional dependency with
  `python3 -m pip install cryptography`). The [API documentation](https://api.whitemagic.dev/docs)
  lists crystal store, fetch, and lineage endpoints; successful hosted
  persistence and retrieval are not implied by local encryption support.

  The helper is distributed as source in this repository; it is not bundled
  into the `wm` binary or platform installers. Use the helper from the source
  revision matching the server/API you intend to use. Generate a client key
  into a protected file with
  `python3 scripts/crystal_client.py genkey --out crystal.key`, then pass that
  file to `seal` and `unseal` with `--key`.
  `seal` obtains the owner locator from the authenticated
  `/crystals/owner-locator` endpoint. This requires an owner credential and an
  existing registry mapping; a payment or session pass does not establish
  ownership. If an existing crystal is unmapped, use the [contact page](https://www.whitemagic.dev/contact)
  to request a manual ownership review.

  Supply the bearer credential through the `WM_CRYSTAL_TOKEN` environment
  variable or `--token-file /path/to/credential`. Token files must be regular,
  non-symlink files with mode `0600` or stricter. Do not put credentials in
  command-line arguments or send plaintext or encryption keys to support.
  `seal`, `push`, `pull`, and `lineage` require authenticated owner access;
  `seal`, `pull`, and `lineage` no longer accept `--tenant`; keyless pulls and
  lineage queries are no longer supported. The former tenant-hash CLI flow is
  a breaking change.

## Status

**WhiteMagic v9.** Release channel: **open alpha** — public alpha for MCP
agents. The version number is a compatibility signal; the channel is
an evidence claim (beta and stable each require their own exit conditions,
not a version milestone).

- **Install path: Linux x86-64, Linux arm64, and macOS arm64** — install-gated. Linux ships fully static (musl) builds with no glibc or distribution requirements, selected automatically by the installer; dynamically linked builds remain available for glibc 2.39+ hosts, and releases also publish gzipped distributables (~58% smaller) that the installer prefers on slow links. macOS arm64 installs through the same checksum-verified installer (hardware smoke evidence in [issue #2](https://github.com/lbailey94/whitemagic/issues/2)). macOS x86_64 and Windows x86_64 binaries are published in every release but their install paths are not gated yet.
- **Support window:** the current minor and the previous minor on the install-gated lines (Linux x86-64, Linux arm64, macOS arm64) receive fixes; older minors are archival. macOS x86_64 and Windows remain published but unsupported — see [`SECURITY.md`](SECURITY.md).
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
[latest release](https://github.com/lbailey94/whitemagic/releases), then
(substituting your platform's artifact name — for example
`wm-linux-x86_64-musl`, `wm-linux-aarch64-musl`, or `wm-macos-aarch64`; the
`.gz` variants decompress with `gunzip -c <file>.gz > <file>`):

```bash
sha256sum -c wm-linux-x86_64-musl.sha256
chmod +x wm-linux-x86_64-musl
mkdir -p ~/.local/bin && mv wm-linux-x86_64-musl ~/.local/bin/wm
```

If `~/.local/bin` is not on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Or use the install script (resolves the latest release, picks the right
artifact for your platform, and verifies the checksum automatically):

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

Verify the installation, activate it, and see the product work end to end:

```bash
wm --version    # wm 9.3.1
wm grimoire     # guided first-run: host, memory layer, agent wiring, vocabulary, continuity
wm connect      # dry run: list detected MCP clients and the exact change
wm connect --write  # apply, with timestamped backups
```

`wm grimoire` proves the environment and previews client wiring; it ends by
telling you activation itself needs `wm connect --write`. `wm quickstart` is
the optional 30-second two-process continuity demo on an isolated store, and
`wm doctor` is a troubleshooting tool, not a setup step — run
`wm doctor --deep` when something looks wrong.

## Everyday commands

```bash
wm status         # is WhiteMagic ready? (store, counts, index, last backup)
wm selftest       # ~1-second end-to-end invariant check (throwaway store)
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
discrete lifecycle catalog — 30 MCP tools in the curated profile: the 14
CRUD/lifecycle aliases (`memory.create/search/read/list/hybrid_recall/update/
revisions/ingest`, `session.start/record/checkpoint/continuity`,
`receipts.emit/verify`) and 15 read-only handles
(`memory.count/stats/tags/aggregate/associations/batch_read/query/filter/
nearby/vector.search`, `session.list/recall/replay`,
`gnosis.status/explain`). Read-only servers (`--readonly`) advertise the 23
read-only entries only — write routes are refused there anyway. The `wm`
meta-tool provides explicit access to the full curated route catalog (70
routes) without expanding the client's schema.
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
- Support the lab (voluntary, not a service payment): XRPL tip jar
  `raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPyXRP` — see
  <https://www.whitemagic.dev/support>. Services are paid via x402 or
  evaluation keys; the tip jar unlocks nothing.
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security: email <lbailey94@protonmail.com> (please do not open public
  issues for security reports)
