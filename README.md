# WhiteMagic

Local-first memory and session continuity for coding agents.

WhiteMagic gives an AI coding agent durable project memory over MCP: record
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

## Status

**WhiteMagic v9.** General release for AI coding agents.

- **Supported platforms: Linux x86-64, macOS, Windows.**
- The Linux x86-64 artifact is fully static — no glibc or distribution requirements.
- Trusted, local-first, single-user operation with Landlock containment and firebreak guards.

## What it does

The supported alpha contract:

- trusted, local, single-user operation;
- explicit MCP routes for dependable behavior;
- durable memory creation and lexical search without an external model;
- session record, replay, and cross-session continuity;
- a complete backup, verification, and restore path;
- no telemetry and no required WhiteMagic cloud service;
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
curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
```

Verify the installation:

```bash
wm --version   # wm 9.1.2
wm doctor      # environment health check
```

## Connect an MCP client

Point any MCP client at:

```bash
wm serve --profile curated
```

The server communicates over stdio and exposes a single `wm` meta-tool.
Explicit routing is the dependable contract:

- `wm(route="memory.create", args={...})`
- `wm(route="session.start", args={...})`
- `wm(route="tools.list", args={})`

`--profile curated` selects the supported memory/session surface and is the
default when no profile is specified. Pass `--profile full` for the research
archive surface (see below).

## Privacy and data

- Your store lives locally at `~/.local/share/whitemagic`. Nothing is sent to
  WhiteMagic-operated services; there is no telemetry.
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
a signed multi-agent mesh, holographic memory coordinates, and a 237-tool
archive reachable via `wm serve` without a profile restriction. These are
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
- [`docs/MCP_CONFIG_GUIDE.md`](docs/MCP_CONFIG_GUIDE.md) — client configuration
- [`docs/MULTI_LAPTOP.md`](docs/MULTI_LAPTOP.md) — moving between machines (backup/restore, session carry)
- [`CHANGELOG.md`](CHANGELOG.md) — release notes
- [`SECURITY.md`](SECURITY.md) — reporting vulnerabilities

## Migrating from v26 (legacy Python)

If you ran the retired Python version:

```bash
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies --dry-run   # preview
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies              # migrate
```

## License

[MIT](LICENSE) © Lucas Bailey and WhiteMagic Contributors

## Support and security

- Support: open an issue at
  <https://github.com/lbailey94/whitemagic/issues>
- Security: email <lbailey94@protonmail.com> (please do not open public
  issues for security reports)
