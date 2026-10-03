# Phase 4 — Wave-5 findings: reflex / sensor / actuator and the MandalaOS boundary

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` / `PHASE4_WAVE2_FINDINGS.md`; covers row **E21**
(`PHASE3_DECOMPOSITION.md` L176/L204) and `PHASE4_GEN1_TREE.md` §3 wave 5. Format: observed
behavior · selection history · candidate Gen3 expression/manifest · adversarial cases ·
ablation · open questions. Counts come from the commands quoted with them.

---

## Observed behavior

### Gen1 v26 — ancestry check ("none — Gen2 added")

`rg -il 'actuator|sensorimotor' og_whitemagic` → **2 files, both non-code artifacts**
(`scripts/library_concepts_index.json`; `forecasting/prescience_claims.yaml` L446–457 is a
claim *about* CyberBrain, not a mechanism). No `reflex.*`/`sensor.*`/`actuator.*` names in
`tools/registry_defs/*.py` — the route-surface claim holds: the verbs are Gen2.

What v26 did have was sensing and declared cadences, never actuation:
- `core/whitemagic/core/consciousness/ambient_sensorium.py` — `SensorSource` protocol (L69)
  and 5 sources (L499–503): psutil system pressure (L81), user pattern (L134), temporal
  (L171), environment (HTTP `localhost:8080/health` + TCP probe `8.8.8.8:53`, L215–260),
  inference hardware (CPU ISA/SIMD/kernel, L445). `start_background()` (L415) has **no
  production caller** (only a worker-registry test); MCP handlers
  (`tools/handlers/v24_3_handlers.py:241,255`) compute on demand; `suggest_actions` is text.
- `core/whitemagic/harmony/physical_metrics.py` — reads laptop-optimizer at `127.0.0.1:3456`
  or psutil fallback (L1–13, L295); `evaluate_homeostasis` (L462) emits recommendations with
  `auto_eligible` flags only (L482–545); homeostatic loop imports it, effect advisory.
- `core/whitemagic/core/cyberbrain/multi_timescale_sync.py` — `TimescaleSync` buckets reflex
  10 ms / planner 1 s / consolidation 1 hr (L7–12); all three `run_*_loop` coroutines have
  **no callers**. `nervous_system.py:32` registers `_check_homeostasis` on "reflex" ("10 ms
  reflex loop", L44); actions are `throttle:<name>` strings (L52); the file names "MandalaOS
  eBPF Nervous System" as inspiration (L3) — name ≠ wiring.

No hardware write, e-stop, GPIO/serial/sysfs path is attested in v26. **Errata candidate:**
E21's "none (Gen2 added)" overstates *sensing* ancestry (sensorium + physical-metrics poller +
declared 10 ms tier existed, dormant/advisory); actuator/reflex-route ancestry is truly
Gen2-added (`PHASE4_ERRATA.md` has no reflex/sensor row).

### Gen2 WMv9 — what is live

1. **Hardware bus** `crates/wm-substrate/src/sensorimotor.rs` (2,127 L): `SensorDevice` /
   `ActuatorDevice` traits (L213/L233); `SensorimotorBus` (L337) with `poll_all` (L377),
   `read_sensor` (L393), `send_command` (L398), `e_stop_all` (L411). Real Linux surfaces:
   sysfs thermal/battery/fan (L630–690), procfs loadavg/meminfo/stat/netdev
   (L746/L870/L951/L1031), cpufreq (L1138); `SysfsActuator` (L1209) writes
   `value.round() * scale` to `/sys/class/hwmon/hwmon*/pwm*` or `/sys/class/leds/*/brightness`;
   its `e_stop` writes `"0"` (L1283). `linux_hardware_bus()` (L1385) discovers + registers it;
   production builds it at `wm-mcp/src/server.rs:930` (fallback `wm-tools/src/expansion/mod.rs:536`).
2. **Reflex rules** `ReflexLoop::evaluate` (L555–605): threshold + cooldown per
   (sensor_id → actuator_id); **no staleness check** on `SensorReading.timestamp`; rules
   in-memory only (no persist/load path). `reflex.evaluate` polls, evaluates and **sends**
   (`wm-tools/src/expansion/sensorimotor_tools.rs:779`); `sensorimotor.scan` runs the same as
   an autonomous cycle (`wm-cognitive/src/autonomous.rs:1899–1975`), is in `CycleType::all()`
   (L51–64) with `requires_human_review = false` (L105). The daemon attaches the live bus/loop
   (`wm-mcp/src/daemon.rs:525`) and runs `run_all` (autonomous.rs:749) on `cycle_interval` —
   a rule added via `reflex.add` executes against sysfs actuators on the daemon schedule.
3. **Dispatch table + safety mask** `wm-cognitive/src/reflex/dispatch.rs` (256 slots, O(1)
   index + mask AND + fn pointer, L47–75) and `reflex/safety.rs` (16 bits; `SAFETY_DEFAULT`
   L72; `is_allowed` subset check L85). Builtins (E_STOP, collision, thermal, beam dump, QEC)
   are **pure functions returning command descriptions** (`builtins.rs:16–88`);
   `reflex.dispatch` returns `{actuator_id, command, priority}` and never touches a bus
   (`wm-tools/src/expansion/v4.rs:158–170`) — symbolic, not actuation. Production table is
   `ReflexDispatchTable::permissive()` = `SAFETY_ALLOW_ALL` (`server.rs:845`; `dispatch.rs:85`);
   the e-stop doc says "always allowed" (L17) but `SAFETY_DENY_ALL` blocks it
   (`deny_all_blocks_everything`, L118–120). The sensorimotor handlers **never consult
   `SafetyMask`** (no safety/mask reference in `sensorimotor_tools.rs`); `actuator.command`
   (L342–452) needs only the bus mutex and declares a plain write
   (`Resource::Galaxy("substrate")`, L356) — not `destructive`, not confirm-gated.
4. **Timescale tiers** `crates/wm-cognitive/src/timescale/`: declared Reflex 100 µs–10 ms …
   Evolutionary 1 hr+ (`tier.rs:10–27`); defaults Reflex 1 ms/10 ms budget, Reactive
   100 ms/1 s, Planning 5 s/30 s, Consolidation 60 s, Evolutionary 1 hr (`mod.rs:16–65`),
   gated per brain-wave. `TimescaleBus` "does not spawn tokio tasks" (`bus.rs:30`); production
   ticks `tick_all()` per dispatch (`server.rs:4119`) and on brain-wave transitions
   (`server.rs:1732`); startup hooks are citta-decay and a `drive_decay` *placeholder*
   (`server.rs:~890–913`). Serve-path sampling is separate, throttled ≥ 1 s: `substrate.sample()`,
   homeostasis, `poll_all()` + `SensorFrameReceived` (`server.rs:4125–4195`) — reads only.

### Boundary (CONV / MandalaOS)

- CONV §2 L2627 (`/home/lucas/Desktop/dev journal/WHITEMAGIC CHATGPT CONVERSATIONS.txt:2627`):
  "WhiteMagic should sit above hard real-time control, not inside every servo loop… the motor
  controller… deterministic and local… while the reflex layer retains veto authority."
- `THEORY_MECHANISM_MAP.md:75`: MandalaOS lane owns enforcement; "this substrate contributes
  evidence, not enforcement." `CHARTER.md:112` puts MandalaOS outside WMgen3's inheritance.
  E21: "MandalaOS boundary; hard real-time stays outside" (`PHASE3_DECOMPOSITION.md:204–205`);
  "PRESERVE IMPL. → link" keeps Gen2's bus/loop/table behind an explicit link, not primitives.

### Selection history

Gen1 declared the 3-tier cadence and two software sensoriums, then left them unwired; Gen2
added the traits, sysfs/procfs bus, rule loop, dispatch table, safety mask and 5-tier timescale
crate, and wired them (server + daemon full surface). What survived is the *reading* path and
symbolic dispatch; the real-time claim did not (request-driven tick, placeholder hooks,
empty-by-default rule loop).

## Candidate Gen3 expression / manifest notes

No proposal is made here; for the row's manifest (ancestor · wire · acceptance · owner):
ancestor = Gen2 sensorimotor bus + `ReflexLoop` + dispatch table (no Gen1 mechanism ancestry
beyond dormant sensing); wire = unset (deferred); owner unset. Any Gen3 link must, per CONV
L2627 and map L75, keep determinism and enforcement outside the cognitive substrate and treat
hardware I/O as an external boundary surfaced as evidence.

## Adversarial cases

1. **E-stop under mask/load.** `is_allowed` makes e-stop refusable by any table mask lacking
   bit 0 (`safety.rs:118–120`), while production ships `permissive()` (all bits) — the bitmask
   describes a posture that is not in force. `actuator.estop` halts only bus-registered
   writable sysfs actuators; failures return `partial` (`sensorimotor_tools.rs:510–533`), and
   `reflex.dispatch` e-stop is symbolic and stops nothing.
2. **Sensor staleness/failure.** `poll_all` skips devices returning `None`; `evaluate` matches
   present readings only and never checks timestamp age or `is_available` — a stuck sysfs file
   satisfies thresholds indefinitely (no freshness bound in the code path).
3. **Unconfirmed autonomous actuation.** `reflex.add` plus the daemon's unreviewed
   Sensorimotor cycle bypasses the safety mask and the destructive-confirm pipeline; rules
   are in-memory only, so restart drops the safety posture with no journal entry.
4. **Surface reachability.** `wm serve` defaults to curated
   `memory/session/claims/transaction/gnosis` (`wm-tools/src/profiles.rs:44–47`;
   `wm-mcp/src/bin/wm.rs:1061–1067`), which excludes these routes; full is the library/daemon
   default (`profiles.rs:26–30`). Which fleet servers run full is UNVERIFIED.
5. **Latency nondeterminism precedent.** Dream cycles were already moved off the request path
   for exactly this reason (`server.rs:4110–4117`); a 100 µs–10 ms reflex inside a
   request-driven `tick_all` model would contradict the shipped tick model.

## Ablation ideas

1. Build the server table with `SAFETY_DEFAULT`/deny-all instead of `permissive` and run the
   v4 tests: symbolic e-stop allowed under default, refused under deny — the mask gates only
   the symbolic path, never `ActuatorCommandTool`.
2. Substitute an empty `SensorimotorBus` at `server.rs:930`: `sensor.list` empties,
   `sensorimotor.scan` returns NoProposals (`autonomous.rs:1938`), serve-path frames stop —
   confirms the bus as the single hardware seam.
3. Drop `Sensorimotor` from `CycleType::all()` and observe sysfs activity / Gan Ying
   `ActuatorCommandSent` + `SensorFrameReceived` volumes.
4. Add an age check in `evaluate` against `SensorReading.timestamp` and re-run cooldown
   tests — distinguishes "fired on live data" from "fired on cached file".
5. Offline: compare per-request `tick_all` cadence to a 1 ms timer loop (declared TIER_0 gap).

## Open questions

- Was the hardware bus ever non-empty in production? `discover_*` gates on path existence,
  not writability; how EACCES surfaces at command time is unattested (UNVERIFIED).
- Did any deployed server run `full` or add reflex rules? No persisted rule store exists in
  source; store-side artifacts unchecked (UNVERIFIED).
- Errata candidates: E21 ancestry wording (sensing existed in v26, dormant); `daemon.rs:73`
  "all 7 cycles" vs 8 in `CycleType::all()`; e-stop "always allowed" vs `SAFETY_DENY_ALL`;
  `SAFETY_DEFAULT` documented while permissive ships.
- `prescience_claims.yaml` L446–457 records the cyberbrain tier claim as VALIDATED (claims ledger, not mechanism evidence).