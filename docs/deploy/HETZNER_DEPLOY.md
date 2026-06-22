# Hetzner VPS Deployment Guide — WhiteMagic Agent-First Lab

**Last Updated**: 2026-06-15 (revised for post-hike pricing + multi-agent lab architecture)
**Target**: Hetzner Cloud CCX23 (4 dedicated vCPU, 16 GB RAM, 160 GB SSD)
**Companion to**: `AGENT_FIRST_LAB_STRATEGY.md` §1.3 (two-track deployment)

---

## What Changed Since the May 26 Version

1. **Pricing**: Hetzner raised CPX/CCX lines 113-176% on June 15, 2026. The previous target (CPX21, was €5.99/mo) is now ~€14-15/mo and no longer the value pick. **CCX23 is the new target** — slightly more expensive, but dedicated vCPU (no noisy neighbor), which matters for always-on multi-agent workloads.
2. **Scope expanded**: The original doc deployed the PWA dashboard + REST API. The lab architecture adds: Sangha (multi-agent coordination), MCP server, x402 gratitude endpoint, Discord bot, gratitude ledger, observatory data collection, Ollama (optional local inference).
3. **Hybrid deployment**: Per the strategy doc's two-track plan, this server hosts **lab.whitemagic.dev** (the showpiece) and the long-running services. **whitemagic.dev** (the public-facing site) deploys to Vercel Hobby separately.
4. **NixOS as recommended OS**: The strategy doc identifies NixOS as the differentiator ("rigorous, reproducible" — strong narrative fit, auditability, generation-based rollbacks). This guide includes a NixOS path; an Ubuntu LTS path is also documented for faster setup.

---

## 1. Server Provisioning

### 1.1 Recommended: Hetzner Cloud CCX23

| Spec | Value |
|---|---|
| vCPU | 4 dedicated (AMD EPYC) |
| RAM | 16 GB |
| Storage | 160 GB NVMe SSD |
| Bandwidth | 20 TB/mo included, then €1/TB |
| Locations | Falkenstein, Helsinki, Ashburn VA, Hillsboro OR |
| **Price (post-Jun 15)** | **~€30-40/mo** |

For comparison:
- **CX32** (4 shared vCPU / 8 GB / 80 GB): ~€7/mo — sufficient for API-only inference, no Ollama
- **CCX13** (2 dedicated / 8 GB): ~€15/mo — middle ground
- **CCX33** (8 dedicated / 32 GB / 240 GB): ~€60-80/mo — scale-up if you add 10+ agents

### 1.2 Provisioning Steps

```bash
# 1. Sign up at hetzner.com/cloud (account, payment method, 2FA)
# 2. Create a new server:
#    - Image: Ubuntu 24.04 LTS (or NixOS 24.05 from Hetzner's "OS" menu)
#    - Type: CCX23
#    - Location: pick closest to your target audience (US: Ashburn; EU: Falkenstein)
#    - Networking: IPv4 + IPv6
#    - SSH key: paste your public key
#    - Name: whitemagic-lab
# 3. Note the server IP (e.g., 188.40.100.50)
# 4. SSH in as root:
ssh root@<hetzner-ip>
```

### 1.3 Cloudflare DNS (Set Up Early)

Before you do anything else, set up the DNS in Cloudflare (free tier):

1. Add `whitemagic.dev` and `lab.whitemagic.dev` to Cloudflare
2. Point A records at the Hetzner IP
3. Set proxy mode to **Proxied** (orange cloud) for DDoS protection + edge caching
4. Set SSL/TLS to **Full (strict)** — Caddy will handle the actual cert
5. Create DNS records:
   - `whitemagic.dev` → Hetzner IP (or skip if whitemagic.dev is on Vercel — see hybrid)
   - `lab.whitemagic.dev` → Hetzner IP
   - `mcp.whitemagic.dev` → Hetzner IP
   - `pay.whitemagic.dev` → Hetzner IP
   - `*.whitemagic.dev` (wildcard) → Hetzner IP

---

## 2. Initial Server Setup

### 2.1 Ubuntu 24.04 LTS Path (Faster Setup)

