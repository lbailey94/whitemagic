# WhiteMagic Quickstart

**Languages:** **English** · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md)

**Version**: 9.2.8
**Install path**: Linux x86-64 and Linux arm64 (aarch64) — install-gated,
fully static (musl) builds selected automatically by the installer (a
dynamically linked build remains for glibc 2.39+ hosts); releases also
publish gzipped distributables for slow links. macOS and Windows binaries
ship in every release but their install paths are not gated yet.

Get from zero to working agent memory in under five minutes.

## 30-second path

```bash
wm grimoire     # guided first-run: host, memory layer, agents, memory, vocabulary, continuity
wm quickstart   # two-process continuity demo on an isolated store
wm selftest     # end-to-end invariant check (throwaway store, ~1 second)
```

You will see a project decision recorded in one session survive a full
process stop/start and be recovered by the next session. That is the product.

## 1. Install (no admin rights needed)

### From a release

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

This downloads the latest release, verifies its SHA256 checksum, and installs
`wm` to `~/.local/bin`. If that directory is not on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Manual equivalent: download your platform's binary (the static
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl` builds, or the glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64` builds, each with its `.gz` variant)
and its `.sha256` file from the
[releases page](https://github.com/lbailey94/whitemagic/releases), then:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

The dynamically linked builds require glibc 2.39+ (built on Ubuntu 24.04);
the static musl builds have no glibc requirement.

### From source

Requires Rust 1.85+. No admin rights required:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Verify

```bash
wm --version   # wm 9.2.8
wm doctor      # store, index, registry health check
```

## 3. Run the demo

```bash
wm quickstart
```

The demo uses an isolated store at `~/.local/share/whitemagic-quickstart`
(your real data is never touched). It shows: session start → record a
decision → process stop → new process → continuity recovers the decision →
budgeted replay. Remove it any time with
`rm -rf ~/.local/share/whitemagic-quickstart`.

## 4. Connect your MCP client

```bash
wm connect           # dry run: list detected clients and the exact change
wm connect --write   # patch every detected client (timestamped backups first)
```

Or configure one client explicitly with `wm setup <client> [--write]`. The
equivalent manual config:

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

The server speaks JSON-RPC over stdio and exposes one `wm` meta-tool.
Explicit routing is the dependable contract:

- `wm(route="session.continuity")` — recall the previous session before starting work
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — discover everything else

See [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) for client-specific setup.

## 5. Back up

```bash
wm backup          # full store -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Keep backups off the live machine. See the README for details.
