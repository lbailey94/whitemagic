# Hetzner Deploy Walkthrough — whitemagic.dev

**Created**: 2026-04-19
**Target**: Hetzner VPS (CX22 or equivalent, Ubuntu 24.04 LTS)
**Stack**: Next.js 15 standalone → systemd → Caddy (TLS + reverse proxy) → Cloudflare (DNS + DDoS)
**Estimated time**: 3–4 hours first time; ~2 minutes per subsequent deploy

---

## Decision to deploy here is in `@docs/architecture/INFRASTRUCTURE_DECISION.md`.

Read that first if you're returning to this without context.

---

## Prerequisites (do these before starting the walkthrough)

- [ ] **Hetzner VPS provisioned.** CX22 (€4.51/mo) is fine. Pick a DC in Germany or Finland. Ubuntu 24.04 LTS. SSH key on file.
- [ ] **Domain control**: `whitemagic.dev` DNS transferable to Cloudflare (or already there).
- [ ] **Cloudflare account** with `whitemagic.dev` added (nameservers pointed per Cloudflare instructions).
- [ ] **Private GitHub repo** created (e.g. `whitemagic-ai/whitemagic-site-private`).
- [ ] **Local SSH access verified**: `ssh root@<hetzner_ip>` works.
- [ ] **OpenRouter API key** created at [openrouter.ai](https://openrouter.ai).
- [ ] **Upstash Redis** free tier account created; have the REST URL + token.
- [ ] **Stripe payment links** created for Office Hours ($250) + Architecture Review ($2,500). Links look like `https://buy.stripe.com/test_xxx` or `https://buy.stripe.com/xxx`.

---

## Step 1 — Harden the VPS (~30 min)

**Run these on the Hetzner box** (don't let Cascade run them; read each first).

```bash
# SSH in as root
ssh root@<hetzner_ip>

# Update the system
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades curl ca-certificates gnupg lsb-release

# Create a non-root user for the app
useradd -m -s /bin/bash whitemagic
usermod -aG sudo whitemagic
# Copy your SSH key to the new user
mkdir -p /home/whitemagic/.ssh
cp /root/.ssh/authorized_keys /home/whitemagic/.ssh/
chown -R whitemagic:whitemagic /home/whitemagic/.ssh
chmod 700 /home/whitemagic/.ssh
chmod 600 /home/whitemagic/.ssh/authorized_keys

# Firewall — allow SSH, HTTP, HTTPS; deny everything else
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp       # SSH
ufw allow 80/tcp       # HTTP (for Let's Encrypt ACME challenge)
ufw allow 443/tcp      # HTTPS
ufw enable

# fail2ban for SSH brute force protection
systemctl enable --now fail2ban

# Auto-install security patches
dpkg-reconfigure -plow unattended-upgrades
# When prompted, select "Yes"

# Disable root SSH login (do this AFTER verifying whitemagic user can SSH in)
# From your local laptop, run: ssh whitemagic@<hetzner_ip>
# If that works, come back as root and:
sed -i 's/#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Verify from your laptop: ssh root@<hetzner_ip>  → should now REFUSE.
#                          ssh whitemagic@<hetzner_ip> → should still work.
```

## Step 2 — Install Node.js 20 (~5 min)

As the `whitemagic` user (or root; your call):

```bash
# NodeSource repo for Node 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

node --version   # → v20.x
npm --version
```

## Step 3 — Install Caddy (~5 min)

Caddy handles TLS (Let's Encrypt auto) and reverse proxies to Next.js on `localhost:3000`.

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Verify
caddy version
```

## Step 4 — Directory structure (~5 min)

As `whitemagic`:

```bash
sudo mkdir -p /srv/whitemagic-site
sudo chown whitemagic:whitemagic /srv/whitemagic-site
cd /srv/whitemagic-site

# Clone the private deploy repo (after setting up a deploy key per step 8)
git clone git@github.com:whitemagic-ai/whitemagic-site-private.git .
```

(If the private repo doesn't exist yet, come back to this step after
step 8 completes.)

## Step 5 — Configure Next.js for standalone output

In the site repo (`apps/site/next.config.mjs` or `next.config.js` in the
standalone repo), ensure `output: 'standalone'` is set so Next emits a
self-contained Node server.

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // ... existing config
};
export default nextConfig;
```

Verify by running `npm run build` locally — you should see `.next/standalone/`
and `.next/static/` directories emitted.

## Step 6 — Environment variables file

On the VPS, create `/srv/whitemagic-site/.env.production.local` (not in git):

```bash
sudo -u whitemagic bash -c 'cat > /srv/whitemagic-site/.env.production.local' <<'EOF'
# ── LLM ────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-v1-REDACTED

# ── KV ─────────────────────────────────────────
UPSTASH_REDIS_REST_URL=https://REDACTED.upstash.io
UPSTASH_REDIS_REST_TOKEN=REDACTED

# ── Budget ─────────────────────────────────────
LIBRARIAN_MONTHLY_CAP_USD=25
# LIBRARIAN_DISABLED=1          # uncomment to disable Librarian globally

# ── Stripe (public — safe to commit if you wanted to) ──
NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL=https://buy.stripe.com/REDACTED
NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL=https://buy.stripe.com/REDACTED

# ── Admin (Basic Auth gate on /admin) ──────────
# SHA-256 hex of the shared admin password. Generate with:
#   node -e "require('crypto').createHash('sha256').update('YOUR_PASSWORD').digest('hex')"
# or:
#   printf '%s' 'YOUR_PASSWORD' | sha256sum | cut -d' ' -f1
# Leave blank in dev to skip the gate. Username is "admin" by default
# (override with ADMIN_USER if desired).
ADMIN_PASSWORD_HASH=REDACTED
# ADMIN_USER=admin

# ── Resend (contact-form email notifications) ──
# Leave blank to disable emails; submissions still land in /admin feed.
# Get key: https://resend.com → API Keys
# RESEND_API_KEY=re_REDACTED
# CONTACT_NOTIFY_EMAIL=lucas@example.com
# Optional sender; defaults to Resend's onboarding address until domain verified:
# CONTACT_FROM_EMAIL="WhiteMagic <notifications@whitemagic.dev>"
EOF
chmod 600 /srv/whitemagic-site/.env.production.local
```

## Step 7 — systemd service unit (~10 min)

Create `/etc/systemd/system/whitemagic-site.service`:

```ini
[Unit]
Description=whitemagic.dev Next.js site
After=network.target

[Service]
Type=simple
User=whitemagic
Group=whitemagic
WorkingDirectory=/srv/whitemagic-site/apps/site/.next/standalone
# Load .env.production.local so the Next.js runtime sees env vars
EnvironmentFile=/srv/whitemagic-site/.env.production.local
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=HOSTNAME=127.0.0.1
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5
# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/srv/whitemagic-site
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable whitemagic-site
# Don't start it yet — we need to build first (step 9)
```

## Step 8 — GitHub deploy key (read-only, for the VPS)

On the VPS as `whitemagic`:

```bash
ssh-keygen -t ed25519 -C "whitemagic-site deploy" -f ~/.ssh/id_ed25519_deploy -N ""
cat ~/.ssh/id_ed25519_deploy.pub   # copy this
```

In GitHub: `whitemagic-ai/whitemagic-site-private` → Settings → Deploy keys
→ Add deploy key. Title: "Hetzner VPS read-only". Paste public key. Do NOT
check "Allow write access".

Back on the VPS, configure SSH to use this key for GitHub:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

# Verify
ssh -T git@github.com   # → "Hi whitemagic-ai/whitemagic-site-private!"
```

## Step 9 — First deploy (manual, to verify)

```bash
cd /srv/whitemagic-site
git pull
cd apps/site
npm ci
npm run build
# Next.js standalone build emits .next/standalone/ which needs static + public copied in
cp -R .next/static .next/standalone/.next/
cp -R public .next/standalone/

sudo systemctl start whitemagic-site
sudo systemctl status whitemagic-site    # should be "active (running)"

# Verify
curl -s http://127.0.0.1:3000/ | head -c 200
# → should return HTML
```

## Step 10 — Caddyfile (~10 min)

Create `/etc/caddy/Caddyfile`:

```caddyfile
whitemagic.dev, www.whitemagic.dev {
    # Cloudflare sits in front and handles TLS at the edge; Caddy still
    # terminates its own TLS at the origin for defense in depth.
    # If you prefer "flexible" SSL mode at Cloudflare (TLS only to the
    # edge), you can set `tls internal` here and skip Let's Encrypt,
    # but full-strict is better.

    # Reverse proxy to the Next.js server
    reverse_proxy 127.0.0.1:3000

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        # Remove Caddy's own server header
        -Server
    }

    # Aggressive caching for static assets
    @static path /_next/static/* /favicon.ico /*.svg /*.png /*.jpg /*.webp /*.woff2
    header @static Cache-Control "public, max-age=31536000, immutable"

    # Compression
    encode zstd gzip

    log {
        output file /var/log/caddy/whitemagic.log {
            roll_size 100mb
            roll_keep 7
        }
    }
}

# Redirect apex → www if desired (remove if you prefer the apex)
# www.whitemagic.dev {
#     redir https://whitemagic.dev{uri} permanent
# }
```

Start Caddy:

```bash
sudo systemctl enable --now caddy
sudo systemctl status caddy
# Caddy auto-provisions Let's Encrypt certs on first request
```

## Step 11 — Cloudflare DNS (~5 min)

In Cloudflare dashboard for `whitemagic.dev`:

- Add A record: `@` → `<hetzner_ip>` — Proxy status: **Proxied** (orange cloud)
- Add A record: `www` → `<hetzner_ip>` — Proxy status: **Proxied**
- SSL/TLS mode: **Full (strict)** (requires valid origin cert — Caddy's Let's Encrypt cert satisfies this)
- Always Use HTTPS: **On**
- Automatic HTTPS Rewrites: **On**
- Minimum TLS Version: **TLS 1.2**

Verify from your laptop:

```bash
curl -I https://whitemagic.dev/
# → HTTP/2 200, cf-ray header present
```

If you see `cf-ray` you're going through Cloudflare. If you see a different
cert issuer than Cloudflare's, check SSL/TLS mode.

## Step 12 — Deploy script (simple version)

Create `/srv/whitemagic-site/deploy.sh` (runnable by `whitemagic`):

```bash
#!/usr/bin/env bash
set -euo pipefail

cd /srv/whitemagic-site
git fetch --all --quiet
git reset --hard origin/main

cd apps/site
npm ci --silent
npm run build
rm -rf .next/standalone/.next/static .next/standalone/public
cp -R .next/static .next/standalone/.next/
cp -R public .next/standalone/

sudo systemctl restart whitemagic-site
echo "Deployed: $(git -C /srv/whitemagic-site rev-parse --short HEAD)"
```

```bash
chmod +x /srv/whitemagic-site/deploy.sh
```

Allow the `whitemagic` user to restart its own service without a password:

```bash
sudo visudo -f /etc/sudoers.d/whitemagic-deploy
```

```
whitemagic ALL=(root) NOPASSWD: /usr/bin/systemctl restart whitemagic-site
```

Now from your local laptop, deploying is:

```bash
ssh whitemagic@whitemagic.dev '/srv/whitemagic-site/deploy.sh'
```

## Step 13 — GitHub Actions (automated deploy)

Create `.github/workflows/deploy.yml` in the private repo:

```yaml
name: Deploy to Hetzner

on:
  push:
    branches: [main]
  workflow_dispatch: {}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger remote deploy
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: ${{ secrets.HETZNER_USER }}
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: /srv/whitemagic-site/deploy.sh
```

GitHub repo secrets needed:

- `HETZNER_HOST` — the IP or hostname
- `HETZNER_USER` — `whitemagic`
- `HETZNER_SSH_KEY` — private key for a **GitHub Actions–specific** deploy user SSH key (generate on your laptop, add public key to `whitemagic@<host>:~/.ssh/authorized_keys`, paste private key into GitHub secret)

Now `git push origin main` auto-deploys.

---

## Verification checklist (before announcing "we're live")

- [ ] `https://whitemagic.dev/` returns 200
- [ ] `https://whitemagic.dev/librarian` loads and chat works
- [ ] Ask Librarian "pricing?" → real Claude response with PricingCard rendered
- [ ] Ask "Tell me about Aria" → Dharma refusal renders as amber notice
- [ ] Visit `/admin` → budget shows tiny spend from your test conversations, karma ledger has entries
- [ ] Floating Librarian appears on every page except `/librarian` and `/admin`
- [ ] `⌘K` / `Ctrl+K` toggles the bubble
- [ ] Mobile (real phone, not dev tools): site usable, Librarian bubble reachable
- [ ] Dark/light theme toggle works
- [ ] DNS: `dig whitemagic.dev` shows Cloudflare IPs (not Hetzner direct)
- [ ] `curl -I https://whitemagic.dev/` shows `cf-ray` header
- [ ] TLS: `https://www.ssllabs.com/ssltest/analyze.html?d=whitemagic.dev` → A or A+
- [ ] `sudo systemctl status whitemagic-site` → active (running) on the VPS
- [ ] `sudo systemctl status caddy` → active (running)
- [ ] Tail Caddy log for a real visit: `sudo tail -f /var/log/caddy/whitemagic.log`

## Ongoing operations

### Monitoring

- Vercel gave you free uptime pings. You don't have that now. Set up
  **UptimeRobot** (free for 50 monitors, 5-min interval) or **Better
  Uptime** (free tier) to ping `https://whitemagic.dev/` and
  `https://whitemagic.dev/api/librarian/karma`. Alert to email.
- Cloudflare Analytics (built-in, free) shows traffic patterns.

### Updates

Monthly:
```bash
ssh whitemagic@whitemagic.dev
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
sudo systemctl restart whitemagic-site   # after npm updates if any
```

### Key rotation schedule

- **OpenRouter key**: every 90 days, or immediately if any leak suspected
- **Upstash token**: every 180 days
- **SSH keys**: annual review; retire old keys immediately when a laptop is sold/lost
- **GitHub deploy keys**: annual review

### Incident response

If compromised:
1. `sudo systemctl stop whitemagic-site caddy` — stop serving
2. Change DNS in Cloudflare to a maintenance page (serve from CF Workers if needed)
3. Rotate all env var secrets
4. Forensics: `/var/log/auth.log`, `/var/log/caddy/whitemagic.log`, `journalctl -u whitemagic-site`
5. Rebuild VPS from snapshot if unsure
6. Post-incident: write up what happened on the `/writing` page (dogfooding transparency)

---

## Troubleshooting first-deploy issues

**`systemctl start whitemagic-site` fails**:
`journalctl -xeu whitemagic-site` — look for missing env var, wrong path, permission issue.

**Caddy can't get TLS cert**:
Check that Cloudflare proxy is **grey cloud (DNS only)** during initial
cert issuance, then switch to orange once it works. Let's Encrypt needs
to reach your VPS directly on port 80.

**"Cannot find module" on Next.js start**:
You forgot to copy `.next/static` or `public` into `.next/standalone/`.
The deploy script does this automatically; manual first deploy needs the
same.

**Chat API works locally but not on Hetzner**:
Check env vars are loaded by systemd:
`sudo systemctl show whitemagic-site | grep -i env` — should show
`EnvironmentFile=/srv/whitemagic-site/.env.production.local`.

---

## When things go well

You should have `whitemagic.dev` live on infrastructure you control,
with TLS, CDN, DDoS protection, rate limiting, budget caps, and a
real Librarian answering real questions — running on a €5/month box
in Germany. First deploy to done: 3–4 hours. Subsequent deploys:
`git push` → 2 minutes.