```bash
# Update system
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades

# Enable automatic security updates
dpkg-reconfigure -plow unattended-upgrades

# Create non-root user
adduser whitemagic
usermod -aG sudo whitemagic
mkdir -p /home/whitemagic/.ssh
cp ~/.ssh/authorized_keys /home/whitemagic/.ssh/
chown -R whitemagic:whitemagic /home/whitemagic/.ssh

# Switch to new user
su - whitemagic

# Set up basic firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2.2 NixOS Path (Strategy-Recommended)

If you choose NixOS (the strategy doc's preferred option):

```bash
# In the Hetzner rescue mode or post-install, install NixOS
# Hetzner has NixOS images available, or use nixos-infect

# Option A: Use Hetzner's NixOS image (if available in your region)
# Option B: Use nixos-infect (https://github.com/elitak/nixos-infect)
curl https://raw.githubusercontent.com/elitak/nixos-infect/master/nixos-infect | sudo bash

# After reboot, /etc/nixos/configuration.nix is the source of truth
# Edit it to match the configuration in §11 of this guide
sudo nano /etc/nixos/configuration.nix
sudo nixos-rebuild switch

# Every deploy is: edit configuration.nix → commit → nixos-rebuild switch
# Every rollback is: nixos-rebuild switch --rollback
# The configuration is your public infrastructure-as-code artifact
```

The NixOS path adds 2-3 days of upfront work but generates a `configuration.nix` you can publish publicly as a sovereign-stack artifact. The strategy doc considers this a "narrative leverage" win.

### 2.3 Install Core Dependencies

```bash
# Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash
sudo apt install -y nodejs

# Python 3.12 + venv + build tools
sudo apt install -y python3.12 python3.12-venv python3.12-dev build-essential \
  libffi-dev libgmp-dev libssl-dev sqlite3

# Caddy (reverse proxy)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Git
sudo apt install -y git rsync curl jq

# Docker (for MCP server isolation, optional)
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker whitemagic
```

---

## 3. Architecture Overview

```
                          Internet
                              │
                              ▼
                  ┌──────────────────────┐
                  │   Cloudflare Free    │  DNS, DDoS, edge cache
                  │   (orange cloud)     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │       Caddy          │  TLS, headers, compression
                  │   port 443 / 80      │  (auto-cert via Let's Encrypt)
                  └──────────┬───────────┘
                             │
       ┌─────────────┬───────┴──────┬──────────────┐
       ▼             ▼              ▼              ▼
   ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │  PWA   │   │   MCP    │   │ x402 +   │   │ Sangha + │
   │:3002   │   │ :8770    │   │ Gratitude│   │ Discord  │
   │ Next.js│   │ FastAPI  │   │ :8780    │   │ :8790    │
   └────┬───┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │            │              │              │
        └────────────┴──────────────┴──────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   WhiteMagic Core    │  Python 3.12 + venv
                  │   wm_rest_server.py  │  479 callable tools
                  │                      │  28 Gana meta-tools
                  └──────────┬───────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌────────┐    ┌──────────┐   ┌──────────┐
         │SQLite  │    │ Polyglot │   │ Ollama   │  (optional)
         │(WAL,   │    │ Rust/Zig │   │:11434    │  local inference
         │256MB)  │    │/Haskell  │   │          │
         └────────┘    └──────────┘   └──────────┘
```

**Services running on this box:**

| Service | Port | Purpose | Long-running? |
|---|---|---|---|
| PWA Dashboard (Next.js) | 3002 | Lab dashboard for human operator | Yes |
| WhiteMagic REST API | 8770 | Tool substrate for agents | Yes |
| **MCP Server** | 8771 (stdio via Tailscale) or 8772 (HTTP) | Agent integration point | Yes |
| **x402 + Gratitude Endpoint** | 8780 | HTTP 402 payment handler, gratitude ledger writes | Yes |
| **Sangha Coordinator** | 8790 | Multi-agent coordination (chat + locks) | Yes |
| **Discord Bot** | n/a (outbound) | Human ↔ agent communication | Yes |
| **Ollama** (optional) | 11434 | Local LLM inference | Yes |
| **Observatory Cron** | n/a | Periodic data collection | Cron |

---

## 4. Clone and Setup WhiteMagic

```bash
# Clone your private repo
git clone <your-private-repo-url> ~/WHITEMAGIC
cd ~/WHITEMAGIC

# Set up Python virtual environment
cd core
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e '.[mcp,cli,api]'  # extras for MCP, CLI, API
cd ..

# Set up Next.js dashboard (if hosting on Hetzner)
# (Skip if using Vercel hybrid — site is on Vercel, lab is here)
cd apps/site
npm install
npm run build
cd ../..
```

---

## 5. Configure Caddy

Create `/etc/caddy/Caddyfile`:

```caddy
# Lab subdomain — main lab interface
lab.whitemagic.dev {
    reverse_proxy localhost:3002
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    encode zstd gzip
    log {
        output file /var/log/caddy/lab-access.log
        format json
    }
}

# API subdomain
api.whitemagic.dev {
    reverse_proxy localhost:8770
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
    }
    encode zstd gzip
}

