# WhiteMagic Labs Site — Deployment Guide

**Site**: `whitemagic-site` (Next.js 15 + TypeScript + Tailwind CSS)
**Location**: `/home/lucas/Desktop/whitemagic-site`
**Last Updated**: 2026-06-04

---

## Prerequisites

- Node.js 20+ (LTS recommended)
- npm 10+
- A Stripe account (optional — for payment links)
- A deployment target (see options below)

---

## Local Development

```bash
cd /home/lucas/Desktop/whitemagic-site

# Install dependencies
npm install

# Run dev server
npm run dev
# → http://localhost:3000
```

---

## Pre-Deploy Checklist

```bash
# 1. Typecheck
npm run typecheck

# 2. Lint
npm run lint

# 3. Build locally (catches errors before remote deploy)
npm run build

# 4. Verify static export works
ls -la out/          # should exist with index.html
```

---

## Option A: Static Export (Simplest)

This site is configured for **static export** — it generates plain HTML/JS/CSS files that can be served from any static host (GitHub Pages, Cloudflare Pages, Netlify, Vercel, or any web server).

```bash
cd /home/lucas/Desktop/whitemagic-site

# Set up environment (copy example, then fill in Stripe links if you have them)
cp .env.local.example .env.local
# Edit .env.local with your Stripe Payment Link URLs

# Build static export
npm run build
# Output goes to ./out/

# Verify
ls out/
# Should contain: index.html, 404.html, _next/, pricing/, services/, etc.
```

### Deploy to Any Static Host

**GitHub Pages**:
```bash
# Push the out/ folder to a gh-pages branch
# Or use GitHub Actions (see .github/workflows/ if configured)
```

**Cloudflare Pages**:
```bash
# Drag and drop the out/ folder into Cloudflare Pages dashboard
# Or use Wrangler CLI
npx wrangler pages deploy out/
```

**Netlify**:
```bash
# Drag and drop the out/ folder into Netlify dashboard
# Or use Netlify CLI
netlify deploy --dir=out --prod
```

**Vercel**:
```bash
# Vercel auto-detects Next.js — just push to git and connect repo
# Or use CLI
vercel --prod
```

**Hetzner / Any VPS (Caddy / Nginx)**:
```bash
# On your VPS, create web root
sudo mkdir -p /var/www/whitemagic-site
sudo chown $USER:$USER /var/www/whitemagic-site

# Copy built files
rsync -avz --delete out/ user@your-server:/var/www/whitemagic-site/

# Caddyfile example
# Caddyfile:
# whitemagic.dev {
#     root * /var/www/whitemagic-site
#     file_server
#     try_files {path} {path}.html {path}/index.html =404
# }

# Nginx config example
# server {
#     listen 80;
#     server_name whitemagic.dev;
#     root /var/www/whitemagic-site;
#     index index.html;
#     location / {
#         try_files $uri $uri.html $uri/ =404;
#     }
# }
```

---

## Option B: Next.js Server (for API routes)

If you need the Librarian chat API (`/api/chat`) or other server-side routes:

```bash
npm run build
npm start
# → Runs on port 3000 (or PORT env var)
```

Use **PM2** or **systemd** for production:

```bash
# PM2
npm install -g pm2
pm2 start "npm start" --name whitemagic-site
pm2 save
pm2 startup

# Or systemd service
# See deploy/whitemagic-dashboard.service in the main repo for a template
```

---

## Option C: Hetzner VPS (Full Stack)

If deploying the **full WhiteMagic stack** (API + site + polyglot) alongside this site, see the existing guide:

`/home/lucas/Desktop/WHITEMAGIC/docs/deploy/HETZNER_DEPLOY.md`

For **site-only** deployment to an existing Hetzner VPS:

```bash
# Build locally
cd /home/lucas/Desktop/whitemagic-site
npm run build

# Deploy via rsync
rsync -avz --delete out/ whitemagic@your-hetzner-ip:/var/www/whitemagic-site/

# Caddy already configured? Just reload
ssh whitemagic@your-hetzner-ip "sudo systemctl reload caddy"
```

---

## Environment Variables

Create `.env.local` from the example:

```bash
cp .env.local.example .env.local
```

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL` | No | Stripe Payment Link for $1,000 Office Hours |
| `NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL` | No | Stripe Payment Link for $12,000 Architecture Review |

**Without Stripe links**: The pricing page falls back to `/contact` forms. The site works fine without them.

**With Stripe links**:
1. Log in to [dashboard.stripe.com](https://dashboard.stripe.com)
2. Go to **Payment Links** → **+ Create**
3. Set price: `$1,000.00` for Office Hours, `$12,000.00` for Architecture Review
4. Set product name: `WhiteMagic Labs — Office Hours` / `Architecture Review`
5. Copy the Payment Link URL into `.env.local`
6. Rebuild and redeploy

---

## DNS

Point your domain's A record to your server's IP:

```
A  whitemagic.dev  → <server-ip>
```

If using Cloudflare or another CDN: use their DNS, set A record, and enable proxy if desired.

---

## Post-Deploy Verification

```bash
# Check site loads
curl -s https://whitemagic.dev | head -20

# Check .well-known/agent.json
curl -s https://whitemagic.dev/.well-known/agent.json | python3 -m json.tool | head -10

# Check pricing page
curl -s https://whitemagic.dev/pricing | grep -o '$[0-9,]*' | sort -u

# Check OpenGraph image
curl -sI https://whitemagic.dev/pricing/opengraph-image.png | head -5
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `out/` folder is empty or missing `index.html` | Check `next.config.mjs` has `output: 'export'` (or `distDir: 'out'`) |
| Images not loading in static export | Use `unoptimized: true` in `next.config.mjs` for static hosts |
| API routes 404 in static export | Expected — static export has no server. Use Option B for API routes |
| Build fails with TypeScript errors | Run `npm run typecheck` locally first |
| Stripe links not appearing | Verify `.env.local` exists and URLs start with `https://` |

---

## Quick Reference

```bash
cd /home/lucas/Desktop/whitemagic-site

# Dev
npm run dev

# Build (static export)
npm run build

# Check
ls out/

# Deploy (rsync to VPS example)
rsync -avz --delete out/ user@server:/var/www/whitemagic-site/
```

---

## Current Blockers (as of 2026-06-04)

1. **No Stripe account**: Payment links fall back to `/contact` forms. Site is functional.
2. **No deployed server**: Site is desktop-only. Pick a host from Option A and deploy.
3. **No DNS**: `whitemagic.dev` (or your chosen domain) needs A record pointed at server.

The shortest path to live: **static export + Cloudflare Pages or Netlify** (free, 5 minutes). No server needed.
