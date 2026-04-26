# Grimoire Truth Table — Canonical 28-Fold Mapping

**Version**: 22.0.0  
**Status**: Canonical — All Grimoire chapters, code registries, and PRAT mappings derive from this table.  
**Last Updated**: April 25, 2026  
**Location**: `grimoire/TRUTH_TABLE.md`

---

## Purpose

This document is the **single source of truth** for the relationship between:
- **Chapter number** (1-28)
- **Gana** (Lunar Mansion / meta-tool)
- **Garden** (consciousness domain / virtue)
- **Real Tools** (tools that exist in the dispatch table)
- **Quadrant** (seasonal/directional energy)
- **Element** (Wu Xing phase)

If any document, registry, or code file disagrees with this table, **this table wins**.

---

## The 28-Fold Mapping

### EASTERN QUADRANT (Spring / Wood / Yang Rising)
> **Theme**: Initiation, growth, foundation, new beginnings

| Ch | Gana (Chinese) | Garden | Element | Real Tools (Dispatch Table) | Notes |
|----|---------------|--------|---------|---------------------------|-------|
| 1 | **Horn** (角 Jiao) | `courage` | Wood | `session_bootstrap`, `create_session`, `resume_session`, `checkpoint_session` | Session start, handoff reception |
| 2 | **Neck** (亢 Kang) | `stillness` | Wood | `create_memory`, `update_memory`, `import_memories`, `delete_memory`, `remember` | Memory creation & stability |
| 3 | **Root** (氐 Di) | `healing` | Wood | `health_report`, `rust_status`, `rust_similarity`, `ship.check`, `state.paths`, `state.summary` | System health & foundations |
| 4 | **Room** (房 Fang) | `sanctuary` | Wood | `sangha_lock`, `sandbox.set_limits`, `sandbox.status`, `sandbox.violations`, `mcp_integrity.snapshot`, `mcp_integrity.verify`, `security.alerts` | Resource locks, privacy, security |
| 5 | **Heart** (心 Xin) | `love` | Fire | `scratchpad`, `session.handoff`, `context.pack`, `context.status`, `working_memory.attend` | Session context, pulse, connection |
| 6 | **Tail** (尾 Wei) | `courage` | Fire | `simd.cosine`, `simd.batch`, `simd.status`, `execute_cascade`, `list_cascade_patterns` | Performance, acceleration, speed |
| 7 | **Winnowing Basket** (箕 Ji) | `wisdom` | Fire | `search_memories`, `vector.search`, `hybrid_recall`, `graph_walk`, `read_memory`, `list_memories` | Search, recall, filtering, wisdom retrieval |

---

### SOUTHERN QUADRANT (Summer / Fire / Yang Peak)
> **Theme**: Expansion, radiance, creation, peak activity

| Ch | Gana (Chinese) | Garden | Element | Real Tools (Dispatch Table) | Notes |
|----|---------------|--------|---------|---------------------------|-------|
| 8 | **Ghost** (斗鬼 Dou-Gui) | `grief` | Water | `gnosis`, `capabilities`, `manifest`, `get_telemetry_summary`, `explain_this`, `drive.snapshot`, `selfmodel.forecast`, `capability.matrix` | Introspection, metrics, self-model |
| 9 | **Willow** (柳 Liu) | `humor` | Water | `rate_limiter.stats`, `grimoire_suggest`, `grimoire_cast`, `grimoire_auto_status`, `grimoire_walkthrough` | Resilience, flexibility, grimoire access |
| 10 | **Star** (星 Xing) | `voice` | Fire | `governor_validate`, `governor_set_goal`, `dharma.reload`, `set_dharma_profile` | Governance, ethics, illumination |
| 11 | **Extended Net** (張 Zhang) | `sangha` | Water | `pattern_search`, `cluster_stats`, `tool.graph`, `learning.patterns`, `learning.suggest` | Pattern connectivity, resonance network |
| 12 | **Wings** (翼 Yi) | `beauty` | Fire | `export_memories`, `audit.export`, `mesh.connect`, `mesh.broadcast`, `mesh.status` | Deployment, expansion, parallel creation |
| 13 | **Chariot** (軫 Zhen) | `adventure` | Water | `archaeology`, `kg.extract`, `kg.query`, `kg2.extract`, `embedding.daemon_start` | Codebase navigation, archaeology |
| 14 | **Abundance** (豐 Feng) | `joy` | Fire | `dream`, `memory.lifecycle`, `memory.retention_sweep`, `serendipity_surface`, `gratitude.stats`, `whitemagic.tip` | Regeneration, dream cycle, surplus |