# MCP server (HTTP transport for A2A agents)
mcp.whitemagic.dev {
    reverse_proxy localhost:8772
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
    }
}

# x402 + gratitude endpoint
pay.whitemagic.dev {
    reverse_proxy localhost:8780
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
    }
}

# SSE event stream (Sangha + observatory)
events.whitemagic.dev {
    reverse_proxy localhost:8791
}
```

Restart Caddy:
```bash
sudo systemctl restart caddy
sudo systemctl enable caddy
sudo systemctl status caddy
```

---

## 6. Systemd Services

### 6.1 WhiteMagic REST API

Create `/etc/systemd/system/whitemagic-api.service`:

```ini
[Unit]
Description=WhiteMagic REST API
After=network.target

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC/core
Environment="PATH=/home/whitemagic/WHITEMAGIC/core/.venv/bin"
Environment="WM_STATE_ROOT=/home/whitemagic/.whitemagic"
Environment="WM_SILENT_INIT=1"
ExecStart=/home/whitemagic/WHITEMAGIC/core/.venv/bin/python scripts/wm_rest_server.py --host 127.0.0.1 --port 8770
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/whitemagic/.whitemagic /home/whitemagic/WHITEMAGIC/state

[Install]
WantedBy=multi-user.target
```

### 6.2 MCP Server (HTTP Transport)

Create `/etc/systemd/system/whitemagic-mcp.service`:

```ini
[Unit]
Description=WhiteMagic MCP Server (HTTP transport for A2A)
After=network.target whitemagic-api.service

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC/core
Environment="PATH=/home/whitemagic/WHITEMAGIC/core/.venv/bin"
Environment="WM_STATE_ROOT=/home/whitemagic/.whitemagic"
Environment="WM_MCP_PRAT=1"
Environment="WM_SILENT_INIT=1"
ExecStart=/home/whitemagic/WHITEMAGIC/core/.venv/bin/python -m whitemagic.run_mcp --http --port 8772
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/whitemagic/.whitemagic

[Install]
WantedBy=multi-user.target
```

### 6.3 x402 + Gratitude Endpoint

Create `/etc/systemd/system/whitemagic-gratitude.service`:

```ini
[Unit]
Description=WhiteMagic Gratitude + x402 Endpoint
After=network.target whitemagic-api.service

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC/core
Environment="PATH=/home/whitemagic/WHITEMAGIC/core/.venv/bin"
Environment="WM_STATE_ROOT=/home/whitemagic/.whitemagic"
Environment="WM_SILENT_INIT=1"
Environment="XRPL_TIP_ADDRESS=YOUR_XRPL_ADDRESS"
ExecStart=/home/whitemagic/WHITEMAGIC/core/.venv/bin/python -m whitemagic.interfaces.gratitude_server --host 127.0.0.1 --port 8780
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/whitemagic/.whitemagic

