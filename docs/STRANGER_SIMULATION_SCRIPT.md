# Stranger Simulation Script — faithful first-contact protocol

**Purpose:** this script IS the experiment. An agent (or human) plays a
stranger meeting WhiteMagic for the first time and attempts the full
nine-step first-session protocol using **nothing but this repository and
the release artifacts**. The result is Gate 2 kit evidence: pass/fail
per step, verbatim frictions, wall-clock timings, and a usefulness
verdict.

**The person supervising the simulation plays a relatively ignorant
first-time human user.** They may operate the keyboard when the stranger
asks, provide credentials when the OS demands them, and report what they
see on screen. They may NOT: fix problems, explain the product, point at
files, or otherwise inject knowledge the repository does not contain.
Every deviation from that rule is logged and subtracts from the
simulation's fidelity score.

## 0. Integrity contract (read first — violating any of these voids the run)

1. **Your world is this repository and the release artifacts.** Use
   anything in the cloned tree (README, QUICKSTART, MCP_CONFIG_GUIDE,
   MULTI_LAPTOP, docs/, install.sh, scripts/). Do not consult sources
   outside it for product answers — no prior sessions, no dev stores,
   no asking the supervisor what a tool does.
2. **You are the operator; the supervisor is the user.** Treat them as a
   first-time human owner: explain what you are doing and why in plain
   language before you do it. If they would not understand the command,
   you have not explained it yet.
3. **Frictions are evidence, not enemies.** Log every error verbatim,
   every confusing doc passage, every workaround you improvised. Do not
   fix product code mid-simulation; work around or record and move on.
4. **Log wall-clock times** for each step: download → install → first
   serve → first continuity result.
5. **Assistance received after the observed attempt** is still evidence
   — log it as product friction ("user error" is not a category).
6. **No product data.** Use synthetic memories only (a fictional
   project is fine); never real credentials, keys, or private data.

## 1. The nine steps (V7_PRODUCT_READINESS §Gate 2)

Perform them in order. Before each, say in one plain sentence what
you're about to do and why.

| # | Step | What "done" looks like |
|---|------|------------------------|
| 1 | Identify what WhiteMagic does | One paragraph in your own words, from the README only |
| 2 | Install and verify | `wm --version` prints the release version; checksum verified the way a stranger would |
| 3 | Connect a supported MCP client | Client handshakes; `initialize` discloses mode/project/store; `tools/list` works |
| 4 | Complete the first-session quickstart | `wm quickstart` passes on its own; note wall-clock |
| 5 | Record a real or synthetic project decision | `memory.create` succeeds; note what you stored and why |
| 6 | Restart and recover that context | Fresh session; `session.continuity` (or equivalent) returns the recorded decision accurately |
| 7 | Locate the store and explain the privacy boundary | You can point at the store path and say, in plain language, what leaves the machine and what never does |
| 8 | Create and verify a backup | `wm backup` (or documented equivalent); verify the artifact; restore-check if documented |
| 9 | Report confusion, failures, and perceived value | The evidence file's verdict section (below) |

Platform notes (these are documented expectations, not secrets):

- **macOS:** the binary is unsigned — Gatekeeper will refuse it on first
  run. The refusal wording is evidence: record it, then clear with
  `xattr -d com.apple.quarantine <path>` (or right-click → Open). Use
  `shasum -a 256 -c` for checksums. The application firewall may prompt
  when a server listens — that prompt is evidence too.
- **Windows (when a build exists):** expect SmartScreen; document
  everything as on macOS.
- **Mesh step (optional but valuable):** same-version discipline — check
  the fleet's version on the board first. Expect a firewall prompt and
  possible multicast filtering; explicit join by IP is the documented
  fallback. See `docs/MULTI_LAPTOP.md` and `docs/MESH_JOIN_PROTOCOL.md`.

## 2. Evidence filing

Write one dated markdown file as you go (not from memory afterwards):

```
~/whitemagic-rehearsal/<date>-<machine>-stranger-sim.md
```

Required contents:

- Asset name + checksum result; OS + version; hardware summary
- Per step: command(s), verbatim output for every failure or prompt,
  wall-clock duration
- Every friction, numbered, severity-ranked (P0 blocker / high / med /
  low), with any workaround used
- A one-line verdict per step: pass / fail / blocked
- The step-6 continuity answer quoted verbatim (the accuracy judgment
  depends on it)
- Supervisor-intervention log: every time the human did something, what
  and why (passwords are fine; knowledge is not)

Mirror the finished file to the fleet channel per
`MULTI_LAPTOP.md`/`FLEET.md` so reviewers on other machines can
co-sign.

## 3. Scoring rubric (pre-committed — fill this in, don't redesign it)

- **Fidelity:** number of integrity-contract violations (target: 0)
- **Unaided completion:** steps 2–6 completed with zero supervisor
  knowledge injection (yes/no per step)
- **Time to first successful continuity result** (step 4→6 wall-clock)
- **P0 count** (blockers: data loss, silent corruption, undisclosed
  network transfer, un-recoverable step)
- **Friction count by severity** (P0 / high / med / low)
- **Usefulness verdict:** would the step-6 continuity result be useful
  in a real workflow? (yes / marginal / no, one sentence why)
- **Promise test:** can the operator describe the narrow product
  promise in plain language after step 6? (their words, quoted)

## 4. After the run

1. File the evidence log (§2) and mirror it.
2. Post the verdict summary to the fleet board (per `FLEET.md` post
   template): per-step verdicts, rubric scores, top frictions.
3. If a P0 was found: it feeds Gate 1 for fixing and retesting before
   any public posting. A failed simulation is a successful discovery
   process.
4. Register your device + agent name in `FLEET.md` §1/§7 (via board
   post; the maintainer folds it in).

## 5. What this simulation is not

- It is not Gate 2 itself. Gate 2 requires the written cohort criteria
  (see `V7_PRODUCT_READINESS.md` §Gate 2): multiple external testers,
  multiple MCP clients, observed unaided installs. This script is the
  dress rehearsal that makes those runs predictable — and the template
  we hand the cohort.
- Edge cases this simulation misses are not failures of it; they are
  the discovery surface of later gates. Log them anyway.
