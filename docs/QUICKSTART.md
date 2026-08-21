# WhiteMagic Quickstart

**Version**: 7.0.0-alpha.1
**Supported platform**: Linux x86-64

Get from zero to working agent memory in under five minutes.

## 30-second path

```bash
wm quickstart   # two-process continuity demo on an isolated store
```

You will see a project decision recorded in one session survive a full
process stop/start and be recovered by the next session. That is the product.

## 1. Install (no admin rights needed)

### From a release

```bash
curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
```

This downloads the latest release, verifies its SHA256 checksum, and installs
`wm` to `~/.local/bin`. If that directory is not on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Manual equivalent: download `wm-linux-x86_64` and `wm-linux-x86_64.sha256`
from the [releases page](https://github.com/lbailey94/whitemagic/releases),
then:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

The binary requires glibc 2.39+ (built on Ubuntu 24.04).

### From source

Requires Rust 1.85+. No admin rights required:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Verify

```bash
wm --version   # wm 7.0.0-alpha.1
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