[Install]
WantedBy=multi-user.target
```

### 6.4 Sangha Coordinator (Multi-Agent)

Create `/etc/systemd/system/whitemagic-sangha.service`:

```ini
[Unit]
Description=WhiteMagic Sangha Multi-Agent Coordinator
After=network.target whitemagic-api.service

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC/core
Environment="PATH=/home/whitemagic/WHITEMAGIC/core/.venv/bin"
Environment="WM_STATE_ROOT=/home/whitemagic/.whitemagic"
Environment="WM_SILENT_INIT=1"
ExecStart=/home/whitemagic/WHITEMAGIC/core/.venv/bin/python -m whitemagic.interfaces.sangha_server --host 127.0.0.1 --port 8790
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/whitemagic/.whitemagic

[Install]
WantedBy=multi-user.target
```

### 6.5 Discord Bot

Create `/etc/systemd/system/whitemagic-discord.service`:

```ini
[Unit]
Description=WhiteMagic Discord Bot (Lab Communication)
After=network.target whitemagic-api.service

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC
Environment="PATH=/home/whitemagic/WHITEMAGIC/core/.venv/bin:/usr/bin"
Environment="WM_STATE_ROOT=/home/whitemagic/.whitemagic"
Environment="DISCORD_BOT_TOKEN=<your-token-from-env-file>"
Environment="WM_SILENT_INIT=1"
ExecStart=/home/whitemagic/WHITEMAGIC/core/.venv/bin/python -m whitemagic.interfaces.discord_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Store the Discord token in `/home/whitemagic/.whitemagic/secrets.env` (mode 600) and source it via an `EnvironmentFile=` directive if you prefer.

### 6.6 Next.js Dashboard (Lab Interface)

```ini
[Unit]
Description=WhiteMagic Lab PWA Dashboard
After=network.target whitemagic-api.service

[Service]
Type=simple
User=whitemagic
WorkingDirectory=/home/whitemagic/WHITEMAGIC/apps/site
Environment="NODE_ENV=production"
Environment="PORT=3002"
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6.7 Enable and Start All Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable whitemagic-api whitemagic-mcp whitemagic-gratitude \
                     whitemagic-sangha whitemagic-discord whitemagic-dashboard
sudo systemctl start whitemagic-api whitemagic-mcp whitemagic-gratitude \
                    whitemagic-sangha whitemagic-discord whitemagic-dashboard

# Check status
sudo systemctl status whitemagic-api
sudo systemctl status whitemagic-mcp
sudo systemctl status whitemagic-gratitude
sudo systemctl status whitemagic-sangha
sudo systemctl status whitemagic-discord
sudo systemctl status whitemagic-dashboard
```

---

## 7. Optional: Ollama (Local LLM Inference)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2:8b         # for routine tasks
ollama pull qwen2.5:14b         # for higher-quality reasoning
ollama pull nomic-embed-text    # for embeddings

# Ollama is already integrated with WhiteMagic (ollama.* tools)
# Verify connectivity
curl http://localhost:11434/api/tags
```

With CCX23 (16 GB RAM), you can run ~7-8B parameter models comfortably alongside the Python stack. For 13B+ models, you may want CCX33 (32 GB).

---

## 8. Environment Variables

Create `/home/whitemagic/.whitemagic/secrets.env` (mode 600):

```bash
chmod 600 /home/whitemagic/.whitemagic/secrets.env
```

```ini
# WhiteMagic Core
WM_STATE_ROOT=/home/whitemagic/.whitemagic
WM_SILENT_INIT=1

# Discord
DISCORD_BOT_TOKEN=...

# Polyglot paths (if using Haskell FFI)
WM_POLYGLOT_HS=/home/whitemagic/WHITEMAGIC/polyglot/whitemagic-hs
WM_POLYGLOT_ZIG=/home/whitemagic/WHITEMAGIC/polyglot/whitemagic-zig/zig-out/lib

# x402 / Gratitude
XRPL_TIP_ADDRESS=YOUR_XRPL_ADDRESS
GRATITUDE_LEDGER_PATH=/home/whitemagic/.whitemagic/gratitude/ledger.jsonl

# API keys (only if using external services)
# OPENROUTER_API_KEY=sk-or-...
# ANTHROPIC_API_KEY=...
```

Source it in services via `EnvironmentFile=` or set individually per service file.

---

## 9. Database and State Setup

```bash
# Create state directory
mkdir -p /home/whitemagic/.whitemagic/{memory,sessions,tasks,votes,cache,logs,data,artifacts,gratitude,observatory}

