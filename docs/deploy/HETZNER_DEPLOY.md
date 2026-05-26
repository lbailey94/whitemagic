# Hetzner VPS Deployment Guide — WhiteMagic v22.2.0

**Last Updated**: 2026-05-26
**Target**: Hetzner Cloud CX21 (2 vCPU, 4GB RAM, 40GB SSD)

---

## 1. Server Setup

```bash
# SSH into VPS
ssh root@<hetzner-ip>

# Create deployment user
adduser whitemagic
usermod -aG sudo whitemagic

# Switch to whitemagic user
su - whitemagic
```

## 2. Install Dependencies

```bash
# System packages
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    nodejs npm \
    caddy \
    git \
    build-essential \
    libffi-dev \
    libgmp-dev

# GHC (for Haskell FFI)
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh
source ~/.ghcup/env
ghcup install ghc 9.6.6
ghcup set ghc 9.6.6
```

## 3. Clone Repository

```bash
# Clone from private repo
git clone git@github.com:<user>/whitemagic-private.git ~/WHITEMAGIC
cd ~/WHITEMAGIC

# Create venv
cd core
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# Install frontend deps
cd ../apps/site
npm install
npm run build
```

## 4. Build Haskell FFI (if needed)

```bash
cd ~/WHITEMAGIC/polyglot/whitemagic-hs
cabal build
# libwhitemagic_hs.so will be in dist-newstyle/
```

## 5. Deploy Services

```bash
# Copy systemd services
sudo cp ~/WHITEMAGIC/deploy/whitemagic-api.service /etc/systemd/system/
sudo cp ~/WHITEMAGIC/deploy/whitemagic-dashboard.service /etc/systemd/system/

# Edit paths in services if different from default
sudo nano /etc/systemd/system/whitemagic-api.service

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable whitemagic-api
sudo systemctl enable whitemagic-dashboard
sudo systemctl start whitemagic-api
sudo systemctl start whitemagic-dashboard

# Check status
sudo systemctl status whitemagic-api
sudo systemctl status whitemagic-dashboard
```

## 6. Deploy Caddy

```bash
# Copy Caddyfile
sudo cp ~/WHITEMAGIC/deploy/Caddyfile /etc/caddy/Caddyfile

# Restart Caddy
sudo systemctl restart caddy

# Check status
sudo systemctl status caddy
```

## 7. DNS Configuration

```
A record:  whitemagic.dev     → <hetzner-ip>
A record:  api.whitemagic.dev → <hetzner-ip>
```

## 8. Verify Deployment

```bash
# Check API
curl https://api.whitemagic.dev/health

# Check PWA
curl -I https://whitemagic.dev

# Check SSE stream
curl -N https://api.whitemagic.dev/events/stream &
```

## 9. Environment Variables

Create `/home/whitemagic/.env`:

```bash
# WhiteMagic Core
WM_STATE_ROOT=/home/whitemagic/.whitemagic
WM_SILENT_INIT=1

# Haskell FFI
LD_LIBRARY_PATH=/home/whitemagic/.ghcup/ghc/9.6.6/lib/ghc-9.6.6/lib/x86_64-linux-ghc-9.6.6
LD_PRELOAD=/home/whitemagic/.ghcup/ghc/9.6.6/lib/ghc-9.6.6/lib/x86_64-linux-ghc-9.6.6/libHSrts_thr-ghc9.6.6.so

# Polyglot paths
WM_POLYGLOT_HS=/home/whitemagic/WHITEMAGIC/polyglot/whitemagic-hs
WM_POLYGLOT_ZIG=/home/whitemagic/WHITEMAGIC/polyglot/whitemagic-zig/zig-out/lib

# Optional: OpenRouter API key (for Librarian)
# OPENROUTER_API_KEY=sk-or-...
```

## 10. Monitoring

```bash
# View logs
journalctl -u whitemagic-api -f
journalctl -u whitemagic-dashboard -f
sudo journalctl -u caddy -f

# Check Caddy logs
sudo tail -f /var/log/caddy/whitemagic-access.log
sudo tail -f /var/log/caddy/whitemagic-api-access.log
```

---

## Architecture

```
Internet
    │
    ▼
┌─────────────────┐
│     Caddy       │  (TLS, headers, compression)
│   port 443/80   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│ PWA    │ │ REST API │
│ :3002  │ │  :8770   │
│ Next.js│ │ FastAPI  │
└────────┘ └────┬─────┘
                │
         ┌──────┴──────┐
         │             │
         ▼             ▼
    ┌─────────┐  ┌───────────┐
    │ SQLite  │  │ Polyglot  │
    │ Pool    │  │ (Rust/Zig │
    │ (10 cxn)│  │  Haskell) │
    └─────────┘  └───────────┘
```

## Key Notes

1. **Haskell FFI requires `LD_PRELOAD`** of the GHC RTS library. Without it, the Haskell shared library will fail to load with "undefined symbol" errors.

2. **SQLite connection pool** uses 10 persistent connections with WAL mode, 256MB mmap, and 64MB page cache. This is 2.1x faster than open/close per query.

3. **SSE event stream** uses `asyncio.Event` for instant push (no polling). Clients receive events within ~10ms of emission.

4. **WASM module** (178KB) is served from `/wasm/` and runs entirely in the browser for the PWA `/app` route.

5. **Security**: Both services run as `whitemagic` user with `NoNewPrivileges=true` and restricted filesystem access.
