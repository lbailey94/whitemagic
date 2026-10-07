# W0 — Gen1 July-2026 runtime evidence: `tool_usage.db`

**Status: findings · 2026-09-17 · read-only; RUNTIME-OBSERVED (July 2026 rows) + inferred, labeled.
Companion to PHASE4_WAVE*_FINDINGS.md**

Source: `WHITEMAGIC_GEN1_v26.0.3/…/v26/state/tool_usage.db`, table `tool_calls`, `file:…?mode=ro`.
5,998 rows; `2026-07-06T20:14:34.286470` → `2026-07-31T19:57:16.112229`; 662 distinct
`tool_name`. Every count is row-derived (queries Q1–Q12, §Appendix). Context first:
`PHASE4_GEN2_DELTA.md`, `PHYLOGENETIC_FRAMING.md`, `PHASE4_ERRATA.md`, both wave masters.
## Coverage & method
- python3 + `sqlite3` read-only URI; the DB is untouched. Family attribution is a **name-prefix
  classifier** (Q7) — not a DB column; the census' one inferred element.
- Coverage = **July bursts only**: four heavy days (Jul 6/8/9/10) + five sparse late days
  (Jul 25/27/28/30/31 = 102 rows). Starts mid-life on Jul 6 20:14; no June baseline.
- `session_id` NULL in **5,998/5,998**; `locality` `'edge'` in **5,998/5,998**; `gana` NULL in
  5,896. Runs had to be reconstructed from timestamps and alphabetical order (below), not keys.
