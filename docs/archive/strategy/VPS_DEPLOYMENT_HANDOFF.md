# VPS Deployment — Session Handoff

**Date**: 2026-06-24
**Status**: Scripts ready, deployment not yet executed. Needs interactive session on the VPS.

---

## What's Ready

### Scripts (in `whitemagic-public` repo, `ops/` directory)

| Script | Purpose | Run As |
|--------|---------|--------|
| `phase-b-harden.sh` | SSH lockdown, fail2ban, UFW firewall, create whitemagic user | root |
| `phase-b-lock-ssh.sh` | Disable root login + password auth, key-only enforcement | root |
| `phase-c-deploy.sh` | Clone repos, build venv + Next.js, install systemd services | whitemagic |
| `phase-d-start.sh` | Start services, health checks, TLS verification | root |
| `redeploy.sh` | Quick update + restart (core/site/both) | whitemagic |

### Service Files (in `whitemagic-public/deploy/`)

| File | Port | Purpose |
|------|------|---------|
| `whitemagic-api.service` | 8770 | Python REST API (`wm_rest_server.py`) |
| `whitemagic-dashboard.service` | 3002 | Next.js site (`npm run start`) |
| `Caddyfile` | 80/443 | Reverse proxy + auto-TLS for whitemagic.dev + api.whitemagic.dev |

### Key Paths on VPS

| Path | What |
|------|------|
| `/home/whitemagic/WHITEMAGIC` | Core repo (Python) |
| `/home/whitemagic/whitemagic-site` | Site repo (Next.js) |
| `/home/whitemagic/.whitemagic/` | State directory (memory DB, logs, scratchpads) |
| `/etc/systemd/system/whitemagic-*.service` | Systemd units |
| `/etc/caddy/Caddyfile` | Caddy config |

---

## Pre-Deployment Checklist

Before starting the session, ensure:

1. **Hetzner VPS provisioned** — CCX23 or CX22 recommended (2 vCPU, 4GB RAM minimum)
2. **SSH access** — You have root SSH key access to the VPS
3. **DNS configured** — `whitemagic.dev` and `api.whitemagic.dev` A records point to the VPS IP
4. **GitHub SSH keys** — The `whitemagic` user on the VPS has SSH keys that can clone:
   - `git@github.com:lbailey94/whitemagic.git` (core, public)
   - `git@github.com:lbailey94/whitemagic-site-private.git` (site, private)
5. **Cloudflare** — If using Cloudflare for DNS, ensure proxy status is "DNS only" (grey cloud) during initial TLS provisioning, then switch to proxied after certs are obtained

---

## Execution Order

```bash
# 1. On the VPS as root:
bash phase-b-harden.sh
bash phase-b-lock-ssh.sh

# 2. As the whitemagic user:
su - whitemagic
bash phase-c-deploy.sh

# 3. As root:
sudo bash phase-d-start.sh
```

---

## Common Issues to Watch For

### 1. Git Clone Fails
**Symptom**: `git clone git@github.com:lbailey94/...` fails with permission denied
**Fix**: Set up SSH keys for the whitemagic user:
```bash
sudo -u whitemagic ssh-keygen -t ed25519 -C "whitemagic@vps"
sudo -u whitemagic cat ~/.ssh/id_ed25519.pub
# Add the public key to GitHub deploy keys for both repos
```

### 2. Next.js Build Fails
**Symptom**: `npm run build` fails with type errors or missing env vars
**Fix**: Check if `.env.production` is needed. The site may require:
```bash
# In ~/whitemagic-site/.env.production
NEXT_PUBLIC_WIP_MODE=0
# Add any other required env vars
```

### 3. Caddy TLS Provisioning Fails
**Symptom**: `caddy validate` passes but `curl https://whitemagic.dev` fails
**Fix**: 
- Check DNS: `dig +short whitemagic.dev` must return the VPS IP
- Check Caddy logs: `journalctl -u caddy -f | grep -i cert`
- If Cloudflare is proxied (orange cloud), Caddy can't get HTTP-01 challenges. Switch to DNS-only (grey cloud) first, then re-enable after cert is provisioned

### 4. API Service Fails to Start
**Symptom**: `systemctl status whitemagic-api` shows failed
**Fix**: 
```bash
journalctl -u whitemagic-api -n 50
# Common: missing PYTHONPATH, missing polyglot libs
# Check: LD_LIBRARY_PATH in the service file matches actual paths
```

### 5. Dashboard Service Fails to Start
**Symptom**: `systemctl status whitemagic-dashboard` shows failed
**Fix**:
```bash
journalctl -u whitemagic-dashboard -n 50
# Common: .next/ directory missing (build failed), PORT env not set
# Verify: ls -la ~/whitemagic-site/.next/server/app/
```

---

## Post-Deployment Verification

```bash
# API health
curl -s http://localhost:8770/health | python3 -m json.tool

# Dashboard
curl -s http://localhost:3002 | head -5

# Caddy TLS
curl -sI https://whitemagic.dev | head -10
curl -sI https://api.whitemagic.dev | head -10

# Service status
systemctl is-active whitemagic-api whitemagic-dashboard caddy
```

---

## Redeploy After Code Updates

```bash
# As whitemagic user:
bash redeploy.sh both    # Updates core + site + restarts both
bash redeploy.sh core    # Updates core only
bash redeploy.sh site    # Updates site only
```

---

## What to Do in the Session

1. SSH into the VPS
2. Run phases B → C → D in order
3. Debug any issues using the guide above
4. Verify all health checks pass
5. Test `https://whitemagic.dev` and `https://api.whitemagic.dev` from a browser
6. If Cloudflare is used, switch to proxied mode after TLS is confirmed
7. Set up monitoring: `journalctl -u whitemagic-api -f` for live logs

**Estimated time**: 2-4 hours (including DNS propagation wait and debugging)
