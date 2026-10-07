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
      "args": ["serve", "--profile", "cyberbrain"]
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

**WhiteMagic Gen3** (the `wm` 10.2 alpha line). Release channel: **open
alpha** — public alpha for MCP agents. The version number is a compatibility
signal; the channel is an evidence claim (beta and stable each require their
own exit conditions, not a version milestone).

- **Install path: Linux x86-64, Linux arm64, macOS arm64, and Windows x86_64** — install-gated. Linux builds are dynamically linked (glibc 2.39+): the ONNX runtime the v10 line loads has no static musl build (pre-v10 releases still ship musl). Releases also publish gzipped distributables (~58% smaller) that the installer prefers on slow links. macOS installs through the same checksum-verified installer (hardware smoke evidence in [issue #2](https://github.com/lbailey94/whitemagic/issues/2)); Windows installs through `scripts/install.ps1`. Every gated installer path is certified against the published release in CI.
- **Support window:** the current minor and the previous minor on the install-gated lines (Linux x86-64, Linux arm64, macOS arm64, Windows x86_64) receive fixes; older minors are archival — see [`SECURITY.md`](SECURITY.md).
- Trusted, local-first, single-user operation with Landlock containment and firebreak guards.

## What it does

The supported alpha contract:

- trusted, local, single-user operation;
- explicit MCP routes for dependable behavior;
- durable memory creation and lexical search without an external model;
- session record, replay, and cross-session continuity;
- an end-to-end install invariant (`wm selftest`) with host-health diagnostics;
- no telemetry by default and no required WhiteMagic cloud service;
- truthful degradation when optional models or embeddings are unavailable.

## Install

Download the binary and its checksum from the
[latest release](https://github.com/lbailey94/whitemagic/releases), then
(substituting your platform's artifact name — for example
`wm-linux-x86_64`, `wm-linux-aarch64`, or `wm-macos-aarch64`; the
`.gz` variants decompress with `gunzip -c <file>.gz > <file>`):

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
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

Verify the installation and see the product work end to end:

```bash
wm --version    # wm 10.2.0-alpha.4
wm status       # display substrate status, epoch, record counts, and store health
```

`wm grimoire` proves the environment and previews client wiring; add `--write`
to write detected MCP client configurations (`--json` for a machine-readable
report). `wm selftest` runs the full invariant check (a throwaway store plus
host health); see [`docs/SELFTEST_AND_HOST_HEALTH.md`](docs/SELFTEST_AND_HOST_HEALTH.md).

## Everyday commands

```bash
wm status                       # store, epoch, record counts, store health
wm selftest                     # install invariant + host health (--json, --strict)
wm remember "decision text"     # record a memory (--galaxy, --source, --kind)
wm recall "query"               # search memories (--limit, --historical, --scope)
wm session list                 # sessions: checkpoint | record | continuity | list
wm serve                        # MCP stdio server (--profile cyberbrain is the default)
```

The v9-only commands (`doctor`, `connect`, `setup`, `quickstart`, `backup`,
`restore`, `update`, `seal`, `verify`, `trust`, `anchor`) belong to the `wm9`
binary line, not the Gen3 `wm` documented here.

## Connect an MCP client

Point any MCP client at:

```bash
wm serve                          # cyberbrain profile (default)
wm serve --profile full           # full curated catalog
```

The server communicates over stdio. Two profiles exist:

- **`cyberbrain` (default)** — 12 lean MCP tools: `memory_recall`,
  `memory_remember`, `memory_get`, `memory_stats`, the `wm` meta-tool
  (explicit `route=` dispatch to the catalog), `session_checkpoint`,
  `session_continuity`, `session_record`, `session_list`, `galaxy_list`,
  `galaxy_fork`, `mesh_sync`.
- **`full`** — 40 curated routes covering memory CRUD, search, sessions,
  receipts, galaxies, mandala, gnosis, sangha, and mesh; optional features add
  gated routes (`decision.shortlist`, `decision.deliberate`,
  `decision.outcome`, `systemone.decide`) when compiled in. A default build
  reports 43 routes via `wm contract --json` (the route count is whatever the
  running binary registered — that manifest is the authority).

Explicit routing is the dependable contract:

- `wm(route="memory.create", args={...})`
- `wm(route="session.start", args={...})`
- `wm(route="galaxy.list", args={})`

## Privacy and data

- Your store lives locally at `~/.local/share/whitemagic/gen3` (override with
  `--store <path>` or `WM_STORE`). Nothing is sent to WhiteMagic-operated
  services; there is no telemetry by default (any future sharing is opt-in,
  previewable, and schema-bound).
- Privacy flags exclude memories from responses and reasoning. **They are
  access controls, not encryption** — anyone who can read the store files can
  read the contents. Do not store credentials in memories.
- Conversation capture happens through explicit tool calls, not automatically.

## Backup and restore

The Gen3 `wm` has no `backup`/`restore` subcommands (`wm backup`, `wm restore`,
`wm doctor`, `wm seal`, and `wm verify` are part of the v9 `wm9` line). Back up
the **whole store directory** while no server is running:

```bash
# Stop any `wm serve` first, then copy the store root:
cp -a ~/.local/share/whitemagic/gen3 /path/to/external/disk/gen3-$(date +%F)
```

- Keep at least one copy on a different disk or machine.
- After restoring a copy, verify it with `wm selftest` and inspect it with
  `wm status`.
- Transaction rollback (`mandala`/session internals) is a short-lived undo, not
  a substitute for backups.

## Research surface (not part of the alpha contract)

The codebase contains a larger research system beyond the product boundary:
autonomous cycles, dream consolidation, bicameral reasoning, an imagination
engine, self-play training loops, polyglot sidecars (Julia/Haskell/Zig/Koka),
a signed multi-agent mesh, holographic memory coordinates, and the rest of the
route catalog reachable via `wm serve --profile full` plus the optional
feature-gated routes. `wm contract --json` is the authority for the compiled
route set. These are research surfaces without product acceptance evidence;
they may change or be removed. Only surfaces documented in this README are part
of the product contract.

## Building from source

Requires Rust 1.85+:

```bash
cargo build --release
cargo test          # full test suite
cargo clippy --all-targets
```

## Documentation

- [`docs/INDEX.md`](docs/INDEX.md) — map of the documentation tree
- [`docs/SELFTEST_AND_HOST_HEALTH.md`](docs/SELFTEST_AND_HOST_HEALTH.md) — `wm selftest` checks, thresholds, and `--strict`/`--json` contracts
- [`INSTALL.md`](INSTALL.md) — source build, store setup, optional model layer
- [`skill.md`](skill.md) — five-minute agent onboarding
- [`llms.txt`](llms.txt) — machine-readable index
- [`docs/CHARTER.md`](docs/CHARTER.md) — binding constitutional core
- [`docs/NUCLEUS.md`](docs/NUCLEUS.md) — frozen nucleus snapshot
- [`continuity-receipt`](https://github.com/lbailey94/continuity-receipt) — signed, offline-verifiable records of governed tasks (separate spec repo, Apache-2.0)
- [`CHANGELOG.md`](CHANGELOG.md) — release notes
- [`SECURITY.md`](SECURITY.md) — reporting vulnerabilities

## Migrating from v26 / Gen2 (LMDB stores)

If you ran the retired Python version (v26) or an earlier Gen2 line, audit and
migrate its LMDB store (the directory containing `data.mdb`) into Gen3:

```bash
wm census ~/.whitemagic/users/local/galaxies/lmdb          # zero-dependency audit
wm migrate --source ~/.whitemagic/lmdb --dry-run           # preview
wm migrate --source ~/.whitemagic/lmdb                     # migrate into the Gen3 store
wm migrate-all --source-root <projects-root> --target-root ~/.local/share/whitemagic/gen3-projects
```

`wm quarantine <file>` reviews the migration quarantine log; a `WM_STORE`/`--store`
override selects the destination.

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
