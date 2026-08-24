# Gate 2 Recruitment Kit

Working materials for the stranger-tested alpha gate defined in
[`V7_PRODUCT_READINESS.md`](V7_PRODUCT_READINESS.md#gate-2--stranger-tested-alpha).
Everything testers receive is copy-paste from this file plus the public
README and release link — nothing internal leaves the repo.

## Pre-recruitment checklist (blockers before the first message ships)

1. **Version truth** — RESOLVED 2026-08-24: `v7.0.0-alpha.3` cut from tag
   (CI-built, 8 assets, prerelease-marked); `wm --version` now matches the
   release page.
2. **GitHub "Latest" release is v5.8.0** — PARTIALLY RESOLVED 2026-08-24:
   v5.8.0 retitled "retired historical release"; alpha.3 marked prerelease
   with truthful notes; installer resolves newest-including-prereleases so
   testers get alpha.3. Remaining cosmetic gap: `/releases/latest` badge
   still names v5.8.0 (the `make_latest` API flag did not apply to a
   prerelease) — one manual UI toggle on the alpha.3 release finishes this.
   Also add a line in the recruitment message pinning the exact release URL,
   which sidesteps the badge entirely.
3. Confirm cohort shape: ≥5 external testers, ≥2 different MCP clients,
   nobody who built the workflow, Linux x86-64 with glibc ≥ 2.39.
4. Freeze the artifact for the cohort: testers all get the same release URL;
   mid-cohort upgrades invalidate comparisons unless re-run end to end.

---

## 1. Recruitment message (copy-paste)

> Subject: Testing a local memory layer for AI coding agents (30–45 min, private alpha)
>
> Hi <name>,
>
> I'm building WhiteMagic — a local-first memory server for AI coding agents.
> It lets an agent record important context during a coding session and pick
> it back up in the next one over MCP, entirely on your machine. No cloud, no
> telemetry.
>
> I'm looking for a handful of people to run a structured first-contact test:
>
> - **What:** install the binary, connect your MCP client (Claude Desktop,
>   opencode, Cursor, or similar), and work through a two-session exercise —
>   record a note in session one, recover it in session two. Then create a
>   backup and fill out a short report.
> - **Time:** about 30–45 minutes.
> - **You'll need:** a Linux x86-64 machine (Ubuntu 24.04 or newer works; the
>   binary needs glibc 2.39+) and an MCP client you already use.
> - **Ground rules:** I won't help while you attempt it — the point is to find
>   everything that confuses a new user, not to get you unstuck. Afterwards
>   I'll happily fix whatever you hit. Your report stays private; don't send
>   me memory contents or anything sensitive — use made-up project notes.
>
> Interested, and can you do it in the next week? I'll send the install link
> and the exercise sheet.

Notes for the recruiter (us): track client type per recruit so ≥2 MCP clients
land in the cohort; prefer people who have never seen the workflow built.

---

## 2. Tester instructions (copy-paste — send with README + release link ONLY)

