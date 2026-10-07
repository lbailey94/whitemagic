# `wm selftest` and host health

Reference for the Gen3 `wm selftest` command: the install-invariant persistence
probe plus the host-health diagnostics that ride beside it. The host probes
exist because the install contract used to report `{"status":"ok"}` while the
machine itself thrashed on zram swap and crash-looping user units
(2026-10-06 incident). Host health is reported **separately** — the install
invariant never fails because the host is unhealthy.

```
wm selftest            # human report
wm selftest --json     # machine report (install invariants + host_status + host_health)
wm selftest --strict   # exit 1 when the host verdict is critical
```

## Persistence probe (the install invariant)

`wm selftest` runs a throwaway end-to-end probe in an exclusive scratch
directory under the system temp dir:

1. opens a fresh store and writes one canary record through the normal
   ingestion path;
2. closes it, then reopens the store **read-only** and confirms the canary is
   present and the record count is 1;
3. verifies the JSONL journal is well-formed and contains a healthy `run.end`
   event and a one-record `ingest.batch`;
4. removes the scratch store (cleanup failure is itself a failure).

On success the console prints
`WhiteMagic Gen3 persistence selftest: PASS (...)`; the JSON report carries
`"status":"ok"` and the invariants. A persistence failure always exits 1, with
or without `--strict` (`{"status":"error","persistence":"failed","error":"..."}`
in JSON mode).

## Host-health checks

All probes are Linux and best-effort: a missing `/proc/pressure` or
`systemctl` simply omits that check — it is never an error. The overall
`host_status` is the worst check verdict.

| Check | Probe | Warn | Critical |
|---|---|---|---|
| `memory` | `/proc/meminfo`: `MemAvailable / MemTotal` | `< 15%` available | `< 5%` available |
| `pressure` | max of `full avg10` in `/proc/pressure/memory` and `/proc/pressure/io` | `>= 10` | `>= 30` |
| `swap` (or `swap/zram`) | `/proc/swaps`: used / total, summed over all entries; named `swap/zram` when any zram device is present | `>= 60%` used | `>= 85%` used |
| `disk` | `df -Pk /`: available on the **root** filesystem | `< 20 GiB` free | `< 5 GiB` free |
| `crash-loops` | `systemctl --user list-units --state=activating --no-legend --no-pager`, lines containing `auto-restart` | — (no warn tier) | any unit listed |

Additionally, the report lists the **top 5 processes by RSS** (`VmRSS`,
rendered as MiB) — informational, not a check.

`pressure` reads the `full avg10` figure: the share of the last 10 seconds in
which **all** tasks were stalled on memory reclaim or I/O. Sustained
`full` pressure is the thrash signal; zram swap is a symptom, not a fix.

## Verdict contract

- `ok` — no action needed.
- `warn` — degrading; hints are advisory.
- `critical` — the host is actively unhealthy (or a user unit is
  crash-looping). `--strict` exits 1.
- `warn` never fails, even under `--strict`.
- The persistence invariant always fails closed independently of host health.

## JSON contract

`--json` prints one object. The install invariants (`status` … `scratch_store`)
always drive `status`; host health is additive:

```json
{
  "status": "ok",
  "engine": "gen3",
  "version": "<workspace version>",
  "persistence": "durable_reopen",
  "records": 1,
  "journal_events": 12,
  "scratch_store": "isolated_and_cleaned",
  "host_status": "warn",
  "host_health": {
    "status": "warn",
    "checks": [
      { "name": "memory", "verdict": "ok", "detail": "9.8 GiB available of 15.6 GiB (63%)" },
      { "name": "pressure", "verdict": "ok", "detail": "stall avg10 — memory full 0.0%, io full 0.0% (share of time all tasks were blocked on reclaim/io)" },
      { "name": "swap", "verdict": "warn", "detail": "10.0 GiB of 16.0 GiB used (62%) — zram pages live in RAM", "hint": "large resident footprint; consider stopping unused background jobs" },
      { "name": "disk", "verdict": "ok", "detail": "/: 42.1 GiB free (83% used)" },
      { "name": "crash-loops", "verdict": "ok", "detail": "none detected" }
    ],
    "top_memory_processes": [
      { "pid": 4242, "name": "llama-server", "rss_mib": 2761 }
    ]
  }
}
```

Notes:

- `verdict` values are lowercase: `"ok"`, `"warn"`, `"critical"`.
- `hint` is present only when the check has one.
- `top_memory_processes` is omitted entirely when empty; the check order is
  `memory`, `pressure`, `swap`, `disk`, `crash-loops`.
- On non-Linux hosts the checks list is empty and `host_status` is `"ok"` —
  the host diagnostics are a Linux surface, the install invariant is portable.
- When the persistence probe fails, the JSON is only
  `{"status":"error","persistence":"failed","error":"..."}` — no host block.

## Guard / CI usage

```bash
# Hard CI/guard gate: non-zero only on a critical host verdict.
wm selftest --strict

# Gate without --strict semantics (warn tolerated):
wm selftest --json | jq -e '.status == "ok" and .host_status != "critical"'

# List only unhealthy checks with their hints:
wm selftest --json | jq -r '.host_health.checks[]
  | select(.verdict != "ok")
  | "\(.verdict)\t\(.name)\t\(.detail)\t\(.hint // "")"'

# Pre-flight before a heavy build / fleet run — who is holding the RAM:
wm selftest --json | jq -r '.host_health.top_memory_processes[]
  | "\(.rss_mib) MiB\t\(.name) (pid \(.pid))"'
```

A oneshot systemd guard is the intended packaging:

```ini
[Unit]
Description=WhiteMagic host-health guard

[Service]
Type=oneshot
ExecStart=/usr/bin/env wm selftest --strict
```

Pair it with a timer (or the existing sentinel timer) for periodic checks;
`--strict` is the exit-code contract a timer/CI can rely on.

## What it does not do

- **No actions.** `wm selftest` never stops units, kills processes, drops
  caches, prunes build trees, or sweeps journeys — every hint is advisory.
  Remediation (the "host-guard" surface) is follow-on work, not shipped here.
- **Point-in-time only.** No history, baselines, alerting, or trend data; use
  a timer or the sentinel brief for cadence.
- **Root filesystem only.** `disk` checks `/`; other mounts are not probed.
- **No thermals/GPU/battery.** Not covered by these checks.
- **Does not replace `wm status`.** `status` reports store/epoch/record
  health; `selftest` reports install invariants + host health.
