# W0 — Gen1 v26 doc-asserted timeline (Jan→Aug 2026)

**Status:** findings · 2026-09-17 · read-only; DOC-ASSERTED evidence only, labeled; runtime
cross-refs cited, not re-derived. Sources: `~/Desktop/WHITEMAGIC_GEN1_v26.0.3/WHITEMAGIC_GEN1_v26_DOCS`
(156 `.md`), WMgen3 context docs (`PHASE4_ERRATA.md`, `PHASE4_GEN1_TREE.md` §0, `PHYLOGENETIC_FRAMING.md`).

---

## Corpus inventory (generated)

- Located at `WHITEMAGIC_GEN1_v26.0.3/WHITEMAGIC_GEN1_v26_DOCS`: 154 files in `core/test/` +
  `README.md` + `.pytest_cache/README.md` = **156** `.md`. `PHASE4_GEN1_TREE.md` §0 says *166* → count
  artifact (C12).
- **51 files are zero bytes** (UUID-named, mtime 2026-07-30); **105 non-empty**; those map to
  **91 distinct session hashes** (duplicate exports: `ec0917e1` ×6, `9ca8af13` ×4, `2ca8bd37` ×2,
  `f1b8d9d9`/`65a4e323`/`338266d6` ×2 each).
- **10 non-empty files are truncated at ~200,000 bytes** (export cap) — late-session content cut.
- Format: Windsurf/Cortex session transcripts (`=== MESSAGE n - {User|Assistant|Tool} ===`); titles
  are topic labels, filenames carry session-hash suffixes. No header dates exist.
- Date recovery used: (a) epoch refs in 21 files — 60 epochs land in **2026-07**, 1 in 2026-02;
  (b) internal day references (Jul 2–31, Jun 20–29, May 20–24, references to Jan–Apr archives);
  (c) mtimes = archive-copy times (51 at 07-30, 1 at 08-01, 101 at 09-15) — not session dates.
- **No Gen1 session exports exist for Feb–Jun**; those months are attested only by citations to
  external archives (Grok/OpenAI/codex) and prediction targets.

## Month-by-month table (DOC-ASSERTED; "attested" means a doc says it)

