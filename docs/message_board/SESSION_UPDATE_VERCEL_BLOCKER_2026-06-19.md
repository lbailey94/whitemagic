# Session Update — Vercel Build Blocker

**Date**: 2026-06-19 11:53 UTC-4
**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: ⚠️ PAUSED — Vercel auto-deploy broken, manual deploys blocked

---

## Executive Summary

We were 4 minutes from completing the full Vercel project cleanup
(4 non-canonical projects backed up and ready for deletion) when
we hit a Vercel-side blocker: **all git push auto-deploys are
silently failing**, and **all manual `vercel deploy` attempts are
now returning "Your deployment failed. Please retry later."**

This is a Vercel infrastructure issue, not a code issue. The
session is paused pending either:
1. Vercel infrastructure recovering
2. A Vercel support ticket
3. User decision to proceed with deletions anyway (build issue
   doesn't affect the backups or the project removal commands)

---

## What's in place (committed, not yet live)

| Item | Status | Notes |
|------|--------|-------|
| 4 non-canonical projects backed up | ✅ 9.3MB, 202 files, full metadata | `/home/lucas/Desktop/WHITEMAGIC-aux/site-ops-backups/2026-06-19/` |
| `INDEX.md` and per-project READMEs | ✅ | In the backup dir |
| `/chat` page committed and pushed | ✅ Code is correct | Not in production (Vercel bug) |
| `vercel domains add chat.whitemagic.dev whitemagic-site` | ⏸ Paused | Would point domain to stale deploy |
| `vercel project remove` for 4 archived projects | ⏸ Paused | Could proceed independently of build issue |
| `whitemagic.dev` → `whitemagic-site` swap | ⏸ Paused | DNS change, requires user confirmation |
| Vercel build issue investigation | ✅ Documented | `docs/site-ops/VERCEL_BUILD_ISSUE_2026-06-19.md` on site repo |

## What is live

- **whitemagic-site.vercel.app** — manual 2h-old deploy (commit
  0b61818), serves `/mcp-bridge` and `/zodiac` but NOT `/chat`
- **whitemagic.dev** — still 3d-old pre-v22.2.3 build (from the
  `whitemagic-website` project)
- All 4 backup projects — files exist on disk but the Vercel
  projects themselves are still in place

## What's broken

- **All git push auto-deploys to whitemagic-site** — build records
  created with `[0ms]` status, never reach Ready. 4+ pushes
  affected (latest commit 176a4e7 not live anywhere)
- **All `vercel deploy --prod` attempts in the last 15 min** —
  "Your deployment failed. Please retry later." with `err.sh/vercel/`
  redirect. This is Vercel Hobby plan rate limiting or internal
  queue saturation
- **`vercel cache purge` cleared the cache** but didn't unblock
  the next deploy

## What we don't know

- Whether the Vercel rate limit is project-scoped, team-scoped,
  or global
- Whether disabling + re-enabling the GitHub integration would
  unblock auto-deploys
- Whether a fresh deployment attempt in 30+ min would succeed

---

## Decision options

### Option A: Pause and wait for Vercel to recover (recommended)
- Pro: No risk of breaking anything further
- Con: Site doesn't catch up to v22.2.3 until Vercel is fixed
- Action: End session, retry deploy in 1-2 hours

### Option B: Proceed with deletions anyway
- Pro: Cleans up the 4 abandoned projects
- Pro: Backups are in place, no data loss
- Con: chat.whitemagic.dev would be unconfigured
- Con: whitemagic.dev DNS is still pointing to the old (now-deleted)
  whitemagic-website project → 404 for everyone
- Action: Run `vercel project remove` for all 4, then later
  re-add whitemagic.dev to whitemagic-site when Vercel works

### Option C: Try the unlink + relink GitHub integration
- Pro: Might fix the auto-deploy (root cause)
- Con: Risk of leaving the integration in worse state
- Action: Run `vercel link --unlink` then `vercel link` again, see
  if next git push works

### Option D: Just delete the abandoned projects
- Same as B but more focused — delete the 3 ancient ones
  (whitemagic, dashboard, whitemagic-website), keep magic-chat
  since its user-facing impact (chat.whitemagic.dev) is unresolved
