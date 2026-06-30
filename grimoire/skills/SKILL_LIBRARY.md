# WhiteMagic Skill Library

> **43 portable `SKILL.md` files** covering all 28 Ganas, 4 development workflows, and 7 Hermes-native integrations.
>
> Compatible with Claude Code, Codex CLI, Gemini CLI, Copilot, Cursor, Cline, Windsurf, and OpenCode.

**Version**: 23.3.1
**Location**: `grimoire/skills/`

---

## Gana Skills (28 files)

**Directory**: `ganas/`

The 28 Gana skills map 1:1 to the Chinese Lunar Mansions (Xiu 宿). Each skill documents the tools, workflows, and invocation patterns for its Gana.

| # | File | Gana | Skill Name | Description |
|---|------|------|------------|-------------|
| 1 | `01_horn_session_initiation.md` | gana_horn | wm-session | Session lifecycle — bootstrap, checkpoint, resume, handoff |
| 2 | `02_neck_memory_presence.md` | gana_neck | wm-memory | Create, update, search 5D holographic memories |
| 3 | `03_root_system_foundation.md` | gana_root | wm-system-health | System health, Rust backend, ship readiness |
| 4 | `04_room_resource_sanctuary.md` | gana_room | wm-security | Security, sandboxing, resource locks, MCP integrity |
| 5 | `05_heart_context_connection.md` | gana_heart | wm-context | Scratchpad, working memory, session context |
| 6 | `06_tail_performance_drive.md` | gana_tail | wm-acceleration | SIMD acceleration, cascade execution, hexagram dispatch |
| 7 | `07_winnowing_basket_consolidation.md` | gana_winnowing_basket | wm-search | Search, vector search, hybrid recall, graph walk |
| 8 | `08_ghost_metrics_introspection.md` | gana_ghost | wm-introspection | Self-awareness, coherence, capabilities, telemetry |
| 9 | `09_willow_adaptive_play.md` | gana_willow | wm-resilience | Grimoire spells, oracle casting, rate limiting |
| 10 | `10_star_prat_illumination.md` | gana_star | wm-governance | Dharma profiles, forge validation, goal setting |
| 11 | `11_extendednet_resonance_network.md` | gana_extended_net | wm-patterns | Pattern mining, associations, causal analysis, learning |
| 12 | `12_wings_parallel_creation.md` | gana_wings | wm-export | Export memories, backup/restore, mesh broadcast |
| 13 | `13_chariot_codebase_navigation.md` | gana_chariot | wm-research | Web research, archaeology, STRATA, browser, image analysis |
| 14 | `14_abundance_resource_sharing.md` | gana_abundance | wm-dream | Dream cycle, serendipity, gratitude, bounties |
| 15 | `15_straddlinglegs_ethical_balance.md` | gana_straddling_legs | wm-ethics | Ethics evaluation, boundaries, Wu Xing balance |
| 16 | `16_mound_strategic_patience.md` | gana_mound | wm-metrics | Metrics, caching, yin-yang, hologram view |
| 17 | `17_stomach_energy_management.md` | gana_stomach | wm-tasks | Task distribution, pipeline management, routing |
| 18 | `18_hairyhead_detailed_attention.md` | gana_hairy_head | wm-karma | Karma tracking, anomalies, OpenTelemetry, salience |
| 19 | `19_net_pattern_capture.md` | gana_net | wm-prompts | Prompt management, karma chain verification |
| 20 | `20_turtlebeak_precise_validation.md` | gana_turtle_beak | wm-edge | Edge inference, BitNet, edge rules |
| 21 | `21_threestars_wisdom_council.md` | gana_three_stars | wm-judgment | Bicameral reasoning, ensemble, kaizen, wisdom council |
| 22 | `22_dipper_governance.md` | gana_dipper | wm-strategy | Cognitive modes, homeostasis, maturity, starter packs |
| 23 | `23_ox_endurance.md` | gana_ox | wm-swarm | Swarm orchestration, war room, worker management |
| 24 | `24_girl_nurture.md` | gana_girl | wm-agents | Agent registration, heartbeat, trust, capabilities |
| 25 | `25_void_emptiness.md` | gana_void | wm-galaxy | Galaxy lifecycle — create, transfer, merge, sync |
| 26 | `26_roof_shelter.md` | gana_roof | wm-ollama | Local LLMs via Ollama, model signing, sovereign sandbox |
| 27 | `27_encampment_structure.md` | gana_encampment | wm-community | Event broker, GanYing emissions, sangha chat |
| 28 | `28_wall_boundaries.md` | gana_wall | wm-marketplace | Voting, engagement tokens, marketplace |