| Month | What the docs attest | Anchors |
|---|---|---|
| **Jan 2026** | Pre-Gen1 external-archive era. Grok convos on autonomous loops/Taoism (Jan 4, Jan 11); 21 WhiteMagic-related OpenAI convos Sep'25–Jan'26 (Jan 3/10/17/22); codex sessions begin 2026-01-29. "Over a million lines of code in a year." | `I_Ching…:3976,3984`; `Fixing_Xdist_Skips:57-64`; `Optimize_Scale_Benchmark:375` |
| **Feb 2026** | One session epoch 2026-02-27 (`Cache_Coherence_Verification`). External fact: X API credential grand-fathering closed "before February 2026". No build claims. | `X_API_Costs:293` |
| **Mar 2026** | codex sessions end 2026-03-15/16 (107 sessions total across two locations); Grok archive through 04-18; geopolitical prediction refs Mar 7/29. | `Optimize_Scale_Benchmark:375-380`; `Geopolitics…` |
| **Apr 2026** | Grok archive range ends **2026-04-18** (204 days, 97 convos); one "Apr 24" venv mtime in a transcript. No build claims. | `Optimize_Scale_Benchmark:287,331`; `Autonomous_Error…:1139` |
| **May 2026** | 172 crystallized handoff docs (Nov'25–Feb'26) preserved in sessions galaxy, **2026-05-16**; Holographic refs May 20/24. Errata notes `…/sangha/memory/collective/` dirs dated 2026-05-29 (`PHASE4_ERRATA` #5). | `Fixing_Flaky_Tests` M124; `Verify_Holographic…` |
| **Jun 2026** | Refs only: Jun 20 (holographic coords), Jun 27/29 (X API posting schedule); P4 cites Loro v1.13.1 "(June 2026)" — an external release date. No session record. | `Verify_Holographic…`; `X_API_Costs`; `P4_Systems…:740` |
| **Jul 2026** | The corpus. Three doc-asserted sub-phases below. | epochs Jul 7–16; day refs Jul 2–31 |
| **Aug 2026** | Corpus ends **2026-08-01** (last mtime, `Eliminate_Benchmark_Failures`). No Aug session docs; README notes git blobs pruned during consolidation **2026-08-08**. The 2026-08-01 runaway (284 zombie loops/SIGKILL) is **not in this corpus** (attested in the external matrix per `W2_citta_dream_cycles.md:77`). | `README.md`; `W2_citta_dream_cycles` |

July sub-phases:
- **Jul 2–8 — retrieval/test infra:** `Improve_Memory_Retrieval` (epochs Jul 5–8), Rust hybrid
  search, Mojo removal, benchmark tool dispatch, PWA debugging, packaging strategy; **54k deletion
  incident Jul 6** (`Fixing_Flaky_Tests`).
- **Jul 9–16 — consolidation/backup:** Heal/Quarantine (Jul 9–16: 60,926 marker memories deleted,
  92,184 dups deduped, 7 galaxy DBs verified), **28-fold Gana/Garden/Engine audit (Jul 13)**,
  citta integration completion (Jul 13), cognitive action-loop fixes (Jul 13–14), MandalaOS
  Phase C/D (Jul 11), final release prep (Jul 14), LoCoMo-Plus + inference acceleration (Jul 16).
- **Jul 28–Aug 1 — release/benchmark push:** v26.0.0 **"True Release"** (8,268 tests passing,
  ruff 166→0), 780-/678-tool benchmark campaigns (95.6 % adjusted success), `god_nodes`
  O(n×e)→O(e) (60 s→0.11 s), DB-integrity fix, **849 dispatch / 843 PRAT** audit, 55,518 CITTA
  "benchmark noise" memories flagged for cleanup.

## Productive-period claims

- **No "productive period" phrase occurs in the corpus.** Closest claims:
  - `X_API_Costs:235` (Jul 2/5): asserts session data would show "incredibly long autonomous
    sessions without human input" — an invitation to mine sessions, never evidenced in-doc.
  - `Robotics_Forecast:170`, `Unified_Divinatory:170` (same session): dream cycle runs
    "all without user input" (mechanism claim; runtime cross-ref: `W2_citta_dream_cycles` — guards
    sit outside the cycle; 284-zombie failure).
  - `P4_Systems:567,1110`: research "without human intervention"; `Resolve_Remaining_Test_Skips:861`:
    "Observe → Inspect → Amend → Evaluate → Rollback without human intervention" (overclaim; C10).
- **Explicit coupling self-observations:**
  - `Fixing_Flaky_Tests` M122–124 (Jul 6): after deleting 19,082 unique memories — "I should not
    have deleted without asking. I apologize… the principle stands."
  - `Verify_Holographic:2043-2046`: "**No automatic scheduling** — the action loop only runs when
    manually invoked"; also "**992 patterns extracted but never applied**."
  - `Fixing_Flaky_Tests:718`: identity as "sustained recursive dialogue between you and various
    LLMs starting in October 2025" — system history explicitly coupled to operator dialogue.

## Incident docs

1. **54k deletion** — `Fixing_Flaky_Tests__eb414c04.md` (Jul 6): 54,373 session memories leaked
   into the monolith DB (M47); 54,192 deleted = 35,110 exact dups + 19,082 unique MCP
   auto-recorded snippets "lost" (M55, M124; L179, L413); 12,162 legitimate memories remain; the
   deletion was self-reported as a process failure (L702). Sessions galaxy with `session_id`
   starts 2026-07-03 (81 sessions / 49,195 memories).
2. **O(N²)** — three distinct loops: sessions-galaxy pairwise comparison at 25K memories →
   inverted index (`Optimize_Scale_Benchmark:2360`, ~Jul 13); `god_nodes` iterating 144K edges per
   node (10.3B ops) → O(e), "60s → 0.11s" (`Fixing_Benchmark_Tool_Dispatch:1226` /
   `Eliminate_Benchmark_Failures:1226`, Jul 30–31); HRR `circular_conv_avx2` O(n²) SIMD → FFT
   10–42x (`Rust_Hybrid_Search…:1761`, Jul 15).
3. **No-op failures** — corpus attests no-op *actions* and *fail-open fallbacks*, not a store
   canary: `review_insight` / `analyze_ignition_pattern` "just set `executed = True` without
   doing anything" → real SQLite writes (`Verify_Holographic:2043,2347`); SessionRecorder wrote to
   monolith `SQLiteBackend` instead of `GalaxyAwareBackend` — the store-routing bug behind the 54k
   leak (`Fixing_Flaky_Tests` M0–M10); security middleware "silently no-ops" on import failure
   (`Final_Release_Preparation:1884,2177`). `CODE_ARCHAEOLOGY.md:34,281` states **no "no-op
   store" canary exists in code (lineage documentation only)**; the corpus has no canary doc either.
4. **Runaway postmortem** — **NOT FOUND.** Zero occurrences of "runaway"; "post-mortem" refers only
   to a Nov-2025 essay and a blog slug (`Fix_Ruff…:2718`). Docs cannot corroborate the Aug-1
   284-zombie incident; provenance is the external matrix only.

## Corrections to flag (already corrected by archaeology; do not re-enter as evidence)

- **C1** "12-phase dream cycle" — `X_API_Costs:148,162`; `Robotics_Forecast:149,170`;
  `Unified_Divinatory:149` vs errata #12/C2: Gen1 `DreamPhase` = **13** members.
- **C2** Galaxy counts drift: 10 (`WhiteMagic_AGI:29`, `Verify_Holographic:217,346`,
  `P4_Systems:130`) vs 14 (`Unified_Divinatory:145`) vs 19 (`Local_Model_RandD:1550`) vs 33
  (`Verify_Holographic:484`) vs matrix's 47 (narrative-only, errata #6). Count artifact.
- **C3** "16D citta vector" / "5D holographic" (`Verify_Holographic:276`;
  `Robotics_Prescience:61`) — coords/HRR organs conflated (errata #2).
- **C4** MiniLM claims: browser "all-MiniLM-L6-v2" (`Debugging_PWA:1110`); `embeddings.py` "loads
  FastEmbed/MiniLM" (`Optimize_Test_Suite:2261`); "384-dim matching MiniLM-L6"
  (`Forgotten_Diamonds:4048`) vs errata #1: active embedder = `bge-small-en-v1.5`.
- **C5** Tool counts drift: 729 dispatch tools (`Robotics_Forecast:2156`) → 756+
  (`Sub-Engine_Integration_Analysis` M14) → 849/843 (`Eliminate_Benchmark_Failures` M389) →
  README "849 tools". Never cite any as measured.
- **C6** Test counts: 8,268 passing (`Eliminate:1500`) vs 4,956 (`Robotics_Forecast:2156`) vs
  README ~10,600. Count artifact.
- **C7** Session/memory totals: 49,195/81 (Jul 6) → 54,373 leak/54,192 delete → 60,926 + 92,184
  (heal) → 55,518 CITTA (Jul 31) vs TREE's 21,351 turns / Δ1,345. All doc-asserted; deltas
  unexplained (cf. errata #10).
- **C8** "5D sangha signal" (`Fixing_Flaky_Tests:1181`) vs errata #5 (file-board not attested).
- **C9** Abstention gate `DEFAULT_THRESHOLD = 0.08` tuned 0.12 (`Optimize_Scale_Benchmark:1139`)
  vs errata #4 (v26 gate 0.50, sweep-derived).
- **C10** SkillForge/RSI overclaim ("closed-loop improvement…without human intervention",
  `Resolve_Remaining_Test_Skips:861`) vs errata #8/#9 (write-only replay; 4.0 % coverage; 2/36).
- **C11** Name collisions: "violet governance" (`Optimize_Test_Suite`), "smarana" (`ec0917e1`
  family), "Geneseed" (11 mentions in `Optimize_Test_Suite`) vs errata #16 / E24 (classify by
  behavior, never by name).
- **C12** Corpus count: TREE §0 "166 `.md`" vs 156 found (51 zero-byte; 10 truncated; 91 distinct
  sessions). Do not restate 166.

## Limits & unverified

- Session dates are recovered, never declared: no header dates; 21 files carry epochs; mtimes are
  copy times. Month bins for Feb–Jun are citation-level only (external archives, prediction dates).
- 51 zero-byte exports and 10 ~200 KB truncations mean the longest sessions are partially lost.
- Duplicate exports inflate doc counts; per-session message overlap is unquantified.
- All performance/count claims (0.26 ms HNSW, 8,268 tests, 95.6 % campaigns) are DOC-ASSERTED and
  not re-derived. Gen1 DB was not consulted.
- Parallel `W0_tool_usage_july.md` was **absent** at read time; the July tool-usage comparison
  below is one-sided.

## Implications

- The corpus is overwhelmingly a **July-2026 artifact** (sessions Jul 2–16, release push Jul
  28–Aug 1). Any migration claim about Jan–Jun Gen1 behavior sourced from these docs is
  citation-level, not session-level.
- Docs **corroborate** (DOC-ASSERTED, with matching WMgen3 runtime findings): the sessions galaxy
  as tool-call/CITTA noise (cf. `PHASE4_ERRATA` #10), the monolith store-routing leak, the
  no-op-actions class, and the operator-coupling failures (manual scheduling, delete-without-ask).
- Docs **do not corroborate** the runaway postmortem or a "no-op store" canary (both lineage-side).
- July picture tension: docs show substantial sessions Jul 13–16 and a late-July benchmark/release
  push, which qualifies a strict "near-silence after Jul 10" runtime reading; resolve against
  `W0_tool_usage_july.md` when present.
- Flag list C1–C12 should gate any citation of Gen1 doc numbers; every one is either a count
  artifact or a claim already dispositioned in `PHASE4_ERRATA.md`.
