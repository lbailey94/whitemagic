# Telemetry contract (local-first)

WhiteMagic records **local diagnostic evidence**. Nothing is transmitted —
there is no transmission path in this build. This document publishes the
record contract, retention policy, and redaction pass so the behavior can be
audited without reading the source.

Machine form: `wm telemetry schema --json` · local funnel: `wm telemetry status` · live preview: `wm telemetry preview`

## Records (typed path)

| kind | required fields | notes |
|---|---|---|
| `telemetry.window` | `kind`, `ts`, `harmony_score`, `dims`, `dim_notes` | `dim_notes` is mandatory — a window without provenance notes is a probe and must not pollute trend lanes |
| `telemetry.rollup` | `kind`, `ts`, `harmony_score` (or `harmony.avg`), `dims` | aggregated harmony over a window |
| `telemetry.observation` | `kind`, `ts`, `policy_id`, `metric`, `state`, `action`, `value` | policy-decision trail from the observation ladder (Yama bridge) |
| `telemetry.funnel` | `kind`, `ts`, `milestone` | local install-activation evidence; optional bounded fields `channel` (site vocabulary `install_sh`\|`binary`\|`npm`\|`docker`\|`cargo`\|`source`\|`unknown`), `version`, `os`, `arch`, `day_offset` — no free text |

Records carry timestamps, metric names/values, policy identity, and harmony
dimensions. They are **content-free by producer convention**: the typed path
expects no memory content, queries, or file paths, but it does not enforce a
field allowlist — extra keys are stored and previewed. Redaction is
shape-based, so `preview` scrubs credential spans but does not strip paths or
arbitrary content. Treat the producer's discipline as the first line.

## Install funnel (local layer, scope 1)

`telemetry.funnel` rows are milestones, not metrics. `wm` emits them once per
store, on-device, with no consent surface and no transmission path:

| milestone | trigger | fields |
|---|---|---|
| `first_launch` | first writable `wm` run against this store | `channel`, `version`, `os`, `arch` |
| `init_ok` | first successful store/substrate init (`wm serve`, `wm grimoire`) | `version` |
| `first_memory` | first successful `memory.create` / `session.record` | `version` |
| `first_resume` | first `session.continuity` hit with ≥ 1 prior turn | `version` |
| `active_dN` | a launch on UTC day N ≥ 1 after `first_launch` | `day_offset` |

Channel detection is best effort and content-free: `WM_INSTALL_CHANNEL`
(npm/docker launchers), the installer marker
`<store-root>/install_channel` (`install_sh[:ref]`), a `/.dockerenv` probe,
the binary path heuristic, then `install.json`'s `installed_via`. Refs are
sanitized (lowercase, `[a-z0-9_-]`, 24 chars) and recorded locally only.

The authoritative milestone ledger is `<store-root>/funnel_state.json`
(atomic tmp+rename); if it is lost, the emitted milestones are rebuilt from a
bounded `telemetry` galaxy scan rather than re-emitted. `WM_FUNNEL_DISABLED=1`
suppresses emissions. `wm telemetry status` (read-only, works with no store)
shows channel, first launch, milestones, and active days. `wm status` shows
`Installed via` when the marker exists.

## Redaction

Every preview/send-shaped payload passes `wm_memory::redact_credential_content`
(the same pass that guards `wm ingest`): PEM private keys, AWS access key
IDs, GitHub/OpenAI/Slack tokens, JWTs, and credential assignment values are
replaced with `[REDACTED:<class>]` markers. A redaction firing inside
content-free telemetry is itself a finding and is disclosed by `preview`.

## Retention

| artifact | default horizon | pruning |
|---|---|---|
| windows | 7 days | `telemetry.retention` reports the inventory read-only; the destructive `telemetry.prune` requires `confirm: true` |
| rollups | 90 days | same |
| observations | retained with rollups | same |
| funnel milestones | store lifetime | **not pruned** — `telemetry.prune` deletes only windows/rollups; the planner lists funnel as `managed: false` ("store-lifetime evidence; telemetry.prune does not delete; reset explicitly") |

## Transport

`mode: none`. `wm telemetry preview` is display-only: it reads the local
telemetry galaxy through read-only inspection, applies the redaction pass,
and prints the exact payload a future opt-in transmission would carry. It
performs no network I/O and writes nothing. Any future transmission is a
separate, explicitly authorized phase.

Scope 1 funnel records are strictly local: no transport, no consent surface,
no install-id, and `wm telemetry status` says so in its output ("Transport:
none — records stay on-device; no share command exists in this build").
