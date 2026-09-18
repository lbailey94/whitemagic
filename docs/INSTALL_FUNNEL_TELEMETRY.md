# Install funnel telemetry — P2 design (opt-in, content-free)

**Status**: design draft for review (2026-09-17, session d8d53567). No
implementation in 9.1.9.
**Related**: `wm telemetry schema` / `wm telemetry preview` (P1, 2026-09-15),
`docs/EDGE_GALAXY_TELEMETRY.md`, site `lib/analytics.ts`, `PRIVACY_POLICY.md`.

## Why

The 2026-09-17 funnel read: 3,012 classified-human site visits and 17
tracked install.sh fetches (1.55/day vs the 2.7/day Q4 gate), while npm
(1,080/week), Docker (+167), crates.io, and release assets show real
machine acquisition. Site counters can count encounters; registry counters
can count acquisitions; **nothing can currently count activation** — first
successful initialization, first memory, first recovered session, day-2/7
return. That missing middle is why "hundreds of visits, few installs"
cannot yet be read as a conversion rate.

Constraints that do not move:

- local-first; nothing leaves the device by default;
- no content, no hostnames, no paths, no usernames, no IP storage;
- an explicit human-facing opt-in (an agent may not consent for a human);
- preview before send, redaction pass, fail-closed.

## Current state (what already exists)

- Local typed telemetry records (`telemetry.window|rollup|observation`) with
  retention (7 d windows / 90 d rollups), a read-only retention planner, and
  a destructive prune. `wm telemetry schema` publishes the contract and
  declares `"transport": {"mode": "none"}`; `wm telemetry preview` renders
  exactly what a send *would* carry, fully offline
  (`crates/wm-mcp/src/telemetry_view.rs`).
- Site-side aggregate counters: visitor classes, install-intent CTA
  beacons, `install.sh?ref=` attribution (site `lib/analytics.ts`,
  `/api/stats`).
- No transport, no consent surface, no install-id.

## P2 scope

### 1. Local funnel layer (no consent needed; nothing leaves the device)

Record one `telemetry.funnel` record per milestone in the existing
telemetry galaxy (evidence, not cognition — same exclusions as the galaxy).

| event | trigger | fields |
|---|---|---|
| `first_launch` | first `wm` run on this store | channel, version, os, arch |
| `init_ok` | first successful substrate pass (`wm grimoire` / serve init) | version |
| `first_memory` | first `memory.create` / `session.record` | — |
| `first_resume` | first `session.continuity` hit with ≥1 prior turn | — |
| `active_dN` | a launch on calendar day N after first_launch | day offset |

Channel detection (best effort, disclosed as best-effort):

- `install.sh?ref=<tag>` → the installer writes `<store>/install_channel`
  (plain file, no network); this alone improves attribution even without
  sharing, and lets `wm status` show how this install arrived;
- npm launcher sets `WM_INSTALL_CHANNEL=npm` (and any ref it was asked for);
- Docker: `/.dockerenv` probe; cargo: binary path heuristic
  (`~/.cargo/bin`); release binary: installer marker; otherwise `unknown`.

No install-id is needed locally — records are per-store.

### 2. Opt-in sharing (the part that needs a decision)

Commands:

- `wm telemetry status` — local funnel counts + share state;
- `wm telemetry enable --share` — human-facing; prints `wm telemetry
  preview` first and requires confirmation;
- `wm telemetry disable` — immediate, stops all further sends;
- `wm telemetry reset-id` — rotates the install-id (old one retired).

Envelope, versioned (`funnel/1`), exact fields:

```json
{
  "schema": "funnel/1",
  "install_id": "<random uuidv4, generated locally at first share>",
  "version": "9.2.0",
  "os": "linux",
  "arch": "x86_64",
  "channel": "install-sh | npm | cargo | docker | release | unknown",
  "first_launch": "2026-09-17",
  "milestones": ["first_launch", "init_ok", "first_memory"],
  "active_days": [0, 1, 4],
  "counts": { "sessions": 3, "memories": 12 }
}
```

Content-free by construction: no memory text, no prompts, no session
content, no file paths, no hostnames, no usernames, no IP storage. The
install-id **is an identifier** — the consent text must say so plainly; it
is random, rotatable, and not derived from hardware or network.

Transport: HTTPS POST to `https://www.whitemagic.dev/api/funnel`
(first-party, same Upstash plane as the site counters), 2 s timeout,
best-effort, never on the critical path. Offline: one pending envelope is
spooled and retried once, then dropped. The server aggregates per day and
keeps day-keyed actives per install-id (so d2/d7 can be computed); it
stores no raw IPs. Retention: 180 days.

### 3. Disclosure updates (required with the transport)

- `PRIVACY_POLICY.md`: new "optional install funnel" section with the
  envelope above.
- Site FAQ + `/whitemagic`: "no telemetry off-device by default" stays
  true; add the opt-in description.
- `wm telemetry schema`: transport becomes `opt-in`, envelope documented.

## Non-goals

- unique humans/visitors (the site stays cookieless and visit-based);
- content, prompts, session replay, file paths, hostnames;
- automatic opt-in, dark patterns, or agent-initiated consent;
- third-party analytics anywhere in the path.

## Rollout

1. **9.1.x**: local funnel records + `wm telemetry status` + the
   `<store>/install_channel` file written by install.sh.
2. **9.2**: consent surface + transport + site endpoint + docs updates.
3. **First analysis** once a meaningful number of install-ids exists, with
   a pre-registered read (activation rate by channel, d2/d7).

## Open questions for Lucas

1. Counts: bucketed (`1-5`, `6-50`, `50+`) or raw integers? Bucketing is
   more private, less useful.
2. Day actives: full offsets (`active_days`) or only `d2`/`d7` booleans?
3. Server retention 180 days — enough?
4. Should the npm launcher pass an install ref through (it currently only
   downloads the release binary)?