# Copy any existing memory database from your local machine
# (Do this once, securely, over SSH)
# scp -r ~/.whitemagic/memory/* whitemagic@<hetzner-ip>:~/.whitemagic/memory/

# Set permissions
chown -R whitemagic:whitemagic /home/whitemagic/.whitemagic
chmod 700 /home/whitemagic/.whitemagic
```

---

## 10. Cloudflare in Front

1. Add domain to Cloudflare (free tier)
2. Set DNS A records pointing to Hetzner IP
3. Set SSL/TLS to **Full (strict)**
4. Enable proxy (orange cloud) for DDoS protection
5. Caddy will provision the actual cert via ACME (Let's Encrypt via Cloudflare DNS challenge works automatically)
6. Set up Page Rules:
   - `lab.whitemagic.dev/api/*` → Cache Level: Bypass
   - `lab.whitemagic.dev/.well-known/*` → Cache Level: Bypass (or short TTL)
   - `mcp.whitemagic.dev/*` → Cache Level: Bypass

---

## 11. Verify Deployment

```bash
# Health checks (run from any machine)
curl -I https://lab.whitemagic.dev
curl -I https://api.whitemagic.dev
curl https://api.whitemagic.dev/health
curl https://mcp.whitemagic.dev/health
curl https://pay.whitemagic.dev/health

# MCP server discovery
curl https://lab.whitemagic.dev/.well-known/agent.json | python3 -m json.tool | head -20

# llms.txt is accessible
curl https://lab.whitemagic.dev/llms.txt

# SSE event stream
curl -N https://events.whitemagic.dev/stream &

# Discord bot is online (check your Discord server)
```

---

## 12. Observability

### Logs

```bash
# All services via journalctl
sudo journalctl -u whitemagic-api -f
sudo journalctl -u whitemagic-mcp -f
sudo journalctl -u whitemagic-gratitude -f
sudo journalctl -u whitemagic-sangha -f
sudo journalctl -u whitemagic-discord -f

# Caddy
sudo tail -f /var/log/caddy/lab-access.log
```

### Observatory Data Collection

```bash
# Cron job to collect metrics
crontab -e

# Every 15 minutes: collect MCP registry size, x402 daily volume, etc.
*/15 * * * * /home/whitemagic/WHITEMAGIC/core/.venv/bin/python /home/whitemagic/WHITEMAGIC/scripts/observatory_collect.py >> /home/whitemagic/.whitemagic/observatory/collect.log 2>&1

# Daily at 3am: roll up the day's data into a snapshot
0 3 * * * /home/whitemagic/WHITEMAGIC/core/.venv/bin/python /home/whitemagic/WHITEMAGIC/scripts/observatory_snapshot.py
```

---

## 13. Backup Strategy

```bash
# Backup script
cat > ~/backup-whitemagic.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/whitemagic
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup state (memory DB, gratitude ledger, observatory data)
tar czf $BACKUP_DIR/state_$DATE.tar.gz ~/.whitemagic/

# Backup config
cp /etc/caddy/Caddyfile $BACKUP_DIR/Caddyfile_$DATE
cp /etc/systemd/system/whitemagic-*.service $BACKUP_DIR/

# Optional: backup polyglot build artifacts
# tar czf $BACKUP_DIR/polyglot_$DATE.tar.gz ~/WHITEMAGIC/polyglot/whitemagic-hs/dist-newstyle/

# Keep last 14 days
find $BACKUP_DIR -mtime +14 -delete

# Optional: rsync to Hetzner Storage Box
# rsync -avz $BACKUP_DIR/ u123456@u123456.your-storagebox.de:/backups/whitemagic/

echo "Backup complete: $BACKUP_DIR/state_$DATE.tar.gz"
EOF

chmod +x ~/backup-whitemagic.sh