---

## Workflow Skills (4 files)

**Directory**: `workflows/`

| File | Skill Name | Description |
|------|------------|-------------|
| `wm-code-review.md` | wm-code-review | Code review for bugs, security, quality |
| `wm-release.md` | wm-release | Release process — version, changelog, tests, tag |
| `wm-audit.md` | wm-audit | Comprehensive system audit |
| `wm-deep-research.md` | wm-deep-research | Multi-source web research with synthesis |

---

## Development Skills (4 files)

**Directory**: `development/`

| File | Skill Name | Description |
|------|------------|-------------|
| `wm-add-tool.md` | wm-add-tool | Add new tool — registry, handler, dispatch, PRAT, tests |
| `wm-test-suite.md` | wm-test-suite | Test suite management — tiers, durations, purity |
| `wm-documentation.md` | wm-documentation | Doc conventions — INDEX.md, grimoire, drift |
| `wm-polyglot.md` | wm-polyglot | 7-language acceleration, graceful degradation |

---

## Hermes-Native Skills (7 files)

**Directory**: `hermes/`

These skills are designed for Hermes Agent's hook system and SKILL.md format.

| File | Skill Name | Description |
|------|------------|-------------|
| `wm-memory.md` | wm-memory | Memory operations with Hermes hook integration |
| `wm-research.md` | wm-research | Deep research with web search and synthesis |
| `wm-dream.md` | wm-dream | Dream cycle for background processing |
| `wm-codebase.md` | wm-codebase | STRATA, archaeology, codegenome analysis |
| `wm-cognitive.md` | wm-cognitive | Parallel reasoning, judgment, kaizen |
| `wm-session.md` | wm-session | Session lifecycle with context injection |
| `wm-system.md` | wm-system | System health monitoring |

---

## SkillForge (Internal)

WhiteMagic includes an internal `SkillForge` (`core/whitemagic/core/intelligence/omni/skill_forge.py`) that automatically crystallizes successful tool chains into reusable skills. When the Universal Router executes a chain with >80% success rate and >2 steps, the Forge saves it as a JSON skill file for future reuse.

**Status**: Wired but untested. The Forge writes to `memory/skills/` (should be under `WM_STATE_ROOT`). No tests exist for the Forge itself.

---

## Usage

### In Windsurf/Cascade IDE
Skills are already installed at `~/.codeium/windsurf/windsurf/skills/` (31 global) and `WHITEMAGIC/.windsurf/skills/` (4 workspace).

### In Claude Code
Copy any skill file to `.claude/skills/` in your project:
```bash
cp grimoire/skills/ganas/02_neck_memory_presence.md .claude/skills/wm-memory.md
```

### In Hermes Agent
Copy Hermes skills to `~/.hermes/skills/whitemagic/`:
```bash
cp -r grimoire/skills/hermes/* ~/.hermes/skills/whitemagic/
```

### In Codex CLI / Gemini CLI / Others
Follow each runtime's SKILL.md discovery convention. The format is portable.

---

## Relationship to MCP

Skills and MCP are complementary layers:
- **Skills** (this library) = the playbook — how to approach a task
- **MCP** (WhiteMagic's 490 tools) = the equipment — access to the system
- **Best practice**: Skills wrap MCP — the Skill defines the procedure, MCP provides the transport

See `skills_audit_and_library_plan.md` in `WHITEMAGIC-aux/surveys/` for the full audit and industry research.
