# Vercel Project Topology Report

**Date**: 2026-06-19
**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: Investigation complete, needs your decision

---

## Executive Summary

Your Vercel org `lbailey94s-projects` has **5 projects**, not just 1.
The local git repo at `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site` is
connected to a Vercel project called `whitemagic-site` that has **no
custom domain** — so `git push` builds go to
`whitemagic-site.vercel.app` (works!) but **NOT to `whitemagic.dev`**.

`whitemagic.dev` is owned by a **different Vercel project** called
`whitemagic-website` (203d old, framework preset "Other", output
`public/`) that hasn't been deployed to in 3 days. Its source repo is
unknown — it might be a separate spinoff (like
`whitemagic-frontend`/`whitemagic-site-git-backup`/etc.),
an older branch, or a GitHub integration that was disconnected.

Until we figure out where `whitemagic-website`'s source is, the 4
commits I just pushed to `lbailey94/whitemagic-site-private` will
build and serve on `whitemagic-site.vercel.app` (working) but won't
reach `whitemagic.dev` (still 3d-old).

---

## The 5 Vercel projects

| Project | ID | Type | Age | URL | Source |
|---------|----|----|-----|-----|--------|
| `whitemagic-site` | prj_ov3zoyHeHAaqCHyvDidw5Ycaa5oj | Next.js | 24.x | `whitemagic-site.vercel.app` | **This repo** (git push) |
| `whitemagic-website` | prj_hvCrE0DNUQQTTh0OymYy5IE7Kq7W | Other (static) | 203d | `whitemagic-website-lbailey94s-projects.vercel.app` + **whitemagic.dev** | **UNKNOWN** |
| `dashboard` | prj_mbhZdPNduQACg2HtWqi9A5jyC1Cn | Next.js | 24.x | `dashboard-self-kappa-94.vercel.app` | `whitemagic-app/hub` or `nexus`? |
| `magic-chat` | prj_dlE5v6I4qjic2U60l0vr6qKhibIu | Next.js | 24.x | `chat.whitemagic.dev` | `whitemagic-app/shell`? |
| `whitemagic` | prj_aaDFR7B4PnMF0QAvtACwQwk6xZMX | Other (static) | 22.x | `whitemagic-lbailey94s-projects.vercel.app` | **UNKNOWN** (very old) |

---

## Where the projects source from

| Project | Known source | Notes |
|---------|--------------|-------|
| `whitemagic-site` | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site` (this repo) | Auto-deploys on `git push origin main` to `whitemagic-site.vercel.app` |
| `whitemagic-website` | UNKNOWN | Serves `whitemagic.dev`. Last deploy June 16, 2026 (3d ago, before v22.2.3 work). Framework "Other" + output `public/` = likely a static export of an older Next.js build, or a completely separate static project |
| `dashboard` | Probably `whitemagic-app/hub` or `whitemagic-app/nexus` | Per `whitemagic-app/AGENTS.md`, these are Tauri+React desktop apps. If dashboard is the web version, source could be `whitemagic-app/shell` |
| `magic-chat` | Probably `whitemagic-app/shell` | Per same AGENTS, shell is the lightweight web dashboard. 31d old deploy |
| `whitemagic` | UNKNOWN | 32d old, very stale, framework "Other". Likely a long-abandoned experiment |

---

## Local git repos (potential sources)

| Repo | Remote | Last commit | Notes |
|------|--------|-------------|-------|
| `~/Desktop/WHITEMAGIC` | `whitemagic-ai/whitemagic` (public) | 13b57a4 (today) | Core Python package |
| `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site` | `lbailey94/whitemagic-site-private` | 53a03c4 (today) | This site repo, Next.js |
| `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site-git-backup` | (no remote) | 5a78166 (older) | Backup, no remote |
| `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic_old_git_backup_20251118_113851` | (no remote) | (empty) | Old backup, no remote |

**No other git repo has `whitemagic.dev` as a known remote.**

---

## Vercel Hobby plan rules (per site AGENTS.md §2)

- **No commercial activity** — no dollar prices
- **No high-traffic endpoints** — static or low-cost API
- **Self-host anything expensive** — MCP server, x402, Discord bot should be on Hetzner

Multiple "Other" framework Vercel projects serving static exports is
**unusual** for a Vercel Hobby account. The `whitemagic` (32d) and
`whitemagic-website` (203d) projects predate the 100 GB/month Hobby
egress cap (introduced 2025). If they're still serving real traffic
at production scale, they may be exceeding the cap.

---

## What's likely true

Looking at the patterns:
1. **`whitemagic-website`** is probably an **older Next.js project
   that was set up as "Other"** with `output: 'export'` (static
   export). The chunks on the live site (`app/page-1ec830e770a91368.js`)
   look like Next.js, not pure static. Someone may have manually
   configured a `next export` workflow.
2. **`whitemagic`** is probably a **long-abandoned static export**
   of an even older site version.
3. **`dashboard` and `magic-chat`** are likely the `whitemagic-app/hub`
   and `whitemagic-app/shell` projects, but I can't confirm without
   investigating those repos.

---

## The fix (proposed, needs your decision)

Per your preference for option 4 (investigate first, then fix):

### Step 1: Investigate `whitemagic-website` source
1. **Check Vercel dashboard** → `whitemagic-website` project →
   Settings → Git → "Connected Git Repository"
2. If a repo is listed, that repo is the source
3. If no repo, check the Build/Deploy logs for clues (last build
   on June 16 was triggered by something)
4. Check if there are GitHub Actions / webhooks in the
   `lbailey94/whitemagic-site-private` or `lbailey94/whitemagic-frontend`
   (if it exists) repos

### Step 2: Consolidate (recommended)
1. **Point `whitemagic.dev` to `whitemagic-site`** (the project
   this repo deploys to). One Vercel dashboard click under
   Settings → Domains.
2. **Delete or archive `whitemagic-website`** (203d old, redundant)
3. **Delete or archive `whitemagic`** (32d old, likely abandoned)
4. Keep `dashboard` and `magic-chat` (active, distinct purposes)

### Step 3: Update git integrations
1. Make sure `whitemagic-site` has a GitHub integration pointing to
   `lbailey94/whitemagic-site-private`
2. Disable any Vercel auto-deploys from old spinoffs

### Step 4: Verify
1. `git push` from local repo
2. Vercel auto-deploys to `whitemagic-site`
3. `whitemagic.dev/mcp-bridge` returns 200 with the new content
4. `whitemagic.dev/zodiac` returns 200 with the new content

---

## What I need from you

1. **Login to Vercel dashboard** → `whitemagic-website` → Settings
   → Git to see what repo (if any) it's connected to
2. **Decide**: consolidate to `whitemagic-site` (recommended) or
   find/fix the source for `whitemagic-website`
3. **Optional**: I can write a quick Vercel admin script once you
   confirm the target project, but I should not touch Vercel
   project topology without your explicit approval (per AGENTS.md §2
   "Vercel Hobby plan rules")

---

## Why this matters

The 4 commits I just pushed are **code-ready** for `whitemagic.dev`:
- 17 files updated for v22.2.3 sync
- New `/mcp-bridge` page + `/api/mcp-bridge` endpoint
- New `/zodiac` interactive page
- 2 new timeline entries
- All tests green, all docs synced

The **only** thing preventing them from being live is the
Vercel project topology. Once we fix the DNS, the site catches up
in 2-3 minutes (Vercel build time) automatically on next push.
