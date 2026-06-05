# WhiteMagic Labs Site — Deployment Guide

**Site**: `whitemagic-site` (Next.js 15 + TypeScript + Tailwind CSS)
**Location**: `/home/lucas/Desktop/whitemagic-site`
**Last Updated**: 2026-06-05

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

# 4. Verify server build output
ls -la .next/server/app/
# Should contain routes: index.html, about/, contact/, grants/, etc.
```

---

## Important: This Is a Next.js Server App

This site has **API routes** (`/api/aria/*`, `/api/well-known/*`, `/api/wm/*`) and **dynamic rewrites** that require a running Node.js server. **Static export is not supported** without removing these features.

Deploy as a **Next.js server application**, not static HTML.

---

## Option A: Vercel (Fastest — Recommended)

Vercel is the native host for Next.js. Connect your GitHub repo and auto-deploy on every push.

```bash
# 1. Ensure repo is pushed to GitHub
#    (already done: lbailey94/whitemagic-site-private)

# 2. Go to vercel.com → Add New Project → Import GitHub repo

# 3. Vercel auto-detects Next.js settings. Click Deploy.

# 4. Add environment variables in Vercel dashboard if needed:
#    (Stripe links, API keys, etc.)

# 5. Point whitemagic.dev DNS to Vercel
#    A record: 76.76.21.21 (Vercel's anycast IP)
#    Or CNAME: cname.vercel-dns.com
```

**Pros**: Zero config, auto-deploy, edge network, serverless functions for API routes.

---

## Option B: Railway (Alternative)

Railway also auto-detects Next.js and handles serverless functions.

```bash
# 1. Go to railway.app → New Project → Deploy from GitHub repo

# 2. Railway auto-detects Next.js and builds

# 3. Add environment variables in Railway dashboard

# 4. Generate domain or connect custom domain
```

---

## Option C: Hetzner VPS (Full Control)

For self-hosted deployment with full control:

```bash
# On your VPS
cd /var/www/whitemagic-site

# Clone or pull latest
git pull origin main

# Install and build
npm install
npm run build

# Run with PM2
pm2 start "npm start" --name whitemagic-site
pm2 save
pm2 startup

# Or use the systemd service template from the main repo:
# /home/lucas/Desktop/WHITEMAGIC/docs/deploy/HETZNER_DEPLOY.md
```

**Caddy reverse proxy**:
```
whitemagic.dev {
    reverse_proxy localhost:3000
}
```

**Nginx reverse proxy**:
```
server {
    listen 80;
    server_name whitemagic.dev;
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## Option D: Static Export (Not Recommended)

⚠️ **Static export disables API routes, rewrites, and dynamic rendering.**

If you absolutely need a static site, you would need to:
1. Remove all `app/api/` routes
2. Remove `rewrites()` from `next.config.mjs`
3. Add `output: 'export'` to `next.config.mjs`
4. Build with `npm run build` → output to `out/`

**This is not the intended deployment mode for this site.**

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
# Check site loads (replace URL with your actual domain)
curl -s https://whitemagic.dev | head -20

# Check .well-known/agent.json (requires running server — API route)
curl -s https://whitemagic.dev/.well-known/agent.json | python3 -m json.tool | head -10

# Check pricing page
curl -s https://whitemagic.dev/pricing | grep -o '$[0-9,]*' | sort -u

# Check OpenGraph image
curl -sI https://whitemagic.dev/pricing/opengraph-image.png | head -5

# Verify API routes respond
curl -s https://whitemagic.dev/api/well-known/agent | python3 -m json.tool | head -5
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Build fails with TypeScript errors | Run `npm run typecheck` locally first |
| Build fails with "metadata export from use client" | Remove `export const metadata` from client components. Metadata must be in server components only. |
| API routes 404 on static host | Expected — this site requires a Node.js server. Deploy to Vercel, Railway, or VPS. |
| Images not loading | Verify `next.config.mjs` has appropriate image configuration for your host |
| Stripe links not appearing | Verify `.env.local` exists and URLs start with `https://` |
| `.next/` build output missing | Run `npm run build` — output goes to `.next/`, not `out/` |
| Server crashes on start | Check `PORT` env var isn't conflicting; verify Node.js 20+ |

---

## Quick Reference

```bash
cd /home/lucas/Desktop/whitemagic-site

# Dev
npm run dev

# Build (server app)
npm run build

# Start production server
npm start

# Deploy to GitHub (for Vercel/Railway auto-deploy)
git add -A && git commit -m "site: update" && git push origin main
```

---

## Current Blockers (as of 2026-06-05)

1. **No Stripe account**: Payment links fall back to `/contact` forms. Site is functional.
2. **No deployed server**: Site builds successfully but is not live. Pick a host from Option A–C and deploy.
3. **No DNS**: `whitemagic.dev` needs A record or CNAME pointed at your deployment target.
4. **No environment variables**: `.env.local` is not committed (correctly — it's gitignored). Add env vars in your hosting dashboard.

The shortest path to live: **Vercel** (connect GitHub repo, auto-deploy, 5 minutes).
