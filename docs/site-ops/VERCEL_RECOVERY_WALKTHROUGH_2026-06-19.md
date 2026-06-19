# Vercel Recovery Walkthrough — Step by Step

**Date**: 2026-06-19 12:34 UTC-4
**Author**: opencode (minimax-m3) on behalf of Lucas
**Current state**: All backups complete, code committed and pushed, deployments blocked by Vercel infrastructure issue
**Time to complete**: ~15-25 minutes of Vercel dashboard work + 5 minutes of CLI

---

## TL;DR (executive summary)

1. **File a Vercel support ticket** about the `[0ms]` builds (1 min)
2. **Wait or retry** auto-deploy — if it starts working, skip to step 4
3. **Try re-linking the GitHub integration** if step 2 doesn't help (3 min)
4. **Point whitemagic.dev to whitemagic-site** (1 min)
5. **Add chat.whitemagic.dev to whitemagic-site** (1 min)
6. **Push a small change to trigger a fresh auto-deploy** (1 min, then wait)
7. **Verify the new deployment** is serving v22.2.3 with all new pages (2 min)
8. **Delete the 4 archived projects** (whitemagic-website, whitemagic, dashboard, magic-chat) — one at a time, verify after each (10 min)

**Total**: 15-25 min of Vercel dashboard work, mostly waiting for deploys to complete.

**If you want to do this in a different order**: the critical path is
**whitemagic.dev → whitemagic-site swap** (step 4) before
**deletions** (step 8), because the deletions will 404 whitemagic.dev
until the swap is done. The chat.whitemagic.dev swap (step 5) is
optional and lower priority.

---

## Background — what you're working with

### Current project topology (from your Vercel account)

| Project | ID | Last deploy | Aliases | Frame | Plan role |
|---------|----|----|---------|-------|-----------|
| `whitemagic-site` | `prj_ov3zoyHeHAaqCHyvDidw5Ycaa5oj` | 41m ago (stuck) | whitemagic-site.vercel.app (preview only) | Next.js | **NEW canonical** — auto-deploys from `lbailey94/whitemagic-site-private` |
| `whitemagic-website` | `prj_hvCrE0DNUQQTTh0OymYy5IE7Kq7W` | 41m ago (3d-old) | whitemagic.dev, www.whitemagic.dev | Other (static) | **TO DELETE** — was serving whitemagic.dev from old Next.js export |
| `dashboard` | `prj_mbhZdPNduQACg2HtWqi9A5jyC1Cn` | 30d ago | dashboard-self-kappa-94.vercel.app | Next.js | **TO DELETE** — ancient, no public users |
| `magic-chat` | `prj_dlE5v6I4qjic2U60l0vr6qKhibIu` | 31d ago | chat.whitemagic.dev | Next.js | **TO DELETE** — replaced by /chat on whitemagic-site |
| `whitemagic` | `prj_aaDFR7B4PnMF0QAvtACwQwk6xZMX` | 32d ago (216d) | app.whitemagic.dev | Other (static) | **TO DELETE** — ancient, original web dashboard |

### What each project is "for" in plain English

- **`whitemagic-site`** is your new home. All 7 of today's commits
  go here. The code on disk right now has `/mcp-bridge`, `/zodiac`,
  `/chat`, the v22.2.3 timeline entries, and the v22.2.3 numbers in
  facts.ts. Auto-deploys to this project are silently broken.