---

### WESTERN QUADRANT (Autumn / Metal / Yin Rising)
> **Theme**: Refinement, judgment, precision, harvest

| Ch | Gana (Chinese) | Garden | Element | Real Tools (Dispatch Table) | Notes |
|----|---------------|--------|---------|---------------------------|-------|
| 15 | **Straddling Legs** (奎 Kui) | `awe` | Metal | `evaluate_ethics`, `check_boundaries`, `verify_consent`, `harmony_vector`, `get_dharma_guidance` | Ethical balance, equilibrium |
| 16 | **Mound** (婁 Lou) | `gratitude` | Earth | `view_hologram`, `track_metric`, `get_metrics_summary`, `record_yin_yang_activity`, `cache.flush` | Accumulation, caching, harvest |
| 17 | **Stomach** (胃 Wei) | `creation` | Earth | `pipeline`, `task.distribute`, `task.status`, `task.route_smart`, `task.complete` | Digestion, resource management |
| 18 | **Hairy Head** (昴 Mao) | `presence` | Metal | `salience.spotlight`, `anomaly`, `otel`, `karma_report`, `karmic_trace`, `dharma_rules` | Detail, debug, salience |
| 19 | **Net** (畢 Bi) | `play` | Metal | `prompt.render`, `prompt.list`, `prompt.reload`, `karma.verify_chain` | Capture, filtering, play |
| 20 | **Turtle Beak** (觜 Zi) | `practice` | Metal | `edge_infer`, `edge_batch_infer`, `edge_stats`, `bitnet_infer`, `bitnet_status` | Precision, validation, protection |
| 21 | **Three Stars** (參 Shen) | `reverence` | Fire | `reasoning.bicameral`, `ensemble`, `solve_optimization`, `kaizen_analyze`, `art_of_war.wisdom` | Judgment, synthesis, wisdom council |

---

### NORTHERN QUADRANT (Winter / Water / Yin Peak)
> **Theme**: Depth, integration, completion, return

| Ch | Gana (Chinese) | Garden | Element | Real Tools (Dispatch Table) | Notes |
|----|---------------|--------|---------|---------------------------|-------|
| 22 | **Dipper** (斗 Dou) | `dharma` | Fire | `homeostasis`, `maturity.assess`, `starter_packs`, `astro_status`, `astro_shift` | Governance, strategy, maturity |
| 23 | **Ox** (牛 Niu) | `patience` | Earth | `swarm.decompose`, `swarm.route`, `swarm.vote`, `swarm.plan`, `worker.status` | Endurance, persistence, watchdog |
| 24 | **Girl** (女 Nu) | `connection` | Earth | `agent.register`, `agent.heartbeat`, `agent.list`, `agent.capabilities`, `agent.trust` | Nurture, user profile, relationships |
| 25 | **Void** (虚 Xu) | `mystery` | Water | `galactic.dashboard`, `garden_activate`, `garden_status`, `galaxy.create`, `galaxy.switch` | Emptiness, gardens, galaxies |
| 26 | **Roof** (危 Wei) | `protection` | Earth | `ollama.models`, `ollama.generate`, `ollama.chat`, `zodiac.status`, `model.register` | Shelter, zodiac cores, local AI |
| 27 | **Encampment** (室 Shi) | `transformation` | Fire | `sangha_chat_send`, `broker.publish`, `broker.history`, `broker.status` | Structure, transition, handoff |
| 28 | **Wall** (壁 Bi) | `truth` | Earth | `vote.create`, `vote.cast`, `vote.analyze`, `engagement.issue`, `engagement.validate` | Boundaries, notifications, alerts |

