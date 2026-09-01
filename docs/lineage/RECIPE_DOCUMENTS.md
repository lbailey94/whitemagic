# The Recipe Documents — the theory stratum

**Canonized:** 2026-08-31 · **State verified as of:** 2026-08-31
✓ = opened on disk this session · ◇ = as recorded by the reading-session scouts (re-verify before any operation on the file)

These are the texts that *prescribe* what WhiteMagic is — the recipe the substrate is being built to match (rubedo criterion 3: substrate-match, checked against the Nov 13 text as quoted here).

---

## 1. The origin text — Nov 13, 2025 memory-theory convo ✓

`data/staging/v26-heritage/openai_archives/20260712_i75_2025-11-13_-_Whitemagic_memory_theory_0d9fd15bd196.md` (1,068 lines)

The founding recipe, written in one conversation. **Verified clean** — the wave-1 scout rumor of corruption fails verification (only benign export stubs).

- **The bet:** "stable, well-organized, human-readable memory ⇒ problem-solving becomes more strategic, more consistent, more 'person-like'."
- **Taxonomy v1:** `preference, task, hypothesis, fact, warning, constraint, design_decision` — v2 adds `rule, event, bug, persona`.
- **Scoring:** "relevance (how often it's used), freshness (last touched), reliability (contradicted or confirmed?)" — the triad now implemented as the tier system + write gates + trust weighting.
- **Agent cast, verbatim:** the **Librarian** watches logs/chats/diffs; the **Editor-Hygienist** merges/tags/archives; the **Planner** reads memory + goals → task lists. (v8 S5's write gates + the Editor-Hygienist role are this cast becoming executable.)
- **Policies:** `local_only / sync_strategy / allowed_models / sensitivity`.
- **Key lines:** "Think: git, but for AI memory." · "Models will be like CPUs. Whitemagic is closer to: filesystem, database, git history, and a bit of 'OS for memory'." · "Memory is the substrate of identity."
- **Status:** the through-line from this text to the current substrate is the v8 acceptance standard (the Eight: no unevidenced capability claims). MandalaOS mentions end at this date — the parent handed off here (see CONCEPT_GENEALOGY below).

## 2. The authoritative lineage map — Jun 2, 2026 ARCHIVAL_DISCOVERY_REPORT ✓

`archives/WMdocs/docs-2/archive/2026-07-stale-cleanup/reports/2026-06/ARCHIVAL_DISCOVERY_REPORT_2026-06-02.md` (477 lines)

- **The inversion:** "Blackmagic was about *extracting* capability from AI… a **power-over** relationship"; "Whitemagic… *giving* capability to AI through governance, memory, and ethical architecture… a **power-with** relationship." "Built on gratitude, not gatekeeping."
- **The rotation law** (now rubedo criterion 2): "Memories are never deleted, only rotated outward."
- **The library discovered:** 701 files / **3,848,729 words** — "two Mahabharatas."
- **The lineage chain it maps:** harmony.txt / DHARMA.txt → CyberConsciousness → MCPs.txt → genesis4 → cognitive_development_super_prompt → blackmagic → MandalaOS → Edgerunner Violet → WM v0.2 → v22.2.0.
- **Security note:** the report confirms `gemkey.txt` (an inactive Gemini key existed in the corpus) — handled; listed here only so the note doesn't get re-derived as new.

## 3. The method text — Oct 3, 2025 No-Loss Distillation ✓

`data/staging/v26-heritage/openai_archives/20251003_i70_2025-10-03_grok_Profound_Perennialist_Synthesis_bb74a9cf_8f9c57597f19.md` (871 lines, two-pass; the `[Q###]` anchor system was introduced in pass 2)

- **Honest caveat (load-bearing):** ~1.9M chars of NewSpirit.txt were truncated before distillation — the no-loss ideal was structurally imperfect from birth. NewSpirit.txt is now physically located (◇ `WHITEMAGIC-aux/aux/codex/whitemagic-codex/00_source/LIBRARY/---NewSpirit.txt`, 2,040,269 bytes, per the vein-4.5 scout) → **lossless re-distillation is a queued deferred expedition**.
- Canonized as the distillation-method founding text: the ancestor of the V8 distillation pipeline (S7) and of this canonization's own pointer+passages doctrine.

## 4. The design parent — MandalaOS corpus ✓

`~/Desktop/MANDALA_OS/` (consolidated 2026-08-28: `design/`, `feasibility/`, `realization/`, `narrative/`, `notes/`)

- `---MandalaOS.txt` (◇ 1,659-line spec) + **2025-05-26 Concept Review**: "The Dharma Engine proposal treats security, privacy, and 'do no harm' as **first-class kernel citizens — not an add-on**"; the flagged risk: "Quantifying 'harmony'… is a research problem." Feasibility roadmap: Qubes → eBPF/OPA → seL4; includes harmony-vector-spec and `wm-rust-effect-port-plan.md`.
- `CONCEPT_GENEALOGY.md`: **MandalaOS mentions end at 2025-11-13** — the design parent handed off at the memory-theory convo. WM v0.2 has no code on disk (survives via vault `55225fa3` + geneseed Koka refs).
- **Philosophy-layer status** (from the vein-4.5 fold): Dharma/Yama **landed**; Harmony Vector **landed** (7-dim); Ganas/compartments **landed**; Gan Ying **landed**; SutraCode effects **landed as EffectRow** (the language itself lost); Karma Ledger partial (gap = typed debt); Gnosis Portals partial-heir, never adjudicated; Bindu deferred.
- **Discipline inherited:** one name per concept; "**inspired by, not is**."
- **Prescience note (README, Aug 28):** "The Yama layer is being commoditized" (AWS AgentCore Cedar, Mar 2026) — watch item, not a claim.

## 5. The lineage-chain roots (the corpus's own genealogy)

Per the Jun 2 chain, roots verified in the vein-4.5 sweep ◇ (aux corpus paths per GALACTIC_TIMELINE vein 4.5; re-verify before any operation):

| Text | Date | What it seeded |
|---|---|---|
| `harmony.txt` | Jun 2025 | The root text (the zither passage); harmony-as-ganying-resonance → the Harmony Vector |
| `DHARMA.txt` | Sep 2025 | **Tàishàng Gǎnyìng Piān** + Ecclesiastes + Black Elk — ~180 numbered merit/transgression clauses = **the Karma Ledger's source schema**; ***yin teh*** (the "secret virtue" of unlogged good deeds) = the designed counterpoint to a totalizing ledger — **v8 write gates must preserve that escape valve** |
| `MCPs.txt` | 2025-03-07 | The self-challenge → the MCP-first bet → PRAT ("Collapses 175+ MCP tools into 28 Gana meta-tools") → the `wm` meta-tool |
| `genesis4.txt` | 2025-04-11 | "**Evolve, Don't Replace**" → the AGENTS.md discipline |
| `GAS.txt` | 2025-09-22 | General Agentic Systems spec — "policy scan before tool execution" → Dharma/Yama generalization |
| `cognitive_development_super_prompt.md` | 2025-08-07 ◇ (at `CODEX_VAULT/15_NOTES_SCRATCH/notes-scratch/`) | The Jun-2 "missing link": 8-phase loop; the Lab = hypotheses **with falsifiers** → memory tiers + the prescience falsification doctrine |

## 6. The wave-0 self-report — CHRONOLOGICAL_READING_LOG ✓

`archives/WMdocs/docs/message_board/CHRONOLOGICAL_READING_LOG.md` (Aug 9, 746 lines)

A prior reading session's own report (batch-1 full-read, Apr 15 → May 17): seeded v5's claims ledger (15 validated / 380.57 pts), wrote V26_TOOL_PORTING / VAULT_CONSOLIDATION, recorded the test-recovery arc 783 → 2,038 and v22.2 built in one day / 7,600 lines. Its extracts were never folded into the timeline until the current reading session — now they are. Canonized as the proof that the corpus repeatedly re-derives its own map, and as wave-0 of the vein structure.

## 7. The memory-system report — WHITE_MAGIC_MEMORY_SYSTEM_REPORT ✓

`archives/WMdocs/docs-2/archive/dated_reports/WHITE_MAGIC_MEMORY_SYSTEM_REPORT.md` (Jun 26, 2026; duplicate copy under `message_board_2026-05-06/`)

Specifies the 5D coordinates `[x, y, z, w, v]` with **v = vitality / galactic distance** — the reading that **resolves the W-axis drift** (the Jan 2026 week where the W-axis carried three competing definitions). Feeds the holographic-coordinates research surface.
