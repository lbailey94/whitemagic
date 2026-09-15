# Telemetry contract (local-first)

WhiteMagic records **local diagnostic evidence**. Nothing is transmitted —
there is no transmission path in this build. This document publishes the
record contract, retention policy, and redaction pass so the behavior can be
audited without reading the source.

Machine form: `wm telemetry schema --json` · live preview: `wm telemetry preview`

## Records (typed path)

| kind | required fields | notes |
|---|---|---|
| `telemetry.window` | `kind`, `ts`, `harmony_score`, `dims`, `dim_notes` | `dim_notes` is mandatory — a window without provenance notes is a probe and must not pollute trend lanes |
| `telemetry.rollup` | `kind`, `ts`, `harmony_score` (or `harmony.avg`), `dims` | aggregated harmony over a window |
| `telemetry.observation` | `kind`, `ts`, `policy_id`, `metric`, `state`, `action`, `value` | policy-decision trail from the observation ladder (Yama bridge) |

Records carry timestamps, metric names/values, policy identity, and harmony
dimensions. They are **content-free by producer convention**: the typed path
expects no memory content, queries, or file paths, but it does not enforce a
field allowlist — extra keys are stored and previewed. Redaction is
shape-based, so `preview` scrubs credential spans but does not strip paths or
arbitrary content. Treat the producer's discipline as the first line.

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

## Transport

`mode: none`. `wm telemetry preview` is display-only: it reads the local
telemetry galaxy through read-only inspection, applies the redaction pass,
and prints the exact payload a future opt-in transmission would carry. It
performs no network I/O and writes nothing. Any future transmission is a
separate, explicitly authorized phase.