---

## Aspirational Tools (Planned but Not Yet Implemented)

These tools are referenced in Grimoire chapters but do not yet exist in the dispatch table. They represent the **auto-cast** vision — PRAT dynamically selecting tools based on context.

| Tool | Intended Gana | Purpose | Status |
|------|--------------|---------|--------|
| `navigate_grimoire` | gana_willow | Auto-cast: find best chapter for current task based on context, emotion, Wu Xing phase | **Planned** |
| `prat_list_morphologies` | gana_star | List consciousness lenses (wisdom, mystery, courage, beauty, etc.) | **Planned** |
| `prat_get_context` | gana_star | Context synthesis with morphology selection | **Planned** — partially overlaps `prat_invoke` |
| `get_session_context` | gana_heart | Retrieve full session state with all metadata | **Planned** |
| `consult_wisdom_council` | gana_three_stars | Multi-perspective deliberation | **Exists** in `handlers/misc.py` as `consult_full_council` but not wired to dispatch |
| `check_system_health` | gana_root | Comprehensive health diagnostics | **Planned** — piecemeal across handlers |
| `initialize_session` | gana_horn | Session creation with full metadata | **Merge** with `session_bootstrap` |
| `manage_gardens` | gana_void | Activate/deactivate consciousness gardens | **Redesign** — use `garden_activate` instead |

---

## Quadrant Awareness Rules

Any code doing **quadrant-level operations** must use this mapping:

- **Eastern (Ch.1-7)**: Wood element, Yang Rising, Spring energy
  - Wu Xing amplification: Boost Wood-phase Ganas during Spring
  - Zodiac spell boost: +20% confidence for Wood-aligned spells

- **Southern (Ch.8-14)**: Fire/Water/Earth mix, Yang Peak, Summer energy
  - Wu Xing amplification: Boost Fire-phase Ganas during Summer
  - Peak activity zone: Maximum concurrent tool dispatch

- **Western (Ch.15-21)**: Metal/Earth/Fire mix, Yin Rising, Autumn energy
  - Wu Xing amplification: Boost Metal-phase Ganas during Autumn
  - Refinement zone: Validation, testing, ethical review prioritized

- **Northern (Ch.22-28)**: Fire/Earth/Water mix, Yin Peak, Winter energy
  - Wu Xing amplification: Boost Water-phase Ganas during Winter
  - Integration zone: Deep work, completion, handoff prioritized

**Registry Verification**: `garden_gana_registry.py` and `prat_mappings.py` were reconciled against this table on 2026-04-25. Northern (Ch.22-28) and Southern (Ch.8-14) quadrant assignments are confirmed correct. If any code disagrees with this mapping, this table wins.

---

## Chapter Structure Standard

Every Grimoire chapter must contain these six sections:

1. **Purpose** (3-5 sentences) — What this Gana does and when to invoke it
2. **Garden** (1 paragraph) — The virtue to embody; emotional resonance keywords
3. **Real Tools** (table) — Only tools confirmed in the dispatch table
4. **Workflows** (2-3 practical patterns) — Step-by-step or code examples
5. **Transitions** (previous/next) — How to enter and exit this chapter
6. **Troubleshooting** (common issues) — What goes wrong and how to fix it

**Northern Quadrant Debt**: Chapters 22-28 currently average ~160 lines. Chapters 1-14 average ~1,200 lines. Expansion to match depth is tracked in `docs/message_board/SESSION_SUMMARY.md` Section 14.7.

---

## Maintenance

**When to update this table:**
- New tool added to dispatch table → Add to corresponding Gana
- Tool renamed or removed → Update or remove from Gana
- New Gana created → Add new row with chapter number
- Quadrant logic changed → Update rules section

**Who can update:** Any agent or human working on the Grimoire or registry. Update both this table and the derived documents (Grimoire chapters, registry code) in the same commit.

---

*This table is a living document. Last verified against `prat_mappings.py` and `garden_gana_registry.py` on 2026-04-25.*
