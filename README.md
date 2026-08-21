# WhiteMagic

Local-first memory and session continuity for coding agents.

WhiteMagic gives an AI coding agent durable project memory over MCP: record
important context, find it after restart, and carry useful decisions into the
next session — without sending your memory store to any hosted service.

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

**v7.0.0-alpha.1 — private alpha.** Under active development and private
testing. The website [whitemagic.dev](https://whitemagic.dev) is in a
work-in-progress state; there is no public launch date.

- **Supported platform: Linux x86-64 only.** Other platforms have not passed
  an install gate and are not advertised.
- The binary is dynamically linked and was built on Ubuntu 24.04
  (glibc 2.39). Distributions with older glibc are not verified; a static
  build is planned.
- The release is marked *pre-release* on GitHub accordingly.

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
wm --version   # wm 7.0.0-alpha.1
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

`--profile curated` selects the supported memory/session surface. Without it,
the server starts with the full research tool archive (see below).

## Privacy and data

- Your store lives locally at `~/.local/share/whitemagic`. Nothing is sent to
  WhiteMagic-operated services; there is no telemetry.
- Privacy flags exclude memories from responses and reasoning. **They are
  access controls, not encryption** — anyone who can read the store files can
  read the contents. Do not store credentials in memories.
- Conversation capture happens through explicit tool calls, not automatically.
- Back up the whole store directory, not just the `lmdb/` subdirectory.

## Research surface (not part of the alpha contract)

The codebase contains a larger research system beyond the product boundary:
autonomous cycles, dream consolidation, bicameral reasoning, an imagination
engine, self-play training loops, polyglot sidecars (Julia/Haskell/Zig/Koka),
a signed multi-agent mesh, holographic memory coordinates, and a 237-tool
archive reachable via `wm serve` without a profile restriction. These are
research surfaces without product acceptance evidence; they may change or be
removed. See [`docs/V7_PRODUCT_READINESS.md`](docs/V7_PRODUCT_READINESS.md)
for how surfaces get promoted into the product contract.

## Building from source

Requires Rust 1.85+:

```bash
cargo build --release
cargo test          # full test suite
cargo clippy --all-targets
```

## Documentation

- [`docs/V7_PRODUCT_READINESS.md`](docs/V7_PRODUCT_READINESS.md) — product gates and evidence ledger (source of truth)
- [`docs/NEXT_SESSION.md`](docs/NEXT_SESSION.md) — current execution slice
- [`docs/MCP_CONFIG_GUIDE.md`](docs/MCP_CONFIG_GUIDE.md) — client configuration
- [`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md) — historical v5.8.0 release record
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — implementation history

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