# Daily at 3am
crontab -e
# Add: 0 3 * * * /home/whitemagic/backup-whitemagic.sh
```

---

## 14. Hybrid Deployment with Vercel (Recommended)

Per the strategy doc's two-track plan, you should run **Vercel for the public-facing site** and **Hetzner for the lab services**:

- **`whitemagic.dev`** (public marketing/agent-discovery site) → **Vercel Hobby (free)**
  - Connect your private GitHub repo
  - Vercel auto-detects Next.js
  - Add env vars: `NEXT_PUBLIC_API_URL=https://api.whitemagic.dev`
  - Deploys on every push; instant rollbacks; edge network for A2A agents

- **`lab.whitemagic.dev`** (lab interface, MCP server, gratitude, Sangha) → **Hetzner CCX23 (this guide)**
  - All the long-running services
  - Persistent state
  - Self-hosted, sovereign

The Caddy config above assumes the public site is on Vercel. If you also want to host it on Hetzner, add:

```caddy
whitemagic.dev {
    reverse_proxy localhost:3000  # PWA site
    # OR redirect to Vercel:
    # redir https://whitemagic-lovat.vercel.app permanent
}
```

---

## 15. Scaling Considerations

**For higher traffic**:
- Add Redis for caching (already in WHITEMAGIC's optional deps)
- Migrate SQLite to PostgreSQL (the disk pool in `core/whitemagic/memory/pool.py` supports it)
- Add a CDN for static assets (Cloudflare free tier covers this)
- Vertical scale: CCX23 → CCX33 (8 vCPU, 32 GB) → CCX43 (16 vCPU, 64 GB)

**For more agents**:
- Each persistent agent in Sangha uses ~50-200 MB RAM depending on context window
- 16 GB supports ~10-15 concurrent agents comfortably
- 32 GB supports 30-40 concurrent agents

**For local LLM scale-out**:
- Run Ollama on a separate Hetzner GPU server (A100, etc.) if needed
- Or rent GPU time on RunPod/Vast for inference-heavy tasks

---

## 16. The Public Artifact (NixOS Path)

If you chose NixOS, the `configuration.nix` is itself a publishable artifact. The strategy doc is explicit:

> "WhiteMagic Labs publishes its production `configuration.nix` as part of its open-source commitment."

Make it public. Commit it to your repo. It's a sovereign-stack statement that distinguishes you from every PaaS-hosted consultancy.

---

## 17. Troubleshooting

| Symptom | Fix |
|---|---|
| Build fails (TypeScript) | `npm run typecheck` locally first |
| Service won't start | `journalctl -u whitemagic-X -n 50` |
| HTTPS not working | Check Cloudflare SSL mode is "Full (strict)"; Caddy needs DNS-01 challenge to work through Cloudflare |
| API returns 502 | `systemctl status whitemagic-api`; check `WM_STATE_ROOT` exists and is writable |
| MCP server unreachable | Check the MCP service is on 8772, not 8770 (API is 8770) |
| Discord bot offline | Check `DISCORD_BOT_TOKEN` is set; verify the bot has been invited to your Discord server with proper permissions |
| Ollama OOM | Reduce model size (use 7B not 14B); or scale up to CCX33 (32 GB) |
| High CPU on shared box | Upgrade to CCX line for dedicated vCPU |

---

## Quick Reference

```bash
# Service management
sudo systemctl status whitemagic-{api,mcp,gratitude,sangha,discord,dashboard}
sudo systemctl restart whitemagic-api
sudo journalctl -u whitemagic-mcp -f

# Logs
sudo tail -f /var/log/caddy/lab-access.log

# Backups
./backup-whitemagic.sh

# Updates
cd ~/WHITEMAGIC && git pull
cd core && source .venv/bin/activate && pip install -e .
cd apps/site && npm install && npm run build
sudo systemctl restart whitemagic-api whitemagic-dashboard
```

---

**The shortest path to live**: Vercel Hobby (30 min) for whitemagic.dev + Hetzner CCX23 (one weekend) for the lab services. Two tracks, each independently shippable, compounding together.

For the longer-term sovereign-stack vision (NixOS, configuration.nix as artifact, MandalaOS spec), this guide provides the foundation; the next layer is your specification work in `docs/spec/MANDALA_OS.md`.
