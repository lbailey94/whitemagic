# Hetzner Setup Runbook for WhiteMagic Self-Hosted Compute

**Status**: Not yet provisioned. This is the runbook for when you're ready.
**Last updated**: 2026-06-20
**Owner**: Lucas Bailey
**Estimated cost**: €17-77/mo depending on box size
**Estimated setup time**: 1-2 hours

---

## Why Hetzner

WhiteMagic's site stays on Vercel Hobby (free). But certain workloads don't fit
Vercel Hobby's 10s timeout, 1 GB memory, and 0.6 CPU per function:

- **Librarian LLM** — needs >10s for long answers, needs >1 GB for local models
- **MCP server** — planned, needs persistent state
- **x402 payment rails** — planned, needs consistent uptime
- **Discord bot** — planned

Hetzner CCX gives us 4-16 vCPU, 16-64 GB RAM, fast NVMe, €17-77/mo. Way cheaper
than Vercel Pro ($20/mo) for compute-heavy workloads.

## Decision matrix

| Workload | Best target | Why |
|---|---|---|
| Site (UI, marketing, catalog) | Vercel Hobby | Free, fast global CDN |
| `/api/librarian/chat` (LLM call) | Hetzner + Ollama | >10s streaming, free local LLM |
| `/api/run-bridge-fn` (catalog demo) | Vercel Hobby | Short responses, fits Hobby |
| `/mcp` (planned MCP server) | Hetzner | Persistent state, no timeout |
| `/x402` (planned) | Hetzner | Consistent uptime |
| Discord bot (planned) | Hetzner | WebSocket connection |

The site routes `/api/librarian/chat` to the Hetzner box via the
`OLLAMA_BASE_URL` env var. Default in dev is `http://localhost:11434`
(works on the same machine); in prod, set it to the Hetzner box.

## Step 1: Provision the box

1. Sign in to https://console.hetzner.com (or create an account)
2. **Servers → New Server**:
   - **Location**: Falkenstein, Germany (FSN1) or Ashburn, VA, USA (ash)
   - **Image**: Ubuntu 24.04 LTS
   - **Type**: 
     - **CCX23** (€17/mo, 4 vCPU, 16 GB RAM, 160 GB NVMe) — for 8B model + librarian
     - **CCX33** (€34/mo, 8 vCPU, 32 GB RAM, 360 GB NVMe) — for 13B model
     - **CCX63** (€77/mo, 16 vCPU, 64 GB RAM, 360 GB NVMe) — for 70B model
   - **Networking**: IPv4 + IPv6 (default)
   - **SSH keys**: add your public key
   - **Name**: `whitemagic-compute` (or whatever)
3. Click **Create & Buy**. Provisioning takes ~30s.
4. Note the **public IPv4 address** — this is your `OLLAMA_BASE_URL` host.

## Step 2: Initial server setup

SSH in: `ssh root@<your-ipv4>`

```bash
# Update + install essentials
apt update && apt upgrade -y
apt install -y ufw curl git fail2ban

# Create non-root user for the service
adduser whitemagic --disabled-password --gecos ""
mkdir -p /home/whitemagic/.ssh
cp ~/.ssh/authorized_keys /home/whitemagic/.ssh/
chown -R whitemagic:whitemagic /home/whitemagic/.ssh
chmod 700 /home/whitemagic/.ssh
chmod 600 /home/whitemagic/.ssh/authorized_keys

# Allow passwordless sudo (optional, for service management)
echo "whitemagic ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/whitemagic

# Configure firewall: SSH + Ollama only
ufw default deny incoming
ufw allow 22/tcp       # SSH
ufw allow 11434/tcp    # Ollama (lock down by IP later)
ufw enable
```

## Step 3: Install Ollama

```bash
# As whitemagic user
su - whitemagic
curl -fsSL https://ollama.com/install.sh | sh

# Verify install
ollama --version

# Pull a model (start with 8B; pull larger ones if you have the box)
ollama pull llama3.1:8b       # 4.7 GB, good for 16 GB RAM
# ollama pull qwen2.5:7b      # alternative 7B
# ollama pull llama3.1:70b    # 40 GB, needs 64 GB RAM

# Start Ollama as a system service
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify it's listening
curl http://localhost:11434/v1/models
```

## Step 4: Lock down the Ollama port

Ollama listens on `0.0.0.0:11434` by default. You need to either:

