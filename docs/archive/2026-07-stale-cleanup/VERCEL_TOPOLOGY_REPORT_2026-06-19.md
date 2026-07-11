# Vercel Topology Report — 2026-06-19 (FINAL)

**Date**: 2026-06-19 13:30 UTC-4
**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: ✅ **CLEAN STATE** — single canonical project, all 3 custom domains live, 4 archived projects deleted, 15 stale deployments cleaned

---

## TL;DR

The 5-project Vercel mess is resolved. There is now **one** project, `whitemagic-site`, that owns all 3 custom domains (`whitemagic.dev`, `www.whitemagic.dev`, `chat.whitemagic.dev`). The 4 archived projects (whitemagic, dashboard, magic-chat, whitemagic-website) are deleted.

---

## Final state

```
$ vercel project ls

  Project Name      Latest Production URL                Updated   Node Version
  whitemagic-site   https://whitemagic-site.vercel.app   5m        24.x
```

**One project. That's it.**

## Custom domain ownership (FINAL)

| Domain | Project | Status |
|---|---|---|
| `whitemagic.dev` | `whitemagic-site` | ✅ 200 (apex → www redirect) |
| `www.whitemagic.dev` | `whitemagic-site` | ✅ 200 (canonical) |
| `chat.whitemagic.dev` | `whitemagic-site` | ✅ 200 |
| `app.whitemagic.dev` | (deleted) | 404 (was on `whitemagic` project, retired) |
| `dashboard-self-kappa-94.vercel.app` | (deleted) | 404 (was on `dashboard` project, retired) |

## Live production verification

**23/23 paths return 200 on `www.whitemagic.dev`:**

| Path | Status |
|---|---|
| `/` `/mcp-bridge` `/zodiac` `/chat` `/librarian` `/library` `/becoming` `/prescience` `/services` `/open-source` `/essays` `/about` `/contact` | 13 pages ✓ |
| `/api/manifest` `/api/zodiac` `/api/mcp-bridge` | 3 APIs ✓ |
| `/llms.txt` `/llms-full.txt` `/sitemap.xml` `/robots.txt` | 4 discovery ✓ |
| `/.well-known/agent.json` `/.well-known/agent-economy.json` `/.well-known/ai-agent-policy` | 3 A2A ✓ |

**4/4 paths return 200 on `chat.whitemagic.dev`:** `/`, `/mcp-bridge`, `/zodiac`, `/chat`

## Current production deploy

**`whitemagic-site-dfizuyq0s-lbailey94s-projects.vercel.app`**
- Build SHA: `2d94687` (current HEAD, session update)
- Author: `WhiteMagic AI <lbailey94@protonmail.com>`
- Status: `● Ready`
- Duration: 2m
- Created: 2026-06-19 13:21 UTC-4

---

## What was done (in order)

### Step 1: Configured opencode to use correct git identity
- Wrote `~/.config/opencode/plugin/git-identity.ts` — a TypeScript plugin
  that intercepts every `git commit` bash invocation and injects
  `-c user.name="WhiteMagic AI" -c user.email="lbailey94@protonmail.com"`
  flags, plus unsets any `GIT_AUTHOR_*` / `GIT_COMMITTER_*` env vars
  that could override the `-c` flags.
- Registered in `~/.config/opencode/opencode.jsonc` as
  `plugin: ["./plugin/git-identity.ts"]`.
- 11/11 unit tests pass.
- **You must restart opencode for the plugin to load.**

### Step 2: Cleaned up 15 stale BLOCKED deployments
- 7 BLOCKED deploys in whitemagic-site (all from the
  `opencode@whitemagic.local` author block).
- 9 BLOCKED deploys in whitemagic-website (same cause).
- All removed via `vercel rm https://<url> --yes`.

### Step 3: Triggered fresh build of whitemagic-site
- Discovered the existing whitemagic-site Ready deploys were all
  **redeploys of the OLD blocked commit 53a03c47**, not the new
  history. The force-push hadn't triggered a fresh build because
  whitemagic-site's GitHub integration was disconnected.
- Ran `vercel deploy --prod` from local to get a fresh build of HEAD
  `2d94687`. Result: `whitemagic-site-dfizuyq0s` (Ready, 2m).

### Step 4: Swapped 3 custom domains to whitemagic-site
- `whitemagic.dev` → `whitemagic-site-dfizuyq0s`
- `www.whitemagic.dev` → `whitemagic-site-dfizuyq0s`
- `chat.whitemagic.dev` → `whitemagic-site-dfizuyq0s`
- Vercel auto-reassigned the old aliases; no DNS downtime.

### Step 5: Deleted 4 archived projects
- `whitemagic` (oldest, no public users)
- `dashboard` (no public users, 30d stale)
- `magic-chat` (replaced by `/chat` on whitemagic-site)
- `whitemagic-website` (now redundant with whitemagic-site)
- All via `printf 'y\n' | vercel project remove <name>`

---

## Lessons learned (add to AGENTS.md / onboarding)

1. **Vercel CLI never shows "Deployment Blocked"** — the dashboard does.
   If you see `[0ms]` UNKNOWN builds, check the dashboard first.
2. **GitHub email must be verified on the GitHub account** that owns the
   Vercel project's Git integration. Unverified emails are silently
   rejected by Vercel.
3. **`git filter-branch` to rewrite commit author** is the canonical fix
   for this class of bug. Backup tag first, force-push with
   `--force-with-lease` to a private repo, and within 60s Vercel
   auto-deploys.
4. **Force-push alone doesn't always trigger a fresh build** if the
   project's GitHub integration is broken or disconnected. Fall back to
   `vercel deploy --prod` from the local working tree.
5. **`yes` piped to `vercel project remove` causes an infinite loop**
   (the CLI re-prompts on every internal resource). Use
   `printf 'y\n' | vercel project remove <name>` instead.
6. **Always check the deployment's `meta.githubCommitSha`** — if it
   doesn't match your expected commit, the build is from a stale
   redeploy, not a fresh source. Use `vercel deploy --prod` to force a
   new build.
7. **Aliases can be swapped without DNS downtime** — Vercel
   auto-reassigns when you `vercel alias set` a new deployment URL to
   an already-aliased custom domain.

---

## Files (this repo)

- `lib/facts.ts` — v22.2.3, all numbers current
- `app/mcp-bridge/page.tsx` + `lib/data/mcp-bridge.ts` + `app/api/mcp-bridge/route.ts` — v22.2.3 bridge catalog
- `app/zodiac/page.tsx` + `lib/data/zodiac-signs.ts` — 12-core interactive view
- `app/chat/page.tsx` — Magic Chat migration target (uses `<LibrarianChat />`)
- `app/sitemap.ts` — includes all 4 new pages
- `public/llms-full.txt` — discovery table updated
- `docs/site-ops/VERCEL_RECOVERY_WALKTHROUGH_2026-06-19.md` — recovery recipe with actual root cause
- `docs/site-ops/VERCEL_BUILD_ISSUE_2026-06-19.md` — original "build issue" investigation
- `docs/site-ops/VERCEL_TOPOLOGY_REPORT_2026-06-19.md` — this file (the original 5-project investigation; this update supersedes it)
- `docs/site-ops/SESSION_UPDATE_VERCEL_RESOLVED_2026-06-19.md` — final session update

## Files (Vercel infrastructure, not in repo)

- `whitemagic-site` — single canonical project
- 3 production aliases: `whitemagic.dev`, `www.whitemagic.dev`, `chat.whitemagic.dev`
- Latest production deploy: `whitemagic-site-dfizuyq0s` (build 2d94687)
