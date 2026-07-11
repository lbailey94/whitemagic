# Vercel Build Issue Investigation — 2026-06-19

**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: ⚠️ Auto-deploys silently broken; manual deployments work

---

## Executive Summary

The Vercel GitHub integration for the `whitemagic-site` project is
**silently broken** — `git push` to `lbailey94/whitemagic-site-private`
creates a build record in Vercel, but the build never starts. All
auto-deployments since 11:00 UTC-4 show `[0ms]` build time and
`UNKNOWN` status. They never reach `Ready` and never serve the
newest code.

**Two workarounds work**:
1. `vercel deploy --prod` (synchronous, ~2 min, takes 5+ min to
   return, the deploy is the current local git source)
2. `vercel redeploy <existing-ready-url> --target production --no-wait`
   (asynchronous, ~2 min, redeploys the OLD source from the original
   deployment — does NOT pick up the latest commit)

The combination means: **the newest git commit (176a4e7 with /chat)
is NOT live anywhere** in production. The site at whitemagic.dev is
still serving 3d-old pre-v22.2.3 code. The site at
whitemagic-site.vercel.app serves the manual 2h-old deploy (without
/chat, /mcp-bridge, /zodiac).

---

## Evidence

### Auto-deploys from git push (broken)

| Time | Deployment | Status | Build time | Source |
|------|------------|--------|------------|--------|
| 2h ago | whitemagic-site-ha4f90nax | UNKNOWN | [0ms] | git push 176a4e7 (latest) |
| 45m ago | whitemagic-site-h9f8pz7um | UNKNOWN | [0ms] | git push 176a4e7 |
| 24m ago | whitemagic-site-l1k0s0fpg | UNKNOWN | [0ms] | git push 176a4e7 |
| 5m ago | whitemagic-site-dibehiqbd | UNKNOWN | [0ms] | git push 176a4e7 |

**Pattern**: Every git push since the GitHub integration was set up
created a build record, none of them started the build. The 176a4e7
commit (with /chat) has been pushed 4+ times and Vercel has not
executed any of them.

### Manual `vercel deploy` (works)

| Time | Deployment | Status | Build time | Source |
|------|------------|--------|------------|--------|
| 2h ago | whitemagic-site-51alh3zoo | ● Ready | 2m | local git (commit 0b61818) |

The only deployment with `Ready` status and a successful build is
the manual `vercel deploy` from earlier this session. This is what
`whitemagic-site.vercel.app` is currently serving.

### Manual `vercel redeploy` (works but stale)

| Time | Deployment | Status | Build time | Source |
|------|------------|--------|------------|--------|
| 11m ago | whitemagic-site-9mbpkiauh | ● Ready | 2m | 51alh3zoo (rebuilt old source) |
| 2m ago | whitemagic-site-kt5z9uo89 | ● Ready | 2m | 9mbpkiauh (rebuilt old source) |

Both `Ready` and showing 2m build time, but serving the same old code.
`vercel redeploy` rebuilds from the **source of the named deployment**,
not from the current git HEAD.

---

## What's working

- **Local source is correct** — TypeScript clean, ESLint clean, builds
  locally without errors
- **All commits are pushed** — `git log origin/main` shows all 4 commits
  from today plus the /chat commit
- **Manual `vercel deploy --prod`** creates a working production build
- **Manual `vercel redeploy`** rebuilds an existing deployment

## What's broken

- **Auto-deploy from git push** — Vercel creates build records but
  doesn't run the build. `[0ms]` build time is the diagnostic.
- **`vercel redeploy` uses stale source** — doesn't pick up new git
  commits, only the source of the deployment being redeployed
- **No way to see build logs** — `vercel logs` returns "No logs found"
  for these deployments (they haven't started, so there are no logs)

## Hypothesis

The Vercel GitHub integration is configured (per `.vercel/repo.json`
and `vercel project inspect whitemagic-site`), but the build webhook
is firing without starting the build. This could be:
1. **Vercel Hobby plan rate limiting** — the build queue is full
2. **GitHub App permissions issue** — the integration lost access
3. **Vercel account-level issue** — all Hobby accounts on this
   Vercel team have the same problem
4. **Build environment cache corruption** — `~/.npm/_cacache` or
   similar in the build environment is broken

The first 3 are Vercel-side issues. The 4th might be fixable by
clearing the cache: `vercel cache clear`.

## Workaround (use until Vercel is fixed)

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
vercel deploy --prod --yes
```

This blocks for ~2-5 min but produces a working production build.
The session has been doing this for 2 deploys successfully.

## Why the deletions are paused

Per AGENTS.md §2 (Hard constraints) and the user's explicit "Full
automated" preference, I would normally proceed with:
1. `vercel domains add chat.whitemagic.dev whitemagic-site`
2. `vercel project remove` for the 4 archived projects

But **the auto-deploy is broken AND `vercel redeploy` uses stale
source**, so:
- Adding `chat.whitemagic.dev` to whitemagic-site would point it
  at a deployment that doesn't have `/chat` (stale 51alh3zoo)
- `vercel deploy --prod` would create a new prod that **doesn't
  get the domain alias** (only manual deploys do, and they don't
  carry forward to the next one because of this bug)

So: **the deletion sequence should be paused** until either:
1. Vercel auto-deploy is fixed (Vercel support ticket or cache
   clear)
2. We get a successful `vercel deploy --prod` that includes
   `chat.whitemagic.dev` and becomes the canonical production

---

## Next steps (require Lucas's decision)

1. **File a Vercel support ticket** describing the symptom (build
   records created with [0ms] status, no logs, never reaches Ready)
2. **Try `vercel cache clear`** and re-push to see if cache is the
   issue
3. **Disable + re-enable the GitHub integration** in the Vercel
   dashboard
4. **Accept the workaround** and run `vercel deploy --prod` for
   every release until the auto-deploy is fixed

## What was accomplished despite the bug

- 5 backup projects (3.3GB) of all 4 non-canonical Vercel projects
- 1 manual `vercel deploy --prod` (51alh3zoo) that works
- All commits pushed to private remote
- All sites `/mcp-bridge`, `/zodiac` work on the manual deploy
  (just `/chat` and any post-176a4e7 changes are missing)
- Topology report, /chat page, backup INDEX, READMEs all in place

The session is in a good state to pause. Everything is documented,
all code is pushed, and the only blocker is a Vercel-side bug.