> ### WhiteMagic first-contact test
>
> Everything below starts from the public
> [README](https://github.com/lbailey94/whitemagic#readme) and the release
> linked in my message. If something contradicts the README or doesn't work,
> that's exactly what I need to know — write it down instead of working around
> it. Please don't ask me questions until the whole attempt is done; note what
> you *would* have asked.
>
> Use synthetic project notes throughout (a fake project name, fake
> decisions). Nothing you store leaves your machine, and please don't paste
> memory contents into the report — describe what happened, not what you
> stored.
>
> 1. **Know before you look (no peeking yet):** in one sentence, what do you
>    expect WhiteMagic does? You'll compare this against reality at the end.
> 2. **Install** following the README. Verify with `wm --version` and
>    `wm doctor`. Note anything that surprises you (paths, permissions,
>    checksum handling, shell profile changes).
> 3. **Connect your MCP client** using the config snippet in the README.
>    Note your client name + version. How did you confirm the connection
>    actually works?
> 4. **Session one:** discover how to record a short synthetic decision (one
>    sentence is fine), then end the session cleanly. Use the tools however
>    the README suggests — don't invent extra structure.
> 5. **Restart** your MCP client completely (kill the process, reopen), then
>    **recover** the context in a fresh session. Time yourself from "server
>    restarted" to "I successfully saw my earlier note" — this number matters.
> 6. **Store + privacy:** locate the store directory on disk. In your own
>    words: what is stored there, what is NOT sent anywhere, and what would
>    someone need to read your notes?
> 7. **Backup:** follow the README's backup section. Then restore it into a
>    scratch location and confirm the restore verifies.
> 8. **Report:** fill the template below and send it back.
>
> If you get stuck anywhere: stop after ~10 minutes of trying, write down
> exactly what you saw (command output, error text), and move to the next
> step you *can* do. Blocked-but-documented beats silently abandoned.

---

## 3. Tester report template (copy-paste)

```
WhiteMagic tester report — <your name or handle>

CONSENT
[ ] I consent to this report being retained in anonymized form for release
    validation. (Names/contact are stripped; the report text itself is kept.)

ENVIRONMENT
- Linux distro + version:
- Kernel arch (uname -m):
- glibc version (ldd --version | head -1):
- MCP client + version:
- WhiteMagic version reported by `wm --version`:

STEP RESULTS (pass / fail / skipped)
[ ] Install completed without help
[ ] `wm --version` and `wm doctor` behaved as documented
[ ] MCP client connected
[ ] First session: recorded a synthetic decision
[ ] Clean session end / restart
[ ] Second session: recovered earlier context        <- core step
[ ] Located store; could state the privacy boundary
[ ] Backup created, verified, restored

KEY NUMBERS
- Minutes from server restart to first successful recall of prior context:
- Total wall-clock time for the whole test:

BLOCKERS & CONFUSION
For each place you got stuck or surprised (most severe first):
- What you were trying to do:
- What happened instead (paste errors/output):
- What you expected:

CONTINUITY QUALITY
- Was the recovered context accurate and useful, or generic/wrong?
- Did your agent follow the session rhythm unprompted (record/checkpoint),
  or did you have to drive it manually?

VALUE
- Would the two-session continuity result be useful in your real workflow?
  (yes / no / maybe — one sentence why)
- One thing that almost stopped you from continuing:

SUPPORT NEEDED AFTER THE ATTEMPT
- What did you ask me afterwards, and what did I change or explain?
  (This gets logged as product friction, never user error.)

OVERALL SEVERITY RANKING OF YOUR ISSUES
- Blockers (could not complete):
- Major (completed with pain):
- Minor (cosmetic/wording):

One-sentence description of what WhiteMagic does, in your own words:
```

---

## 4. Observer log (internal — one per tester, kept in this repo or private notes)

```
Test #<n> — <pseudonym> — <date>
Client: <name + version>          OS: <distro + version>
Artifact: <release URL + checksum>
Steps passed WITHOUT assistance: <list>
Time to first successful continuity: <minutes>
Interventions (each = product friction, cite step + quote):
  - <step>: <what I had to explain/do>
Agent followed session rhythm unprompted: yes/no/partial
Recalled context useful + accurate: yes/no/partial
Backup/restore outcome:
P0 candidates (data loss, silent corruption, undisclosed network transfer,
onboarding failure): <none | describe>
Severity-ranked feedback summary:
Verdict vs acceptance criteria contribution: <which criterion this record feeds>
```

---

## Acceptance criteria reference (from V7_PRODUCT_READINESS.md)

- ≥4/5 install and connect without live assistance.
- ≥4/5 complete the two-session continuity workflow.
- No data loss, silent corruption, or undisclosed network transfer.
- Every P0 fixed and retested before exit.
- Remaining limitations documented, not hidden.
- Testers can state the narrow promise in plain language.
- Majority say continuity would be useful in a real workflow.

A failed Gate 2 returns the product to Gate 1 with evidence; it does not
justify expanding the feature set.
