# Wave-1 spec B2 — Sessions & continuity

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `309e111` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Sessions & continuity (wave plan §2; split: **link** (storage/lifecycle ·
`PRESERVE IMPL. · E11`) + **compile** (continuity/digest · `CLEANLY · E11, E1 ¶`)).
**Wire:** records + relations; continuity = `recall`/`think` over the record layer.
**Nucleus touch points:** N1, N3, N4; Part 1 invariants 3, 6; carry: adopt the
`checkpoint_nodiscovery` rhythm.
**Caution carried:** the checkpoint lives in `wm-tools/src/expansion/session.rs`, **not**
`session_ops.rs` (W1 §2; divergence #2) — a spec reading only `session_ops.rs` misses the target.
**Do not re-raise:** W0 #30 (shells empty) is the *acceptance driver*, not a new finding; the
Gen1 "Total Recall" conflation is already documented (W1).

---

## 1. Frozen behavioral spec

### 1.1 The split (one frontier, two halves)

- **Storage/lifecycle = link.** Gen2 `session.*` (`session.rs`, `session_ops.rs`; 3,047 LOC) stays
  the live storage surface; replacement is unearned (Phase 1 excluded a session module). The
  link contract is §1.2.
- **Continuity/digest = compile.** Gen3 expresses continuity as `recall` over session records and
  digest as `think` synthesis — composition, not a module (E11; canon §7 anti-bloat). No new
  primitive is created by this row.

### 1.2 Record contract (link side)

- Typed turns: `role`, `turn_type`, `session_id`, `sequence`, `importance`, tags; provenance trust
  user 1.0 / agent 0.7; sequence counts superseded turns. (SOURCE-IMPLEMENTED; W1 source map §4)
- **Resolution is time-based** (newest prior session **with turns**, `created_at` ordering; scoped
  hint when none) — never UUID-scan-based (the 2026-08-22 fix is the contract). (RUNTIME-OBSERVED)
- **Lossless replay shape:** export/import preserve ids/timestamps/tags; superseded turns are
  hidden by default and restored with `include_superseded: true`; digest derives from records —
  hand-written summaries that duplicate records are not the mechanism. (SOURCE-IMPLEMENTED +
  contract tests)
- **No payload-less shells:** every handoff record carries payload. Gen1's 24 empty shells
  (`W0_handoffs_sessions.md`; errata #30) are the failure class this acceptance targets.
- Turn supersession (`session.record` `supersedes` tags) belongs to the link side; where it and R
  (A3) could both apply to one record, a **disclosed precedence rule** is required before either
  double-applies (frontier carried from A3 §1.4).

### 1.3 Checkpoint contract (the WMgen3 rhythm)

- **Adopted route: `session.checkpoint_nodiscovery`** — stores exactly the supplied handoff fields
  (`commit`, `branch`, `tests_green`, `next_queue`, `open_flags`, `lease_id`) with **no repository
  discovery, filesystem reads, or subprocesses**; the only strict-mode-admitted checkpoint shape
  (9.1.8 delta §2.1). This ends the observed WMv9-HEAD capture quirk — the WMgen3 commit goes in
  the supplied fields, never through discovery.
- The git-capturing `session.checkpoint` **declares its reads/spawns** and is refused under strict
  mode; using it in the WMgen3 rhythm is deprecated (it captures the wrong repo by construction
  here).
- No repo discovery/subprocess may be added to the rhythm path by either side.

### 1.4 Invariants the link must state

- **Single-writer per session** (sequence canonical): concurrent recorders on one `session_id`
  are refused or merged by a stated rule — duplicates/gaps are not acceptable "chronological"
  output.
- **Boundedness is an invariant, not per-method:** the generic update path enforces the caps
  (v26's `update()` bypass is the exemplar defect); state churn does not inflate the session
  record set.
- **No ambient valence:** turns are not stamped with a global affective tone (v26 leak,
  `session_recorder.py:369-386` — not inherited).
- **One capture default, stated:** the recording default is declared once and truthfully
  (v26 double-default: settings `False` vs middleware on-unless-`"0"`; W1 consolidated errata 4,
  dual-default truth-hygiene item);
  captures exclude secrets fail-closed (9.1.7 redaction/hygiene class).

### 1.5 Journal events / evidence surface

Session writes index at **write time** (9.1.7 fix; drift 0 while serving, unchanged after
shutdown); continuity/digest evidence comes from records + journal (N4); no payload-less events.
Named here: session write events (link), `selection.decision` / `provenance.chain` for any
continuity recall (compile; A2 owns vocabulary).

### 1.6 Statutory parameters named (Tier-2)

Checkpoint field set (`commit · branch · tests_green · next_queue · open_flags · lease_id`);
recording default (link, declared); caps (files/events/next-steps/tasks) as link-side settings.

### 1.7 Non-goals

No session module in Gen3 · no porting of the Gen1 middleware taxonomy · no ambient valence · no
new continuity primitive · no changes to supersession semantics (A3) or disclosure vocabulary (A2).

---

## 2. Selection history

**Ancestor (Gen1 v26):** `session_recorder.py` — 9 machine-generated turn types; each turn a
`Memory(CITTA)` row in the `sessions` galaxy written through a **private backend handle bypassing
ingestion gates** (consistent with the 37.2 % dup inventory); sequence canonical, timestamps
metadata; three divergent "Total Recall" paths (turns, citta stream, current state — name ≠
function); dormant "continuity" siblings with zero importers; 21,351 turns of which ~10.6 % are
imports; the turn-type counts do not close (Δ1,345 — UNVERIFIED). Emotional auto-tagging was
ambient/global. `current_state.py` dual-store with a cap-bypassing `update()`.

**Selection fate:** storage/lifecycle folded and hardened into Gen2 `session.*`; continuity
folded; the ratified split (link + compile) is deliberate. Gen2 additions that matter here:
write-time indexing, the checkpoint pair (`checkpoint` + `checkpoint_nodiscovery`), time-based
resolution, export/import.

**Evidence levels:** Gen1 organs SOURCE-IMPLEMENTED, some RUNTIME-OBSERVED (sessions DB);
Gen2 contracts SOURCE-IMPLEMENTED + live; checkpoint pair delta-verified (9.1.8 §2.1); the
Δ1,345/counted-figures stay UNVERIFIED (do not cite as measured).

---

## 3. Adversarial cases

1. **Two-writer sequence race** — single-writer or a stated merge rule; test duplicate/gap
   sequences under two concurrent recorders.
2. **Ambient valence leak** — assert no global-tone stamping across sessions.
3. **Previous-session selection** — time-based newest-with-turns; tz-naive vs tz-aware and an
   empty/one-turn previous session must not hijack "where we left off"; bounded query, no 10k
   fetch.
4. **Cap bypass** — the generic update path enforces caps (no `setattr` bypass).
5. **Capture hygiene** — one declared default; secrets-in-args excluded fail-closed; counts
   generated under each default.
6. **Phrase routing (#2, 9.1.7)** — every continuity phrase ("where were we", and each
   `PHRASE_ROUTES` entry) routes **bare and with trailing content** to its tool; the
   stopword-only early-return must not pre-empt the phrase table.
7. **Write-time indexing (9.1.7)** — session writes indexed at write time; a live server reports
   drift 0; unchanged after shutdown.
8. **`checkpoint_nodiscovery` semantics (9.1.8)** — stores exactly the supplied fields; no
   discovery/FS read/subprocess; strict mode admits it while refusing the git-capturing variant.
9. **Payload-less shells** — an empty-payload handoff is refused/journaled, never stored as a
   shell (W0 class).
10. **Starvation (9.1.8)** — continuity reads stay open under starvation; empty continuity is
    disclosed as empty (scoped hint), not as stress.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Recording producers (middleware analog) | full turn stream | only explicit records; continuity coverage collapses (`first_awakening`-heavy) | EFFECTFUL |
| Nodiscovery checkpoint | correct repo fields stored | discovery captures the wrong repo (the quirk) | RE-ENTERS (rhythm correctness) |
| Continuity over records | session-grouped recall | grouping lost; digest must fail loud, not fabricate | RE-ENTERS |
| Superseded-visibility toggle | hidden by default | restored with flag (lossless) | PERSISTENT |

---

## 5. Acceptance + owner

Wrapper-side:

1. **Lossless replay shape** — export/import round-trip preserves ids/timestamps/tags.
2. **No payload-less shells** — empty handoff refused; stored handoffs have payload.
3. **Resolution semantics** — newest prior session with turns; empty → scoped hint.
4. **Nodiscovery proof** — checkpoint stores exactly the supplied fields; strict-mode refusal of
   the discovery variant.
5. **Phrase table test (#2)** — bare + trailing variants.
6. **Write-time indexing** — drift probe green while serving and after shutdown.
7. **Superseded visibility** — hidden by default, restored on request.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_B2_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