## Burst structure (Q1–Q4)
Q1 per-day (calls/distinct/fails): Jul 6 = 2,929/585/388 (13.2 %); Jul 8 = 859/499/98 (11.4 %);
Jul 9 = 654/568/118 (18.0 %); Jul 10 = 1,454/640/240 (16.5 %); Jul 28 = 90/35/36 (40.0 %);
Jul 25 = 2, Jul 27 = 1, Jul 30 = 6, Jul 31 = 3. Calls per distinct tool: 5.0 / 1.7 / 1.2 / 2.3.
Q2 per-hour flat tops: Jul 6 20 h = 1,117 calls but only **102 distinct**; 21 h = 1,364/582;
22 h = 448/443. Jul 8 16 h = 540/**180**; 17 h = 319/319. Jul 9 19 h = 86/86; 22 h = 568/568.
Jul 10 12 h = 665/**86**; 13 h = 789/562.
Q3 segment scan (split on inter-call gap > 300 s): 17 segments ≥ 80 calls covering 5,896/5,998
rows; each begins at its epoch's alphabetically first tool and advances in **strict byte-order**
(`activation.spread…` Jul 6/8; `abi.decode_calldata…` Jul 9/10).

| Segment | Day/time | len | distinct | last tool | read |
|---|---|---|---|---|---|
| 1–4 + merged | Jul 6 20:14–20:58 | 102/102/99/98 + 818 | 102 | consolidation.stats | **12 passes** of a 102-tool surface |
| 5–6 | Jul 6 21:03–21:46 | 598 → 766 | 153 → **580** | elemental.optimize / zodiac.status | surface grows mid-day |
| 7 | Jul 6 22:03–22:13 | 448 | 443 | sensorium.citta | cut mid-tour |
| 8–10 | Jul 8 16:28–17:06 | 180/180/499 | 180, 180, 499 | forge.validate / state.summary | **two exact 180-tool passes** (the "~181" shape) |
| 11+12 | Jul 9 19:04 → 22:04 | 86 + 482 | 568 | codegenome.fork → vector.index | full 568-tool pass, **paused 3 h, resumed at the next alphabetical tool** |
| 13–16 | Jul 9 22:42; Jul 10 12:25–12:44 | 86×4 + 172 | 86 | codegenome.fork | passes cut at the same tool; five 86-tool passes |
| 17 | Jul 10 12:51–13:18 | 1,110 | 640 | zodiac.status | ~1.7 passes over the widest surface |

Q4 surface growth: 585 first-seen Jul 6, +13 Jul 8, +48 Jul 9, +9 Jul 10, +7 Jul 27/28 = **662
union**; 607/662 are *last* seen Jul 10; late July touched 54 distinct tools in 102 calls.
**Flat-top verdict — FOR automated full-surface tours.** Signals: exact alphabetical order in every
segment; repeated passes; flat distinct-counts (102, 104, 133, 180, 568); 43–51 rows sharing one
second; handlers mostly 0.1–50 ms; a 3 h pause that resumed at the *next alphabetical tool*;
identical pass-2 order. "~181" is Jul 8's exact 180-tool pass; "~662" is the cross-day union — no
single pass covered all 662 (largest: 640 distinct in one segment; 580 uninterrupted). Evidence is
structural; no run metadata exists to label the driver.
## Sequence anatomy (Q5)
First 100 calls of Jul 6 (id order): `activation.spread, activation.stats, agent.capabilities,
agent.deregister, agent.heartbeat, agent.list, agent.register, agent.trust, alchemical_cycle, …,
consciousness.unified_field` — 100 distinct names in strict alphabetical order in 40.7 s
(20:14:34→20:15:14). Pass 2 (calls 103–204) repeats the identical order in 37 s. Between-pass
gaps on Jul 6: 8 m, 4.5 m, 1.5 m, …; a 5-call mini-fragment at 22:03:32
(`activation.spread→agent.heartbeat`, 11 ms total) precedes the next pass by 20 s. Jul 28 is the
opposite shape: 35 tools, `capabilities`/`state.current`/`galaxy.list`/`citta.cycle` re-probed
5–18×, durations 0.5–48 s, 40 % failure — an interactive/debug rhythm, not a tour. **INFERRED:**
Jul 6–10 = harness/tour enumeration; Jul 28 = operator-style probing. Structure alone cannot
settle it.
## What executed vs what didn't (Q6–Q8)
Q7 family census (prefix classifier; `other` = no rule matched, 528 tools):

| family | calls | tools | fail | top error codes |
|---|---|---|---|---|
| archaeology | 433 | 14 | 0.9 % | KeyError×3 |
| browser | 224 | 7 | **85.7 %** | browser_unavailable×192 |
| agent | 215 | 10 | 19.1 % | not_found×38 |
| citta | 160 | 8 | 2.5 % | timeout×2 |
| anomaly | 133 | 4 | 0 % | — |
| codegenome | 123 | 5 | **43.1 %** | template_not_found×36, generation_failed×15 |
| association | 107 | 6 | 0 % | — |
| memory | 97 | 16 | 11.3 % | not_found×8, DatabaseError×2 |
| dream | 90 | 9 | 34.4 % | internal_error×15, not_found×15 |
| session | 76 | 16 | 11.8 % | not_found×8 |
| activation | 68 | 2 | 0 % | — |
| retention | 45 | 7 | 31.1 % | **not_implemented×14** |
| skillforge (`skill.*`/`forge.*`) | 44 | 8 | 18.2 % | import_failed×4, skill_not_found×4 |
| grimoire | 41 | 8 | 12.2 % | internal_error×5 |
| constellation | 34 | 3 | 0 % | — |
| emergence / mesh | 18 / 18 | 2 / 3 | 0 % | — |
| kaizen / serendipity | 10 / 10 | 2 / 2 | 20 % | TimeoutError×2 / DatabaseError×2 |
| other | 4,042 | 528 | 12.5 % | internal_error×157, not_found×110, TypeError×84 |

Absent families (Q6, no name match): **reflex 0 rows, actuator 0, geneseed 0, claims 0**.
Q8 artifact organs, exact counts: **retention** — `memory.retention_sweep` 6, `memory.lifecycle`
6, `.lifecycle_stats` 6, `.lifecycle_sweep` 6, all success, each once per tour day, **never between
tours** (consistent with W2 "sweep never armed automatically"); `reconsolidation.mark/update` 7+7,
all `not_implemented` — the DB's only such codes. **constellation** — `stats` 13, `merge` 13, 0
fails; calls succeeded, but rows cannot show W2's constant-zero no-op claim (no outputs logged) —
UNVERIFIED here. **activation** — `spread` 34, `stats` 34, 0 fails (42 calls Jul 6, 16 Jul 10; one
pair per tour); invocation runtime-observed, effect not (W3: read-side live in the planner).
**emergence** — `scan` 9, `status` 9 (Jul 6 4+4, Jul 8 3+3, Jul 9 1+1, Jul 10 1+1), 0 fails, and
**no `emergence.*` row exists on Jul 28**, yet W2 dates the 329-insight writer 7/28–8/1 — the
writer does not appear in this tool log (below the tool layer, or logging off). **skillforge** —
`skill.invoke` 4/4 `skill_not_found` (runtime confirms W2 "replay dormant"); `skill.import` 4/4
`import_failed`; `skill.list/seed/export_all` 4 each, 0 fails; `forge.*` 24 calls, 0 fails; tiny
volume vs W2's 33 persisted skills — forging happened off-tool. **browser** —
`browser_session_status` 32/32 success; the six action tools 192/192 `browser_unavailable`: the
organ was dead for the entire logged month.
## Failure taxonomy (Q9–Q10)
Totals: 882/5,998 failures (14.7 %). Q9 codes: `browser_unavailable` 192 · `not_found` 179 ·
`internal_error` 179 · `TypeError` 84 · `template_not_found` 36 · `invalid_params` 29 ·
`unavailable` 18 · NULL 17 · `reflection_failed` 16 · `generation_failed` 15 · `not_implemented`
14 · `KeyError` 14 · `DatabaseError` 9 · `clone_failed` 8 · `yield_unavailable` 7 · `timeout` 7 ·
`missing_params` 7 · `ClientConnectorError` 6 · `policy_blocked` 3 · others ≤5. **751/882 failures
carry no message** (Q10) — only 131 are text-diagnosable.
- **Concentration:** top single tools — `codegenome.fork` 36, `analyze_scratchpad` 35,
  `agent.heartbeat` 34, `bitnet_infer` 33, `broker.publish` 32, six browser tools 32 each
  (388 of 882 failures, 44 %).
- **Signature-fault class (new; 84 rows, 42 tools):** every `TypeError` text is
  `handle_*() missing 1 required positional argument: 'params'` — ×8 each for `abi.parse`,
  `abi.summarize`, `abi.decode_calldata`, `api.state_machine`, `audit.report`, `bounty.track`;
  ×1–2 across `swarm.*`, `slither.*`, `http_probe.*`, `foundry.*`, `monitor.*`, `poc.*`, `pr.*`,
  `oss.*`. A scaffold invoked handlers without params — a dispatch-layer wiring fault, not an
  organ fault.
- **Broken/unavailable organs:** `browser_unavailable` 192; `template_not_found` 36
  (codegenome.fork, *every* call); `not_implemented` 14 (reconsolidation); `skill_not_found` 4 +
  `import_failed` 4 (skill replay); `reflection_failed` 16 (`consciousness.reflect`);
  `generation_failed` 15 (`codegenome.generate`); `NO_NODES` 4 (`solve_optimization`);
  `clone_failed` 8 (`external.repo_scan`). The 179 `not_found` and 179 `internal_error` are
  handler-level and mostly message-less — classed structurally, not diagnosed.
## Cost & scale (Q11–Q12)
- **Duration:** family medians 0.1–30.5 ms (`other` 1.1, archaeology 0.2, activation 315.7,
  browser 30.5; kaizen n=10, median 5,862.8). Tails: `codegenome.generate` **10,691,211.7 ms
  (2.97 h, success=1)** Jul 9 22:04; `corpus_callosum.debate` 244,168.6;
  `embedding.daemon_process` 231,654.4; `fragment.index` 137,810.8 (fail);
  `memory.lifecycle_sweep` 69,379.2. Long calls cluster in archive/index/daemon paths; the 2.97 h
  row is a hang or mis-timed logging. UNVERIFIED.
- **Tokens:** input 12,962 (2,113 rows), output **15,930,268** (5,765 rows); `archaeology_find_
  unread` alone 13,801,643 (86.6 %) over 33 calls (max 2,973,489). Looks like content-size
  accounting, not LLM usage. UNVERIFIED as cost.
- **Keys:** `locality` 100 % `'edge'`; `session_id` 100 % NULL; `gana` populated 102× mostly on
  Jul 28 (`capabilities`→gana_star ×22, `state.current`→gana_heart ×12). The DB **cannot group
  runs by session**; timestamp + alphabetical position is the only run reconstruction, and `gana`
  is unusable as an organ key for the bursts.
## Limits & unverified
- **Coverage = July bursts.** Starts Jul 6 20:14; after Jul 10 only 102 sparse rows. Not Gen1's
  lifetime, not a random sample of it.
- **Cannot label "useful."** `success=1` = handler returned without raising. Constant-zero no-ops
  (W2 constellation), broken persist paths (W2 retention) and correct results are
  indistinguishable; outputs are not logged.
- **Bench vs real use** separable only structurally (alphabetics, same-second bursts, 0.1 ms
  handlers) — INFERRED, not proven.
- **Blind spots:** no code hash/version, no agent/session identity, no daemon/background activity
  (7/28–8/1 emergence writer invisible), `error_message` NULL in 85.1 % of failures, one
  implausible duration.
## Implications for the wiring/coupling hypotheses
1. **Outward-only loop, no visible accumulation.** 662 tools × ~9 calls, repeated exact tours on
   four days, no downstream artifact beyond size-accounted reads (`archaeology_find_unread` =
   86.6 % of output tokens). This is the runtime shape of PHYLOGENETIC_FRAMING §2's named failure
   mode ("reactive tool-use with no accumulation") — INFERRED; the DB cannot see consequences.
2. **Route existence ≠ organ function.** 43 % of codegenome calls, 86 % of browser calls, and all
   of reconsolidation failed; much of the "surface" is trivia-success stat handlers. Gen3
   migrations must cite call rows, not route names.
3. **The coupling claim needs its own attestation channel.** The one documented consequence-writer
   (emergence insights, W2) left no tool rows here; a Gen3 journal must capture background
   writers or coupling stays unmeasurable.
4. **Adversarial cases to freeze from runtime:** handler-signature `TypeError: params`;
   `browser_unavailable` degradation; `template_not_found` (fork, every call); `not_implemented`
   (reconsolidation); `skill_not_found` replay; `policy_blocked` (3 rows: citta.coherence,
   galaxy.status, code.communities) — each reproducible and row-cited.
## Appendix — stated queries (read-only)
- Q1/Q2: `SELECT substr(timestamp_iso,1,10|13) k, COUNT(*), COUNT(DISTINCT tool_name), SUM(success=0) FROM tool_calls GROUP BY k`
- Q3: id-ordered rows per day; split when `ts[i]−ts[i-1] > 300`; strictness = `tool[i] <= tool[i+1]`
- Q4/Q6/Q8: `SELECT tool_name, COUNT(*), SUM(success=0) … GROUP BY tool_name` (Q4 adds MIN/MAX day)
- Q5: first 100 Jul-6 rows by id; same-second groups `GROUP BY substr(timestamp_iso,1,19)`
- Q7: prefix-classifier census (table above); families sum to 5,998
- Q9/Q10: `SELECT error_code|error_message, COUNT(*), COUNT(DISTINCT tool_name) FROM tool_calls WHERE success=0 GROUP BY 1 ORDER BY 2 DESC`
- Q11: `SELECT locality, COUNT(*) FROM tool_calls GROUP BY 1` · `SELECT COUNT(*), SUM(session_id IS NULL) FROM tool_calls`
- Q12: `SELECT tool_name, duration_ms, input_tokens, output_tokens FROM tool_calls ORDER BY duration_ms|output_tokens DESC LIMIT 10`