**Option A: Whitelist Vercel egress IPs (recommended).** Vercel's outbound
IPs are documented at https://vercel.com/docs/answers/what-are-the-vercel-static-ip-addresses
(rotates; check docs). The simplest is to add a reverse proxy that
authenticates requests with a shared secret.

**Option B: Use a Cloudflare Tunnel in front.** This is what the WhiteMagic
MCP server planned architecture uses (see site AGENTS.md §2).

Quick shared-secret approach (good enough for low-stakes librarian use):

```bash
# Install nginx
sudo apt install -y nginx

# Configure a reverse proxy with a secret header
cat > /etc/nginx/sites-available/ollama <<'EOF'
server {
    listen 11434;
    server_name _;
    
    # Require a shared secret in a request header
    if ($http_x_ollama_secret != "YOUR-SECRET-HERE") {
        return 403;
    }
    
    location / {
        proxy_pass http://127.0.0.1:11434;
        proxy_set_header Host $host;
        proxy_buffering off;  # critical for streaming
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
EOF
ln -s /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/ollama
sudo nginx -t && sudo systemctl reload nginx
```

Set `OLLAMA_BASE_URL=http://<your-ipv4>:11434` in the Vercel env. The
site will append the `X-Ollama-Secret` header automatically (TODO: wire
this in `lib/librarian/llm.ts`).

**Option C: SSH tunnel** (for development only). Run a local Ollama on
your dev machine and tunnel to it. Not for production.

## Step 5: Wire the Vercel site to Hetzner

In the Vercel project settings, add env vars:

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://<your-ipv4>:11434
OLLAMA_MODEL=llama3.1:8b
```

If you set up the shared-secret nginx proxy, also add:

```
OLLAMA_SECRET=YOUR-SECRET-HERE
```

And update `lib/librarian/llm.ts` to send the `X-Ollama-Secret` header
when the env var is set.

## Step 6: Test end-to-end

```bash
# From Vercel (after deploy):
curl -X POST https://whitemagic.dev/api/librarian/status | jq

# Should show:
# {
#   "provider": { "provider": "ollama", "configured": true, ... },
#   "bridge": { "librarian_can_call": 21, ... },
#   ...
# }

# Then chat (UI at /chat) and verify responses stream.
```

## Step 7: Ongoing maintenance

- **Ollama upgrades**: `ollama pull <model>` for new versions. Restart the
  service if kernel-level changes happen.
- **Backups**: Ollama models live in `/usr/share/ollama/.ollama/models`.
  Snapshot weekly to S3 (or use Hetzner Storage Box at €3.50/mo).
- **Monitoring**: `journalctl -u ollama` for logs. Consider adding
  Prometheus + Grafana if you scale beyond 1 box.
- **Capacity planning**: At 100 chats/day × 1K tokens × 8B model, the box
  runs at ~5% CPU. Plenty of headroom. Scale up if you see >50% sustained.

## When to scale up

| Signal | Move to |
|---|---|
| Sustained >50% CPU | CCX33 (€34/mo) |
| Want 13B+ model quality | CCX33 (€34/mo) |
| >10 concurrent librarian users | CCX63 (€77/mo) + 70B model |
| Need 24/7 availability | Add 2nd box + load balancer (€34-154/mo) |
| Need GPU inference (faster) | Hetzner GPU servers (€200+/mo, A100) |

## Cost summary

| Box | €/mo | Use case |
|---|---|---|
| CCX23 (4 vCPU / 16 GB) | 17 | Default — 8B Ollama, librarian + MCP |
| CCX33 (8 vCPU / 32 GB) | 34 | 13B Ollama, higher traffic |
| CCX63 (16 vCPU / 64 GB) | 77 | 70B Ollama, multi-tenant |
| Hetzner Storage Box (1 TB) | 3.50 | Backups (optional) |
| **Total monthly** | **20-110** | depending on scale |

Compare to Vercel Pro ($20/mo) which still has the 10s timeout ceiling.

## Open follow-ups

- [ ] Wire `OLLAMA_SECRET` to `lib/librarian/llm.ts` (currently no auth header)
- [ ] Add `X-Librarian-Provider` to /api/librarian/chat response (already done in route)
- [ ] Document Cloudflare Tunnel setup for production-grade security
- [ ] Add Ollama model warming (keep model in memory between requests)
- [ ] Wire Vercel → Hetzner observability (logs, errors, metrics)
