# Install funnel telemetry — P2 design (opt-in, content-free)

**Status**: scope 1 (local funnel layer) implemented 2026-09-18 — typed
`telemetry.funnel` milestones, `<store-root>/funnel_state.json`,
`<store-root>/install_channel`, `install.sh --ref`, npm/docker channel
markers, and the read-only `wm telemetry status`. Scope 2 (consent surface,
transport, install-id) remains design; **no transmission path exists in this
build**.
**Related**: `wm telemetry schema` / `wm telemetry status` / `wm telemetry
preview` (P1/P2, 2026-09-15/18), `docs/TELEMETRY.md`,
`docs/EDGE_GALAXY_TELEMETRY.md`, site `lib/analytics.ts`,
`PRIVACY_POLICY.md`.

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
- The scope-1 funnel layer (2026-09-18): `telemetry.funnel` milestones in the
  same galaxy, the `<store-root>/funnel_state.json` ledger, the installer
  marker `<store-root>/install_channel`, and `wm telemetry status` /
  `Installed via` in `wm status` (`crates/wm-tools/src/expansion/funnel.rs`).
- Site-side aggregate counters: visitor classes, install-intent CTA
  beacons, `install.sh?ref=` attribution (site `lib/analytics.ts`,
  `/api/stats`).
- No transport, no consent surface, no install-id.

## P2 scope

### 1. Local funnel layer (no consent needed; nothing leaves the device)

**Implemented (scope 1).** Record one `telemetry.funnel` record per milestone
in the existing telemetry galaxy (evidence, not cognition — same exclusions as
the galaxy). The authoritative ledger is `<store-root>/funnel_state.json`
(atomic write); a missing ledger rebuilds emitted milestones from a bounded
galaxy scan. `WM_FUNNEL_DISABLED=1` is the kill switch.

| event | trigger | fields |
|---|---|---|
| `first_launch` | first `wm` run on this store | channel, version, os, arch |
| `init_ok` | first successful substrate pass (`wm grimoire` / serve init) | version |
| `first_memory` | first `memory.create` / `session.record` | — |
| `first_resume` | first `session.continuity` hit with ≥1 prior turn | — |
| `active_dN` | a launch on calendar day N after first_launch | day offset |

Channel detection (best effort, disclosed as best-effort), in precedence
order, using the site's `INSTALL_CHANNELS` vocabulary
(`install_sh | binary | npm | docker | cargo | source | unknown`):

- `WM_INSTALL_CHANNEL` (npm launcher sets `npm`; Dockerfile sets `docker`);
- the installer marker `<store-root>/install_channel`
  (`install_sh[:ref]`, written atomically by `scripts/install.sh` after a
  successful verified install; `--ref` / `WM_INSTALL_REF` sanitized with the
  site middleware rule — lowercase, `[a-z0-9_-]`, 24 chars);
- a `/.dockerenv` probe;
- the binary path heuristic (`~/.cargo/bin` → `cargo`, `/node_modules/` →
  `npm`, `/Cellar/` or `/homebrew/` → `source`, otherwise `binary`);
- `install.json` `installed_via`;
- otherwise `unknown`.

No install-id is needed locally — records are per-store. `wm telemetry
status` (`--store`, `--json`) shows the local funnel read-only, even with no
store.

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
  "channel": "install_sh | npm | docker | cargo | source | binary | unknown",
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

1. **Local funnel layer — implemented 2026-09-18 (scope 1)**: typed
   `telemetry.funnel` records, `<store-root>/funnel_state.json`,
   `<store-root>/install_channel` written by `install.sh` (`--ref` /
   `WM_INSTALL_REF`), npm/docker channel markers, `wm telemetry status`, and
   the `Installed via` line in `wm status`. Read-only/preservation servers
   write nothing; `WM_FUNNEL_DISABLED=1` disables emission.
2. **Consent surface + transport + site endpoint + docs updates — not
   implemented** (scope 2; requires the explicit opt-in decision below).
3. **First analysis** once a meaningful number of install-ids exists, with
   a pre-registered read (activation rate by channel, d2/d7) — blocked on
   step 2, but the local milestone ledger already supports on-device reads
   via `wm telemetry status`.

## Open questions for Lucas

1. Counts: bucketed (`1-5`, `6-50`, `50+`) or raw integers? Bucketing is
   more private, less useful. (Scope 2 — local layer stores no counts.)
2. Day actives: local scope 1 records one `active_dN` milestone per offset
   (`day_offset` field); the scope-2 envelope can still choose `active_days`
   vs only `d2`/`d7` booleans.
3. Server retention 180 days — enough?
4. Should the npm launcher pass an install ref through? Scope 1 answer: the
   launcher sets `WM_INSTALL_CHANNEL=npm` only; refs stay install.sh-side
   until a scope-2 decision.