- **`whitemagic-website`** was the old project that served
  whitemagic.dev. It's from November 2025, the "Other" framework
  means it was probably a static export. Last successfully deployed
  June 16 (3 days ago, before any of today's work). You already
  disconnected the git source on 6/19, so it's not auto-deploying
  anymore — just serving its last build.

- **`whitemagic`** is the original project from November 2025, 32 days
  old and 216 days since the last deploy. The "Root Directory:
  dashboard" in the project settings suggests it was a Tauri/React
  web dashboard preview. No git integration visible. Very stale.

- **`dashboard`** is a Next.js project (not "Other") from November
  2025, 30 days since the last deploy. No public URL or domain,
  probably a stale dashboard preview.

- **`magic-chat`** is the Next.js project that served
  `chat.whitemagic.dev`. 31 days since last deploy. **This is the
  only one with a currently-active public surface besides
  whitemagic.dev.** Before deleting it, you need a plan for
  `chat.whitemagic.dev` — either migrate to your new `/chat` route
  on whitemagic-site (recommended), or accept the URL will 404.

### Custom domains registered in your Vercel account

- `whitemagic.dev` — currently assigned to `whitemagic-website`
- `www.whitemagic.dev` — currently assigned to `whitemagic-website` (alias)
- `chat.whitemagic.dev` — currently assigned to `magic-chat`
- `app.whitemagic.dev` — currently assigned to `whitemagic`
- `dashboard-self-kappa-94.vercel.app` — assigned to `dashboard` (Vercel subdomain, not custom)

Nameservers: `ns1.vercel-dns.com` / `ns2.vercel-dns.com` (Vercel-managed)
Registrar: Third Party (the actual registrar is Namecheap or similar; you can see in Vercel dashboard)

---

## Step 1: File a Vercel support ticket (1 min)

This isn't strictly required to proceed, but it documents the issue
with Vercel and gives you a paper trail. The auto-deploy being
broken is a real Vercel problem, not a project problem, and the only
real fix is Vercel infrastructure-side.

### How to file

1. Go to https://vercel.com/help
2. Sign in as `lbailey94`
3. Click "Contact Support" or "Submit a ticket"
4. Select category: **Build & Deploy**
5. Subject: `Hobby plan: git push auto-deploys stuck at [0ms] status, never reach Ready`
6. Severity: **Medium** (not blocking your work, but you want it fixed)

### Ticket body (copy-paste ready)

```
Team: lbailey94s-projects
Project ID: prj_ov3zoyHeHAaqCHyvDidw5Ycaa5oj (whitemagic-site)

Since approximately 2026-06-19 11:00 UTC-4, every git push to
github.com/lbailey94/whitemagic-site-private has created a
Vercel build record that never executes. The deployments stay at
"status: UNKNOWN" and "build time: [0ms]" indefinitely. I've
pushed 7+ commits and all 7 created non-executing build records.

Steps already tried:
- vercel cache purge --yes  (succeeded but didn't unblock)
- vercel deploy --prod --yes  (first 2 calls worked, taking ~2 min
  each. Subsequent calls after 11:50 UTC return
  "Your deployment failed. Please retry later.")
- vercel deploy --prod --yes --no-wait  (same failure)
- vercel redeploy <existing-Ready-url> --target production --no-wait
  (succeeds in 2 min but uses the OLD source of the named
  deployment, not the current git HEAD)

What works:
- vercel redeploy of an existing deployment, but it's a fresh
  build of the OLD source code, not the current main branch

What doesn't work:
- Any git push to main since ~11:00 UTC
- Any fresh vercel deploy --prod (returns 4xx error)
- vercel logs returns "No logs found" for the stuck deployments
  (they haven't started, so no logs exist)

Hobby plan, whitemagic-site project, Next.js framework. The Vercel
GitHub integration is configured (vercel link --repo shows
lbailey94/whitemagic-site-private connected). Node version 24.x.
Region iad1.

Expected behavior: a git push to main should trigger a build
within seconds, with build time progressing from 0 to ~2 min,
ending in Ready status.

Actual behavior: build records created, no build execution,
stays at [0ms] UNKNOWN indefinitely.

Thank you.
```

7. Submit. Vercel support typically responds in 1-3 business days
   for Hobby tier.

### If you want to skip this

It's a nice-to-have but not blocking. Skip if you want to keep
moving.

---

## Step 2: Try a fresh git push (5-15 min wait)

Sometimes Vercel rate limits clear on their own. Let's see if a
fresh `git push` triggers a build now.

### How

From the site repo:

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
# Make a small change
echo "" >> docs/site-ops/.last-deploy-test
git add docs/site-ops/.last-deploy-test
git commit -m "test: trigger fresh auto-deploy"
git push origin main
```

### Watch

```bash
# In another terminal:
vercel ls
```

### What you should see

- Within 1-2 min: a new deployment appears with `Status: Building`
  and a duration of `Xs` counting up
- Within 2-3 min: `Status: Ready` and your new content is live

### What you'll see if it's still broken

- New deployment with `Status: UNKNOWN` and `[0ms]` build time
- Same as before

### If it works, skip to Step 4

If it doesn't work, continue to Step 3.

---

## Step 3: Re-link the GitHub integration (3 min)

The GitHub integration might be in a stuck state. Re-linking can
sometimes unblock it.

### How (in the Vercel Dashboard)

1. Go to https://vercel.com/dashboard
2. Click on the **`whitemagic-site`** project
3. Click **Settings** in the top nav
4. Click **Git** in the left sidebar
5. You'll see "Connected Git Repository" — should show
   `lbailey94/whitemagic-site-private`
6. Click **Disconnect** (you'll get a confirmation dialog — confirm)
7. Wait 30 seconds for the disconnect to propagate
8. Click **Connect Git Repository**
9. Select **GitHub** as the provider
10. Search for `lbailey94/whitemagic-site-private` and select it
11. Confirm the connection

### How (via CLI, equivalent)

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site

# Check current state
vercel link --repo --yes

# Force re-link
rm -rf .vercel/repo.json
vercel link --repo --yes
```

### Test

```bash
# Make a small change
echo "" >> docs/site-ops/.last-deploy-test
git add docs/site-ops/.last-deploy-test
git commit -m "test: re-trigger auto-deploy after re-link"
git push origin main
```

### Watch

```bash
vercel ls
```

If you see a `Building` status within 1-2 min, the re-link worked.

### If still broken

The problem is at the Vercel infrastructure level. Wait for Vercel
support to respond, OR proceed with the deletions and use the
**manual workaround** below.

---

## Step 3.5: Manual workaround (if Steps 2 and 3 fail)

If auto-deploys are still broken, you can use the `vercel deploy`
command (which works for 1-2 deploys before hitting rate limits).

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
vercel deploy --prod --yes
```

This takes 2-5 min and pushes the **current** git source. The
deployment will become the new production.

**Important**: this approach has been rate-limited in this session
after a few attempts. If it returns "Your deployment failed. Please
retry later", wait 30-60 min and try again.

---

## Step 4: Point whitemagic.dev to whitemagic-site (1 min)

This is the critical step. Once done, anyone visiting
`https://whitemagic.dev` will see your new v22.2.3 site.

### Prerequisites

Before this step, you need a **production deployment of
whitemagic-site that is Ready**. If you don't have one, do Step 3.5
first.

### How (in the Vercel Dashboard)

1. Go to https://vercel.com/dashboard
2. Click on the **`whitemagic-website`** project (NOT
   whitemagic-site — this is the project that currently owns the
   domain)
3. Click **Settings** in the top nav
4. Click **Domains** in the left sidebar
5. Find `whitemagic.dev` in the domains list
6. Click the **three dots** (⋯) on the right
7. Click **Remove** (or "Transfer" if you see that option)
8. Confirm the removal
9. Click on **`whitemagic-site`** project
10. Click **Settings** → **Domains**
11. Type `whitemagic.dev` in the "Add Domain" input
12. Click **Add**
13. Repeat for `www.whitemagic.dev` (the www subdomain)
14. Both should show "Valid Configuration" within 30 seconds
    (Vercel sets the DNS automatically since you use Vercel nameservers)

### How (via CLI, equivalent)

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site

# Add the domain to whitemagic-site
vercel domains add whitemagic.dev whitemagic-site --yes
vercel domains add www.whitemagic.dev whitemagic-site --yes

# Remove from the old project (Vercel CLI doesn't have a clean
# "remove from project" command for domains — you need to do
# this in the dashboard or via the API)
```

### Verify

```bash
# Test in a browser (or curl)
curl -sL -o /dev/null -w "%{http_code}\n" https://whitemagic.dev/
curl -sL -o /dev/null -w "%{http_code}\n" https://whitemagic.dev/mcp-bridge
curl -sL -o /dev/null -w "%{http_code}\n" https://whitemagic.dev/zodiac
```

All three should return 200. If they return 200, **whitemagic.dev
is now serving v22.2.3 with all the new pages**.

### Note on www.whitemagic.dev

`www.whitemagic.dev` is a separate domain that already redirects
to `whitemagic.dev`. You only need to add `whitemagic.dev` —
Vercel handles the www redirect automatically when the apex domain
is added.

---

## Step 5: Add chat.whitemagic.dev to whitemagic-site (1 min)

This is the migration target for the old `magic-chat` project. After
this step, `https://chat.whitemagic.dev` will serve your new
`/chat` page.

### Prerequisites

Same as Step 4 — you need a Ready production deployment of
whitemagic-site that includes the `/chat` page (commit `176a4e7`
or later). If you don't have that yet, you need to do Step 3.5
first.

### How (in the Vercel Dashboard)

1. Go to https://vercel.com/dashboard
2. Click on the **`magic-chat`** project
3. Click **Settings** → **Domains**
4. Find `chat.whitemagic.dev`
5. Click the **three dots** (⋯) on the right
6. Click **Remove**
7. Confirm
8. Click on **`whitemagic-site`** project
9. Click **Settings** → **Domains**
10. Type `chat.whitemagic.dev` in the "Add Domain" input
11. Click **Add**
12. Should show "Valid Configuration" within 30 seconds

### How (via CLI, equivalent)

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
vercel domains add chat.whitemagic.dev whitemagic-site --yes
```

### Verify

```bash
curl -sL -o /dev/null -w "%{http_code}\n" https://chat.whitemagic.dev/
```

Should return 200 and show the new /chat page with Aria (Librarian
component) and the "What this is" explanation about the migration.

### About the old `magic-chat` content

The old `magic-chat` page was a thin client-side SPA backed by a
now-deprecated API endpoint. The actual chat functionality is not
recoverable from the backup (the API endpoint has been retired).
The new `/chat` page uses the same `<LibrarianChat />` component
that the `/librarian` page uses, which is the canonical
budget-capped, dharma-governed AI chat. This is the right migration
target per AGENTS.md §2 budget cap.

---

## Step 6: Push a small change to verify (1 min)

After Steps 4 and 5, push a small change to trigger a fresh
auto-deploy and verify everything is working.

### How

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
# Add a small note
cat >> docs/site-ops/.last-deploy-test << 'EOF'
This file exists to verify auto-deploys work after the Vercel recovery.
If you're reading this on the live site, auto-deploys are working.
EOF

git add docs/site-ops/.last-deploy-test
git commit -m "site: verify auto-deploy after Vercel recovery"
git push origin main
```

### Watch

```bash
vercel ls
```

### What to expect

- Within 1-2 min: a new deployment with `Building` status
- Within 2-3 min: `Ready` status

### If still broken

The auto-deploy is fundamentally broken. Use the manual workaround
(Step 3.5) for every deploy until Vercel fixes it.

---

## Step 7: Verify the new deployment (2 min)

After a Ready deploy, verify all the new content is live.

### Quick check

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site

echo "=== whitemagic.dev ==="
curl -sL -o /dev/null -w "  home: %{http_code}\n" https://whitemagic.dev/
curl -sL -o /dev/null -w "  /mcp-bridge: %{http_code}\n" https://whitemagic.dev/mcp-bridge
curl -sL -o /dev/null -w "  /zodiac: %{http_code}\n" https://whitemagic.dev/zodiac
curl -sL -o /dev/null -w "  /chat: %{http_code}\n" https://whitemagic.dev/chat

echo
echo "=== chat.whitemagic.dev ==="
curl -sL -o /dev/null -w "  /chat: %{http_code}\n" https://chat.whitemagic.dev/chat

echo
echo "=== version check ==="
curl -sL https://whitemagic.dev/ | grep -oE "v22\.[0-9]\.[0-9]" | head -3
```

### What to expect

```
=== whitemagic.dev ===
  home: 200
  /mcp-bridge: 200
  /zodiac: 200
  /chat: 200

=== chat.whitemagic.dev ===
  /chat: 200

=== version check ===
v22.2.3
```

If you see all 200s and v22.2.3, **everything is working**.

### If something is 404

- It's the stale content (from the old `0b61818` deploy). Wait
  for a new deploy, or run Step 3.5 manually.

---

## Step 8: Delete the 4 archived projects (10 min)

Once Steps 4-7 are confirmed working, the deletions are safe. Do
them one at a time, verify each, in this order:

### Order matters

1. **whitemagic** (oldest, no public users, lowest risk)
2. **dashboard** (no public surface)
3. **whitemagic-website** (had whitemagic.dev, but you already moved it to whitemagic-site in Step 4)
4. **magic-chat** (had chat.whitemagic.dev, but you already moved it in Step 5)

### How (in the Vercel Dashboard)

For each project:

1. Go to https://vercel.com/dashboard
2. Click on the project to delete
3. Click **Settings** in the top nav
4. Scroll to the bottom of the page
5. Find **Delete Project** (in the "Danger Zone" section)
6. Type the project name to confirm
7. Click **Delete**
8. Wait for confirmation (~30 seconds)
9. Verify by going back to the dashboard — the project should be gone

### How (via CLI)

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site

# Delete one at a time
vercel project remove whitemagic --yes
vercel project remove dashboard --yes
vercel project remove whitemagic-website --yes
vercel project remove magic-chat --yes
```

### Verify after each

```bash
vercel project ls
```

The deleted project should disappear from the list.

### If a deletion fails

The most common reason is **outstanding deployments with active
aliases**. If you get an error like "Cannot delete project with
active deployments":

1. Go to **Deployments** in the project
2. For each deployment, click the **three dots** → **Retire** or
   **Delete**
3. Try the deletion again

For `whitemagic-website` specifically, you'll have 4 aliases
(whitemagic.dev, www.whitemagic.dev, whitemagic-website.vercel.app,
whitemagic-website-lbailey94s-projects.vercel.app). If
whitemagic.dev was successfully moved to whitemagic-site in Step 4,
you can safely delete the others.

---

## Step 9: Update the topology report (5 min)

After all deletions, update the topology report to reflect the new
state.

### What to update

In `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/docs/site-ops/VERCEL_TOPOLOGY_REPORT_2026-06-19.md`:

1. Change the "Status" column from "TO DELETE" to "✅ DELETED" for all 4 projects
2. Update the "whitemagic-site" entry to note it now owns
   `whitemagic.dev`, `www.whitemagic.dev`, AND `chat.whitemagic.dev`
3. Add a final note: "After cleanup: 1 Vercel project, 3 custom
   domains, GitHub auto-deploy working (or documented as
   workaround)"

### Commit

```bash
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
git add docs/site-ops/VERCEL_TOPOLOGY_REPORT_2026-06-19.md
git -c user.email=opencode@whitemagic.local -c user.name=opencode commit -m "site: update topology report — cleanup complete"
git push origin main
```

---

## Step 10: Verify the cleanup (1 min)

After all 9 steps, the final state should be:

```bash
vercel project ls
# Should show ONLY: whitemagic-site

curl -sL -o /dev/null -w "whitemagic.dev: %{http_code}\n" https://whitemagic.dev/
curl -sL -o /dev/null -w "chat.whitemagic.dev: %{http_code}\n" https://chat.whitemagic.dev/
curl -sL -o /dev/null -w "app.whitemagic.dev: %{http_code}\n" https://app.whitemagic.dev/
# Expected: 200, 200, 404 (app was the abandoned dashboard)
```

The expected outcome: **1 Vercel project, 3 working custom
domains, v22.2.3 live everywhere**.

---

## Recovery from common errors

### "Cannot delete project with active deployments"

Solution: retire all deployments first. In the dashboard, go to
**Deployments** → click each one → **Retire**. Or via CLI:

```bash
# Find active deployments
vercel ls --prod
# Delete each
vercel rm <deployment-url> --yes --safe
```

### "Domain already in use"

You're trying to add a domain to a project that already has it.
Either:
- Skip the add (it's already there from before)
- Remove from the old project first

### "Build still failing with [0ms]"

Auto-deploys are still broken. Wait 1-2 hours, then retry. If
still broken, file the Vercel support ticket and use manual deploys
in the meantime.

### "404 on whitemagic.dev after step 4"

The DNS change might take a few minutes to propagate. Wait 5 min,
clear browser cache, retry.

### "I deleted a project I didn't mean to"

The backups are at `/home/lucas/Desktop/WHITEMAGIC-aux/site-ops-backups/2026-06-19/`.
Each backup has the full mirror, deployment metadata, and READMEs.
You can re-deploy from any of them by:
1. Creating a new Vercel project
2. Adding the domain
3. Uploading the backup files

This is exactly what we did with whitemagic-site. Same process
applies to any of the 4 archived projects.

---

## Summary checklist

- [ ] Step 1: Filed Vercel support ticket (or skipped)
- [ ] Step 2: Tested fresh git push, saw `Building` status
- [ ] Step 3: Re-linked GitHub integration if needed
- [ ] Step 4: Pointed `whitemagic.dev` to `whitemagic-site`
- [ ] Step 5: Added `chat.whitemagic.dev` to `whitemagic-site`
- [ ] Step 6: Pushed test commit, saw successful auto-deploy
- [ ] Step 7: Verified all new pages return 200
- [ ] Step 8: Deleted 4 archived projects (whitemagic, dashboard, whitemagic-website, magic-chat)
- [ ] Step 9: Updated topology report
- [ ] Step 10: Final state check shows 1 project, 3 working domains

If you hit a blocker at any step, the session is in a clean state
to pause. All backups are in place, all code is committed, and the
worst case is that some old Vercel projects linger.

The session repo (with this walkthrough) is at:
`github.com/lbailey94/whitemagic-site-private` branch `main`,
file `docs/site-ops/VERCEL_RECOVERY_WALKTHROUGH_2026-06-19.md`
