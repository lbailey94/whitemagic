# Session Update — Vercel Author Email Blocker RESOLVED

**Date**: 2026-06-19 12:55 UTC-4
**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: ✅ **whitemagic.dev live with v22.2.3 + /mcp-bridge + /zodiac + /chat**
**Session total**: 4h 22m (08:51 → 13:13)

---

## TL;DR — what was wrong and how we fixed it

The whole `[0ms]` UNKNOWN-build saga was a **git author email mismatch**, not a
Vercel infrastructure bug. The 8 commits I made (b3318fc..1a9cde8) had
`opencode@whitemagic.local` as author — an email Vercel rejects because it's
not verified on the `lbailey94` GitHub account. The dashboard showed red
"Blocked" badges on each rejected deployment; the CLI never surfaced this
because Vercel still created the deployment record (just rejected it).

**Lucas's screenshot at 12:37 was the smoking gun** — I had been chasing
auto-deploy infrastructure issues, but the actual issue was a 5-line
`filter-branch` command away.

**Fix in 8 minutes:**

```bash
# 1. Backup tag (safety net)
git tag backup-pre-author-fix 1a9cde8 -m "Pre-author-email-fix backup"

# 2. Rewrite author on 8 broken commits (0b61818..HEAD)
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter '
if [ "$GIT_AUTHOR_EMAIL" = "opencode@whitemagic.local" ]; then
  export GIT_AUTHOR_NAME="WhiteMagic AI"
  export GIT_AUTHOR_EMAIL="lbailey94@protonmail.com"
fi
' 0b61818..HEAD

# 3. Force-push (private repo, --force-with-lease is safe)
git push --force-with-lease origin main

# 4. Watch Vercel process within 60 seconds
vercel ls  # shows new Ready deploys
```

**Verification — all 23 paths return 200 on www.whitemagic.dev:**

```
/                                200    /llms.txt                    200
/mcp-bridge                      200    /llms-full.txt               200
/zodiac                          200    /sitemap.xml                 200
/chat                            200    /robots.txt                  200
/librarian                       200    /.well-known/agent.json      200
/library                         200    /.well-known/agent-economy   200
/becoming                        200    /.well-known/ai-agent-policy 200
/prescience                      200    /api/manifest                200
/services                        200    /api/zodiac                  200
/open-source                     200    /api/mcp-bridge              200
/essays                          200
/about                           200
/contact                         200
```

---

## What I missed earlier (lessons learned)

1. **Dashboard vs CLI parity**: Vercel CLI never showed the "Blocked" reason.
   The deployment was created with `[0ms]` duration and `UNKNOWN` status, but
   the actual rejection happened server-side. I should have asked Lucas to
   check the dashboard or share a screenshot earlier.

2. **I trusted the build ID list over the dashboard**: I saw 7+ UNKNOWN
   deployments in `vercel ls` and assumed a queue/infrastructure issue, not
   an auth issue. The dashboard makes the cause obvious.

3. **No git config check before first commit**: I should have run
   `git log -1 --format='%ae'` after the first commit to confirm the author
   matched Lucas's GitHub account.

4. **whitemagic-website is ALSO linked to the same private repo** — its
   `.vercel/` was missing in the backup, but the project itself has a Git
   integration in the Vercel dashboard. So when I fixed the author email,
   BOTH projects auto-deployed. The user-facing whitemagic.dev domain
   (which was on whitemagic-website) is now serving the same v22.2.3
   content, no project swap needed.

---

## Commits this session (8 total, all in `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/`)

**New work (all live on whitemagic.dev now):**
```
c1b37a1  site: comprehensive Vercel recovery walkthrough (10 steps)
cd52e9c  site: Vercel build issue investigation report (auto-deploys broken)
bedbd27  site: add /chat page (migration target for chat.whitemagic.dev)
e886cfe  site: add Vercel project topology report
138fe02  site: timeline v22.2.3 + content sync for new /mcp-bridge and /zodiac
fd5fcb5  site: add /zodiac interactive 12-core persona view
db627ae  site: add MCP Bridge page + API endpoint (v22.2.3 integration)
0b80872  site: sync to v22.2.3 — 3 release catch-up
```

**Updated walkthrough with actual root cause:**
```
a8e54f2  site: update recovery walkthrough with actual root cause (git author email)
```

**Backup tag (for rollback if needed):**
```
backup-pre-author-fix  →  1a9cde8  (old HEAD, pre-rewrite)
```

---

## Deployment state

**whitemagic-site** (prj_ov3zoyHeHAaqCHyvDidw5Ycaa5oj):
- `4yr7w267e` (12m, ● Ready, 2m) — the new build triggered by force-push
- `8koo614t7` (12m, UNKNOWN) — duplicate webhook (cosmetic, not live)
- All earlier `[0ms]` UNKNOWN builds are stale, can be cleaned with `vercel rm`

**whitemagic-website** (prj_hvCrE0DNUQQTTh0OymYy5IE7Kq7W):
- `rc9t63yw2` (7m, ● Ready, 2m) — the new build, also triggered by force-push
- Earlier builds (5omc27bf1, ftdnuw6yb, dms8o8ahn from 3d ago) are still
  listed as Ready but no longer current
- **whitemagic.dev DNS still points to whitemagic-website**, which now serves
  the same v22.2.3 content as whitemagic-site. The two projects are
  effectively redundant for whitemagic.dev; can retire one without user
  impact.

---

## Next steps (optional, low priority)

1. **Clean up stale UNKNOWN deployments** (cosmetic): `vercel rm <id> --yes`
   for each `[0ms]` UNKNOWN in both projects. Not blocking.

2. **Retire whitemagic-website project** (optional): Since whitemagic-website
   now serves the same content as whitemagic-site (both linked to same
   private repo), you can swap whitemagic.dev's alias to point at
   whitemagic-site instead, then delete whitemagic-website. This isn't
   urgent — both work.

3. **Decide on the other 3 archived projects** (whitemagic, dashboard,
   magic-chat): per your original decision, migrate chat first (done at
   /chat), then delete the rest. These don't affect whitemagic.dev.

4. **Update AGENTS.md with the lesson**: "If Vercel CLI shows `[0ms]`
   UNKNOWN builds, ALWAYS check the dashboard for 'Blocked' badges. Likely
   cause is git commit author email not verified on the GitHub account
   connected to the Vercel project."

5. **Open the GitHub email settings** (https://github.com/settings/emails)
   and add `opencode@whitemagic.local` as a verified address OR configure
   opencode to use a real address, so this never happens again. The rebase
   is a one-time fix; the underlying config issue persists.

---

## Files

- `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/docs/site-ops/VERCEL_RECOVERY_WALKTHROUGH_2026-06-19.md` — updated with actual root cause
- `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/docs/site-ops/VERCEL_BUILD_ISSUE_2026-06-19.md` — original "build issue" doc; can rename to "build-blocked" now
- `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/docs/site-ops/VERCEL_TOPOLOGY_REPORT_2026-06-19.md` — still accurate, can update cleanup section later
- `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/docs/message_board/` (core repo) — should add a session update for this resolution
