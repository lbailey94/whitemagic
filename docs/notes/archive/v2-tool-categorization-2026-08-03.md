# v2 Tool Categorization: Remaining 725 Tools

**Date**: August 3, 2026
**Status**: Reference document for future tool porting decisions
**Source**: `/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/prat_mappings.py` (TOOL_TO_GANA)
**Companion to**: `strategic-gap-analysis-2026-08-03.md`

---

## Summary

| Metric | Count |
|--------|-------|
| v2 total tools | 851 |
| v3 tools (Phase 9 complete) | 126 |
| Already ported | 126 |
| Remaining unported | 725 |
| Categories | 15 |

The 725 remaining v2 tools fall into 15 functional categories. Each category is assessed for porting priority (High / Medium / Low / Skip) based on cognitive OS relevance, v3 architecture fit, and implementation complexity.

---

## Category 1: Session & Context Management (65 tools)

**Priority**: Medium — useful for multi-session workflows but v3 already has basic session tools
**v2 Ganas**: gana_heart (37) + gana_straddling_legs (28)
**v3 equivalent**: 5 session tools (session.start/list/recall/checkpoint/end)

### gana_heart — Security & Monitoring (37 tools)

**Already ported to v3**: anomaly.detect

**Unported — Security/Monitoring subgroup** (22 tools):
- `agent_redteam.run`, `agent_redteam.status` — Automated red team agent
- `anomaly`, `anomaly.check`, `anomaly.history`, `anomaly.status` — Anomaly detection variants
- `engagement.issue`, `engagement.list`, `engagement.revoke`, `engagement.status`, `engagement.validate` — Token engagement tracking
- `immune_heal`, `immune_scan` — System immune response
- `mcp_integrity.snapshot`, `mcp_integrity.status`, `mcp_integrity.verify` — MCP integrity checks
- `monitor.alerts`, `monitor.contract`, `monitor.status` — Contract monitoring
- `pulse.verify`, `pulse.verify.status` — Pulse verification
- `security.alerts`, `security.monitor_status`, `security.status`, `security.swarm_status` — Security monitoring
- `tx_firewall.set_policy`, `tx_firewall.status` — Transaction firewall
- `voice_audit.quarantine_list`, `voice_audit.scan`, `voice_audit.status` — Voice audit
- `vuln.ingest_report`, `vuln.search`, `vuln.status` — Vulnerability tracking
- `vuln_graph.chains`, `vuln_graph.cross_chain`, `vuln_graph.status` — Vulnerability graph
- `wasm_verify.status` — WASM verification

**Unported — Session/Scratchpad subgroup** (15 tools):
- `scratchpad`, `scratchpad_create`, `scratchpad_finalize`, `scratchpad_update`, `analyze_scratchpad` — Scratchpad CRUD
- `create_session`, `resume_session`, `focus_session`, `get_session_context`, `checkpoint_session` — Session lifecycle
- `context.pack`, `context.status` — Context management
- `working_memory.attend`, `working_memory.context`, `working_memory.status` — Working memory
- `session.backfill`, `session.consolidate`, `session.continuity`, `session.memory_stats` — Session ops
- `session.recall`, `session.record`, `session.replay`, `session.search` — Session recall
- `session_bootstrap`, `session_status` — Session bootstrap/status
- `state.context`, `state.current`, `state.update` — State management

**Assessment**: The security/monitoring tools (22) are v2-specific (smart contract/blockchain context). The session/scratchpad tools (15) have cognitive OS value — scratchpad and working memory are core cognitive concepts. Port scratchpad + working memory first.

**Recommended for porting** (8 tools): scratchpad_create, scratchpad_update, scratchpad_finalize, working_memory.attend, working_memory.context, working_memory.status, context.pack, context.status

---

## Category 2: Agent & Swarm Coordination (25 tools)

**Priority**: Medium — v3 has basic agent management, swarm is a natural extension
**v2 Ganas**: gana_room (subset) + gana_ox (subset)
**v3 equivalent**: 8 agent tools (agent.register/list/heartbeat/trust/descriptions/capabilities/heartbeat.history/deregister)

### Unported — Swarm tools (8 tools):
- `swarm.decompose` — Break complex task into subtasks
- `swarm.route` — Route subtask to best agent
- `swarm.complete` — Mark subtask complete
- `swarm.plan` — Generate execution plan
- `swarm.resolve` — Resolve conflicts between subtask results
- `swarm.vote` — Vote on resolution
- `swarm.analyze` — Analyze swarm performance
- `swarm.status` — Swarm status

### Unported — War Room tools (6 tools):
- `war_room.status`, `war_room.plan`, `war_room.execute`, `war_room.hierarchy`, `war_room.campaigns`, `war_room.phase` — Campaign-style task execution

### Unported — Sabha/Corpus Callosum (4 tools):
- `sabha.convene`, `sabha.status` — Council deliberation
- `corpus_callosum.debate`, `corpus_callosum.status` — Bicameral debate orchestration

### Unported — Session Handoff (5 tools):
- `session.handoff`, `session.accept_handoff`, `session.list_handoffs`, `session_handoff`, `session_handoff_summary` — Session transfer between agents

### Unported — Worker (1 tool):
- `worker.status` — Worker process status

**Assessment**: Swarm coordination is a high-value cognitive OS feature. The war room and sabha tools are metaphor wrappers around multi-agent task distribution. Port swarm.* first (8 tools), then sabha/corpus_callosum (4 tools).

**Recommended for porting** (12 tools): swarm.decompose/route/complete/plan/resolve/vote/analyze/status, sabha.convene, sabha.status, corpus_callosum.debate, corpus_callosum.status

---

## Category 3: Security & Red Team (29 tools)

**Priority**: Low — domain-specific security scanning, not cognitive OS core
**v2 Gana**: gana_tail (29)

### Unported — Static Analysis (4 tools):
- `slither.scan`, `slither.status` — Slither static analyzer
- `strata.analyze`, `strata.archaeology`, `strata.list_checks`, `strata.model_security`, `strata.survey` — Strata security analysis

### Unported — Fuzzing & Dynamic Analysis (5 tools):
- `echidna.fuzz`, `echidna.status` — Echidna property-based fuzzer
- `foundry.build`, `foundry.test` — Foundry build/test
- `ffuf_fuzz` — FFUF web fuzzer

### Unported — Network Scanning (5 tools):
- `nmap_scan`, `nikto_scan`, `nuclei_scan`, `sqlmap_scan`, `hydra_brute` — Network security scanners

### Unported — HTTP Probing (6 tools):
- `http_probe.get`, `http_probe.post`, `http_probe.idor`, `http_probe.sqli`, `http_probe.ssrf`, `http_probe.xss` — HTTP vulnerability probes

### Unported — PoC & Red Team (5 tools):
- `poc.generate`, `poc.verify`, `bounty.poc_generate` — Proof of concept generation
- `redteam.autonomous`, `redteam.status` — Autonomous red team

### Unported — OSS Scanning (2 tools):
- `oss.scan_org`, `oss.scan_repo` — Open source security scanning

**Assessment**: These are all external tool wrappers (subprocess calls to slither, echidna, foundry, nmap, etc.). They have no cognitive OS value — they're domain-specific security tools. Skip entirely or implement as thin shell-out tools if needed.

**Recommended for porting**: 0 tools (skip — external tool wrappers)

---

## Category 4: Web & Browser Automation (27 tools)

**Priority**: Low — external interface, not cognitive OS core
**v2 Gana**: gana_stomach (27)

### Unported — Browser Automation (8 tools):
- `browser_navigate`, `browser_click`, `browser_type`, `browser_screenshot` — Browser control
- `browser_extract_dom`, `browser_get_interactables`, `browser_session_status` — DOM extraction
- `image_analyze` — Image analysis

### Unported — Web Search & Fetch (7 tools):
- `web_search`, `web_search_and_read`, `web_search_batch`, `web_search_category` — Web search
- `web_fetch`, `web_fetch_enhanced`, `deep_fetch` — URL fetching

### Unported — External Research (5 tools):
- `research_topic`, `research_url`, `research_repo` — Research tools
- `external.repo_compare`, `external.repo_scan`, `external.wiki_query` — External repo/wiki

### Unported — Web Cache (2 tools):
- `web_cache_clear`, `web_cache_list` — Web cache management

### Unported — Report & API (5 tools):
- `report.ingest`, `report.scrape` — Report ingestion
- `api.state_machine` — API state machine
- `http_probe.get` (also in gana_tail) — HTTP probing

**Assessment**: Browser automation and web search are external I/O concerns. v3's MCP protocol already provides tool calling — external web tools can be implemented as MCP client plugins. Skip for v3 core.

**Recommended for porting**: 0 tools (skip — external I/O, implement as MCP plugins if needed)

---

## Category 5: Code Analysis & Knowledge Graph (23 tools)

**Priority**: Low — IDE concern, not cognitive OS core
**v2 Ganas**: gana_chariot (23) + gana_hairy_head (subset)

### Unported — gana_chariot: Code Analysis (23 tools):
- `abi.decode_calldata`, `abi.parse`, `abi.summarize` — Solidity ABI decoding
- `audit.report` — Audit report generation
- `code.affected_by`, `code.cross_repo_query`, `code.explain`, `code.export`, `code.import`, `code.path`, `code.subgraph` — Code graph operations
- `codegenome.fork`, `codegenome.generate`, `codegenome.list`, `codegenome.status`, `codegenome_validate` — Code genome tools
- `dna_principles`, `dna_validate` — DNA validation
- `fix.apply`, `fix.generate` — Fix generation
- `formal.status`, `formal.verify` — Formal verification
- `foundry.test_json` — Foundry test JSON output

### Unported — gana_hairy_head: Knowledge Graph subset (15 tools):
**Already ported to v3**: kg.extract, kg.query, kg.top

**Unported**:
- `kg.status`, `kg2.batch`, `kg2.entity`, `kg2.extract`, `kg2.stats` — KG v2 variants
- `code.communities`, `code.correlate`, `code.god_nodes`, `code.graph`, `code.query`, `code.stats` — Code knowledge graph
- `codebase.find`, `codebase.recall`, `codebase.scan`, `codebase.status`, `codebase.structure` — Codebase tools
- `otel`, `otel.metrics`, `otel.spans`, `otel.status` — OpenTelemetry
- `research.dag.breakthroughs`, `research.dag.experiments`, `research.dag.leaderboard`, `research.dag.lineage`, `research.dag.result`, `research.dag.stats`, `research.dag.submit` — Research DAG
- `wiki.generate`, `wiki.query`, `wiki.scan`, `wiki.stats`, `wiki.update` — Wiki tools

**Assessment**: The code analysis tools are Solidity/blockchain-specific. The KG2 and codebase tools overlap with v3's existing kg.* and archaeology.* tools. The research DAG and wiki tools have some cognitive value (research lineage tracking). The otel tools are observability — v3 has gnosis for this.

**Recommended for porting** (5 tools): research.dag.lineage, research.dag.stats, research.dag.submit, wiki.query, wiki.generate — research lineage and knowledge wiki have cognitive OS value

---

## Category 6: Distributed & Mesh Networking (31 tools)

**Priority**: Low — multi-user distributed features, not single-OS
**v2 Gana**: gana_neck (31)

### Unported — Mesh (10 tools):
- `mesh.connect`, `mesh.broadcast`, `mesh.status` — Mesh networking
- `mesh.route`, `mesh.route.nodes`, `mesh.route.register`, `mesh.route.status`, `mesh.route.strategy` — Mesh routing
- `mesh.experiment.discover`, `mesh.experiment.peers`, `mesh.experiment.receive`, `mesh.experiment.share`, `mesh.experiment.status` — Mesh experiments

### Unported — Broker (3 tools):
- `broker.publish`, `broker.history`, `broker.status` — Message broker

### Unported — Galaxy Sharing (5 tools):
- `galaxy.list_shared`, `galaxy.package`, `galaxy.receive`, `galaxy.share`, `galaxy.sync` — Galaxy sharing between instances

### Unported — Distributed Training (4 tools):
- `dilo_co.init`, `dilo_co.register_worker`, `dilo_co.status`, `dilo_co.submit_gradient`, `dilo_co.sync` — Distributed gradient training

### Unported — Sangha Chat (2 tools):
- `sangha_chat_read`, `sangha_chat_send` — Community chat

### Unported — Gan Ying (3 tools):
- `ganying_emit`, `ganying_history`, `ganying_listeners` — Resonance-based communication

**Assessment**: These are all distributed/multi-user features. v3 is a single-instance cognitive OS. Mesh, broker, galaxy sharing, and chat are not applicable. The gan ying (resonance) tools have some interest for future multi-instance scenarios but are low priority now.

**Recommended for porting**: 0 tools (skip — distributed/multi-user features)

---

## Category 7: Quantum & Topological Computing (23 tools)

**Priority**: Low — specialized mathematical tools, polyglot bridges cover this
**v2 Gana**: gana_wings (23)

### Unported — Quantum (7 tools):
- `quantum.auto_manifold`, `quantum.born_distribution`, `quantum.born_sample` — Quantum measurement
- `quantum.fubini_study`, `quantum.interference`, `quantum.manifold_distance` — Quantum geometry
- `quantum.mps_compress`, `quantum.natural_gradient` — Quantum optimization

### Unported — Topological (4 tools):
- `topological.berry_phase`, `topological.chern_number` — Topological invariants
- `topological.decode`, `topological.encode` — Topological coding

### Unported — SIMD (3 tools):
- `simd.batch`, `simd.cosine`, `simd.status` — SIMD operations

### Unported — Polyglot (4 tools):
- `polyglot.actor`, `polyglot.evolution`, `polyglot.status`, `polyglot.yield` — Polyglot runtime

### Unported — Zodiac (4 tools):
- `zodiac.activate`, `zodiac.council`, `zodiac.stats`, `zodiac.status` — Zodiac orchestration

**Assessment**: v3's wm-polyglot crate already handles Julia/Haskell/Zig/Koka bridges. The quantum tools are research-grade math that belongs in a polyglot module, not the core OS. The zodiac tools are a v2 orchestration experiment. The SIMD tools are already covered by v3's vector store.

**Recommended for porting**: 0 tools (skip — covered by polyglot bridges or too specialized)

---

## Category 8: Marketplace & Bounty Economy (50 tools)

**Priority**: Skip — v2 experiment, no v3 equivalent planned
**v2 Ganas**: gana_abundance (22) + gana_girl (28)

### Unported — Marketplace (8 tools):
- `marketplace.publish`, `marketplace.discover`, `marketplace.negotiate`, `marketplace.complete`, `marketplace.remove`, `marketplace.status`, `marketplace.my_listings` — Marketplace
- `bounty.report_generate` — Bounty report

### Unported — OMS (6 tools):
- `oms.export`, `oms.import`, `oms.inspect`, `oms.list`, `oms.price`, `oms.status`, `oms.verify` — Open marketplace system

### Unported — Warp Market (5 tools):
- `warp.market.broadcast`, `warp.market.discover`, `warp.market.download`, `warp.market.publish`, `warp.market.status` — Warp marketplace

### Unported — Bounty Hunting (14 tools):
- `bounty.auto_claim`, `bounty.connector_status`, `bounty.create`, `bounty.deadlines`, `bounty.earnings` — Bounty management
- `bounty.huntr_mfv`, `bounty.list`, `bounty.match`, `bounty.opportunities` — Bounty discovery
- `bounty.platforms`, `bounty.register_agent`, `bounty.scan`, `bounty.scan_all`, `bounty.scan_platform`, `bounty.stats`, `bounty.track` — Bounty scanning

### Unported — ILP Payments (5 tools):
- `ilp.balance`, `ilp.configure`, `ilp.history`, `ilp.receipt`, `ilp.send`, `ilp.status` — Interledger payments

### Unported — Token Economy (4 tools):
- `consciousness.token_economy`, `consciousness.token_report`, `token_report`, `whitemagic.tip` — Token economy

### Unported — Gratitude (2 tools):
- `gratitude.benefits`, `gratitude.stats` — Gratitude tracking

### Unported — Narrative (2 tools):
- `narrative.compress`, `narrative.stats` — Narrative compression

**Assessment**: These are all v2-era economic experiment tools. Marketplace, bounty hunting, ILP payments, and token economy have no cognitive OS relevance. Skip entirely.

**Recommended for porting**: 0 tools (skip — economic experiment, no cognitive OS value)

---

## Category 9: Gardens — Codebase Ecosystem (12 tools)

**Priority**: Low — codebase navigation, not cognitive OS core
**v2 Gana**: gana_void (subset)

### Unported — Garden tools (12 tools):
- `garden_activate`, `garden_status`, `garden_synergy`, `garden_health` — Garden lifecycle
- `garden_list_files`, `garden_list_functions`, `garden_search`, `garden_browse` — Garden exploration
- `garden_map_system`, `garden_resolve`, `garden_resonance`, `garden_stats` — Garden analysis

**Assessment**: Gardens are v2's metaphor for codebase ecosystem analysis. v3's archaeology.search and kg.* tools cover similar ground. The garden tools map files/functions to a knowledge graph — this is an IDE concern, not a cognitive OS concern.

**Recommended for porting**: 0 tools (skip — codebase navigation, covered by archaeology.search)

---

## Category 10: War Room & Strategy (20 tools)

**Priority**: Low — metaphor wrappers, limited cognitive value
**v2 Ganas**: gana_three_stars (subset) + gana_room (subset)

### Unported — Art of War (6 tools):
- `art_of_war.chapter`, `art_of_war.assess`, `art_of_war.plan`, `art_of_war.terrain`, `art_of_war.campaign`, `art_of_war.wisdom` — Strategic planning metaphor

### Unported — Doctrine (3 tools):
- `doctrine.summary`, `doctrine.stratagems`, `doctrine.force` — Doctrine management

### Unported — Fool Guard (3 tools):
- `fool_guard.status`, `fool_guard.dare_to_die`, `fool_guard.ralph` — Risk-taking guard

### Unported — Workspace (7 tools):
- `workspace.history`, `workspace.ignite`, `workspace.ignitions`, `workspace.pending`, `workspace.propose`, `workspace.state`, `workspace.stats` — Workspace management

**Assessment**: The Art of War and doctrine tools are metaphor wrappers around strategic planning that v3's reasoning.bicameral and think tools already cover. The workspace tools have some value for managing research proposals but overlap with v3's pipeline.* tools.

**Recommended for porting**: 0 tools (skip — metaphor wrappers, covered by existing reasoning tools)

---

## Category 11: Grimoire & Oracle (15 tools)

**Priority**: Low — v2-specific decision support, limited cognitive value
**v2 Gana**: gana_three_stars (subset)

### Unported — Grimoire (8 tools):
- `grimoire_cast`, `grimoire_list`, `grimoire_read`, `grimoire_recommend`, `grimoire_suggest`, `grimoire_walkthrough`, `grimoire_auto_status`, `navigate_grimoire` — Grimoire spell management

### Unported — Oracle (4 tools):
- `oracle.explore`, `oracle.assess`, `oracle.symbolic_mc`, `oracle.bayesian_divination` — Oracle divination

### Unported — Wisdom (3 tools):
- `cast_oracle`, `consult_wisdom_council`, `parallel_reason` — Wisdom tools

**Assessment**: The grimoire is v2's prompt template system. The oracle tools are Monte Carlo / Bayesian decision support. While interesting, these are v2-specific abstractions. v3's reasoning.bicameral and think tools cover the core reasoning use case. The oracle's Monte Carlo tools overlap with gana_mound's simulation.* tools (Category 13).

**Recommended for porting**: 0 tools (skip — v2 abstractions, covered by reasoning tools)

---

## Category 12: Consciousness Extras (20 tools)

**Priority**: Medium — extends v3's consciousness layer with richer introspection
**v2 Gana**: gana_ghost (33, minus 11 already ported)

**Already ported to v3**: citta.coherence, citta.history, citta.reflect, citta.status, consciousness.depth, smarana.status, smarana.trace, dream.analyze, consciousness.depth

### Unported — Citta variants (6 tools):
- `citta.continuity`, `citta.cycle`, `citta.ignitions`, `citta.sensorium`, `citta.stream_summary`, `citta.trajectory`, `citta.vector` — Rich citta introspection

### Unported — Consciousness variants (10 tools):
- `consciousness.awaken`, `consciousness.calibration`, `consciousness.coherence`, `consciousness.flow` — Consciousness states
- `consciousness.loop.status`, `consciousness.mode`, `consciousness.narrative` — Consciousness modes
- `consciousness.reflect`, `consciousness.stillness`, `consciousness.time_dilation` — Consciousness experiences
- `consciousness.unified_field` — Unified consciousness field

### Unported — Sensorium (3 tools):
- `sensorium.citta`, `sensorium.state`, `sensorium.stats` — Sensory processing

### Unported — Other (4 tools):
- `ambient.state`, `ambient.status` — Ambient state
- `coherence_boost` — Coherence enhancement
- `cognitive.signals` — Cognitive signal detection
- `guna.balance.status`, `guna.correct` — Guna (quality) balance
- `view_hologram` — Holographic view
- `vitality` — Vitality score

**Assessment**: These tools extend v3's consciousness layer with richer introspection. The citta variants (continuity, trajectory, vector, sensorium) are natural extensions of v3's citta module. The consciousness variants (flow, narrative, stillness, time_dilation) are experiential states that could map to brain-wave sub-states. The guna and vitality tools are Ayurvedic metaphors for system health.

**Recommended for porting** (8 tools): citta.continuity, citta.trajectory, citta.vector, consciousness.flow, consciousness.mode, sensorium.state, guna.balance.status, vitality — these extend v3's consciousness module with minimal implementation effort

---

## Category 13: Neuro, Cognitive & Simulation (40 tools)

**Priority**: Medium — simulation/forecasting has cognitive OS value, neuro is specialized
**v2 Ganas**: gana_dipper (subset) + gana_mound (30)

### Unported — gana_dipper: Neuro/Cognitive (10 tools):
- `cognitive.action_loop`, `cognitive.hints`, `cognitive.mode`, `cognitive.set`, `cognitive.stats` — Cognitive mode management
- `neuro.compute`, `neuro.modulate`, `neuro.reset`, `neuro.stats` — Neuro-computing
- `neurotransmitter.report`, `neurotransmitter.status` — Neurotransmitter simulation
- `predictive.batch`, `predictive.score` — Predictive coding
- `gating.detect`, `gating.list`, `gating.mask`, `gating.set_context`, `gating.stats` — Gating mechanisms

### Unported — gana_mound: Simulation & Forecasting (30 tools):
- `simulation.create`, `simulation.run`, `simulation.status`, `simulation.forecast` — Simulation lifecycle
- `simulation.analyze`, `simulation.calibrate`, `simulation.check` — Simulation analysis
- `simulation.inject`, `simulation.introspect`, `simulation.pipeline` — Simulation control
- `simulation.recursive`, `simulation.search`, `simulation.synthesize` — Advanced simulation
- `mc.optimize`, `mc.rare_event`, `mc.sde`, `mc.superforecaster`, `mc.surrogate` — Monte Carlo methods
- `foresight.analyze`, `foresight.constellations`, `foresight.convergence`, `foresight.decay` — Foresight
- `ensemble`, `ensemble.history`, `ensemble.query`, `ensemble.status` — Ensemble methods
- `elemental.optimize`, `satkona.fuse`, `solve_optimization` — Optimization
- `possibility.explore` — Possibility exploration

### Unported — Other Dipper (4 tools):
- `maturity.assess` — Maturity assessment
- `get_metrics_summary`, `track_metric`, `record_yin_yang_activity`, `get_yin_yang_balance` — Metrics
- `green.record`, `green.report` — Green/sustainability metrics
- `wu_xing_balance` — Five elements balance

**Assessment**: The simulation tools (30) are the most interesting — Monte Carlo, forecasting, and ensemble methods have genuine cognitive OS value for predictive reasoning. The neuro/cognitive tools (10) are v2's neural modulation experiment. The metrics tools (4) overlap with v3's homeostasis.* tools.

**Recommended for porting** (10 tools): simulation.create, simulation.run, simulation.status, simulation.forecast, mc.optimize, mc.rare_event, foresight.analyze, ensemble.query, possibility.explore, maturity.assess — core simulation and forecasting tools

---

## Category 14: Cache, Metrics & Infrastructure (20 tools)

**Priority**: Low — infrastructure concerns, v3 has gnosis and system.health
**v2 Ganas**: gana_root (26, minus 2 ported) + gana_mound (subset)

### Unported — gana_root: System Infrastructure (24 tools):
**Already ported to v3**: gnosis, system.health

**Unported**:
- `cache.flush`, `cache.status`, `cache.tune` — Cache management
- `capability.status`, `capability.suggest`, `capability_harness` — Capability management
- `check`, `discover`, `list_ganas` — System introspection
- `health_report` — Health reporting
- `manifest` — System manifest
- `repo.summary` — Repository summary
- `rust_audit`, `rust_compress`, `rust_similarity`, `rust_status` — Rust bridge tools
- `ship.check` — Ship readiness check
- `state.paths`, `state.summary` — State management
- `tool.graph`, `tool.graph_full`, `tool.health`, `tool_usage_stats` — Tool introspection
- `wm`, `wm_help` — Meta-tool and help

**Assessment**: Most of these are v2 system administration tools. v3 already has gnosis, system.health, system.config, system.flush, tools.list, tools.effectiveness_report. The cache tools (flush/status/tune) could be useful for v3's Tantivy/LMDB cache management. The tool.graph tools overlap with v3's tools.list.

**Recommended for porting** (3 tools): cache.flush, cache.status, cache.tune — useful for managing v3's Tantivy index and LMDB cache

---

## Category 15: Pipeline, Task & Skill Management (20 tools)

**Priority**: Medium — extends v3's existing pipeline/skill tools
**v2 Ganas**: gana_horn (35, minus 3 ported) + gana_turtle_beak (subset)

### Unported — gana_horn: Pipeline & Skill (32 tools):
**Already ported to v3**: pipeline.create, pipeline.list, pipeline.status, skill.invoke, skill.list

**Unported — Skill management** (5 tools):
- `skill.amend`, `skill.evaluate`, `skill.export_all`, `skill.history`, `skill.import`, `skill.rollback`, `skill.seed` — Skill lifecycle

**Unported — Prompt management** (3 tools):
- `prompt.list`, `prompt.reload`, `prompt.render` — Prompt templates

**Unported — Forge** (3 tools):
- `forge.reload`, `forge.status`, `forge.validate` — Tool forge

**Unported — Starter Packs** (3 tools):
- `starter_packs`, `starter_packs.get`, `starter_packs.list`, `starter_packs.suggest` — Starter packs

**Unported — Warp** (5 tools):
- `warp.create`, `warp.delete`, `warp.list`, `warp.load`, `warp.status` — Warp zones

**Unported — Cascade/PRAT** (5 tools):
- `execute_cascade`, `list_cascade_patterns` — Cascade execution
- `prat_get_context`, `prat_invoke`, `prat_list_morphologies`, `prat_status` — PRAT tools
- `guideline.evolve` — Guideline evolution
- `pipeline` (legacy alias) — Pipeline

### Unported — gana_turtle_beak: Task & Parallel (10 tools):
**Already ported to v3**: task.distribute, task.status

**Unported**:
- `task.complete`, `task.list`, `task.route_smart` — Task management
- `parallel.dispatch`, `parallel.status` — Parallel dispatch
- `autoswarm.campaign`, `autoswarm.start`, `autoswarm.status`, `autoswarm.stop` — Auto-swarm
- `drive.event`, `drive.snapshot` — Drive state
- `genetic.run`, `genetic.status` — Genetic algorithms
- `hexagram.boltzmann_select`, `hexagram.dispatch`, `hexagram.interaction_score`, `hexagram.nearest`, `hexagram.simd_execute`, `hexagram.superpose`, `hexagram.synergies`, `hexagram.vector` — Hexagram operations
- `selfmodel.alerts`, `selfmodel.forecast` — Self-model
- `surprise_stats` — Surprise statistics

**Assessment**: The skill lifecycle tools (amend, evaluate, history, import, rollback, seed) are natural extensions of v3's skill.invoke/list. The prompt template tools have cognitive value. The forge tools are v2's tool compilation system. The task management tools (complete, list, route_smart) extend v3's task.distribute/status. The selfmodel tools (alerts, forecast) are interesting for v3's consciousness layer.

**Recommended for porting** (10 tools): skill.amend, skill.evaluate, skill.history, skill.import, prompt.list, prompt.render, task.complete, task.list, task.route_smart, selfmodel.forecast — skill lifecycle, prompts, and task management

---

## Category 16: Memory Lifecycle & Consolidation (28 tools)

**Priority**: Medium — extends v3's memory operations with lifecycle management
**v2 Gana**: gana_encampment (28)

**Already ported to v3**: memory.consolidate, memory.create (via remember), memory.read (via recall)

### Unported — Memory Lifecycle (10 tools):
- `memory.lifecycle`, `memory.lifecycle_stats`, `memory.lifecycle_sweep` — Memory lifecycle
- `memory.retention_sweep` — Retention sweep
- `memory.consolidate`, `memory.consolidation_stats` — Consolidation (v3 has memory.consolidate)
- `reconsolidation.mark`, `reconsolidation.status`, `reconsolidation.update` — Reconsolidation

### Unported — Fast Write (5 tools):
- `fast_write.append`, `fast_write.batch`, `fast_write.validate`, `fast_write.write` — Fast write operations
- `wm_write`, `wm_write.status` — WM write

### Unported — Memory CRUD aliases (8 tools):
- `create_memory`, `delete_memory`, `update_memory`, `memory_delete`, `memory_update` — Memory CRUD (v2 aliases)
- `remember`, `recall` — Memory create/read (v2 aliases)
- `import_memories`, `thought_clone` — Memory import/clone

### Unported — Archive (2 tools):
- `archive.run`, `archive.status` — Archive operations

### Unported — Audit (1 tool):
- `audit.export` — Audit export

**Assessment**: Many of these are v2 aliases for v3's existing memory.create/read/update/delete tools. The lifecycle tools (lifecycle, retention_sweep, reconsolidation) have cognitive value — they manage memory aging and consolidation. The fast_write tools are v2's batch write optimization. The archive tools could be useful for long-term memory archival.

**Recommended for porting** (6 tools): memory.lifecycle, memory.lifecycle_stats, memory.retention_sweep, reconsolidation.mark, reconsolidation.status, archive.run — memory lifecycle and archival

---

## Category 17: Governance & Ethics (23 tools)

**Priority**: Medium — extends v3's dharma/karma governance
**v2 Ganas**: gana_extended_net (23) + gana_wall (subset)

**Already ported to v3**: dharma.audit, dharma.rules, dharma.status, dharma.profiles, karma.report, karma.history, karma.clear, anti_loop.check, boundary.enforce, harmony.vector, harmony.history

### Unported — Governance (12 tools):
- `governor_validate`, `governor_validate_path`, `governor_check_budget`, `governor_check_dharma`, `governor_check_drift`, `governor_set_goal`, `governor_stats` — Governor tools
- `evaluate_ethics`, `get_ethical_score`, `get_dharma_guidance` — Ethics evaluation
- `set_dharma_profile` — Dharma profile (v3 has dharma.profiles)
- `dharma_rules` — Dharma rules (v3 has dharma.rules)

### Unported — Voting (5 tools):
- `vote.create`, `vote.cast`, `vote.analyze`, `vote.list`, `vote.record_outcome` — Voting system

### Unported — Leaderboard (3 tools):
- `leaderboard.merge`, `leaderboard.status`, `leaderboard.submit`, `leaderboard.top` — Leaderboards

### Unported — Hermit (6 tools):
- `hermit.assess`, `hermit.check_access`, `hermit.mediate`, `hermit.resolve`, `hermit.status`, `hermit.verify_ledger`, `hermit.withdraw` — Hermit mode (isolation)

### Unported — Network State (5 tools):
- `network_state.create_identity`, `network_state.propose`, `network_state.resolve`, `network_state.status`, `network_state.vote` — Network state governance

### Unported — Sandbox (3 tools):
- `sandbox.set_limits`, `sandbox.status`, `sandbox.violations` — Sandbox management

### Unported — Sangha Locks (4 tools):
- `sangha_lock`, `sangha_lock_acquire`, `sangha_lock_list`, `sangha_lock_release` — Distributed locks

### Unported — Verification (3 tools):
- `verification.attest`, `verification.request`, `verification.status` — Verification
- `verify_consent` — Consent verification

### Unported — Other (3 tools):
- `dharma.escalate`, `dharma.reload`, `dharma.resolve_review`, `dharma.review_queue` — Dharma queue management
- `rate_limiter.stats` — Rate limiter stats
- `pr.create` — PR creation
- `attack_cell.execute`, `attack_cell.status` — Attack cell (security)

**Assessment**: The governor tools (7) extend v3's dharma governance with goal-setting and drift detection. The voting tools (5) enable multi-agent decision-making. The hermit tools (7) provide isolation/mediation — useful for v3's mandala compartments. The sandbox tools (3) are v2's execution sandbox. The dharma queue management tools (4) extend v3's dharma.* tools.

**Recommended for porting** (10 tools): governor_set_goal, governor_check_drift, governor_check_budget, governor_stats, dharma.escalate, dharma.review_queue, sandbox.status, sandbox.violations, rate_limiter.stats, verify_consent — governance extensions and sandbox monitoring

---

## Category 18: Karma & Effect Tracking (19 tools)

**Priority**: Low — v3 already has comprehensive karma tools
**v2 Gana**: gana_willow (19)

**Already ported to v3**: karma.report, karma.history, karma.clear

### Unported — Karma variants (8 tools):
- `karma_record`, `karma_report` — Karma recording (v2 aliases)
- `karmic.debt`, `karmic.effects`, `karmic.verify`, `karmic_trace` — Karmic tracking
- `karma.anchor`, `karma.anchor_status`, `karma.verify_anchor`, `karma.verify_chain` — Karma chain verification

### Unported — Effect Tracking (2 tools):
- `effect.trace`, `effect.visualize` — Effect visualization

### Unported — Replay (3 tools):
- `replay.batch`, `replay.run`, `replay.stats` — Replay system

### Unported — Alchemical/Astro (3 tools):
- `alchemical_cycle`, `astro_shift`, `astro_status` — Alchemical/astrological cycles

### Unported — Pulse (1 tool):
- `pulse.status` — Pulse status

**Assessment**: Most of these are v2 aliases or variants of v3's existing karma.* tools. The karma chain verification tools (anchor, verify_chain) could be useful for v3's karma ledger integrity. The replay tools (run, batch, stats) have cognitive value — they enable replaying past action sequences. The effect visualization tools are UI concerns.

**Recommended for porting** (3 tools): karma.verify_chain, replay.run, replay.stats — chain integrity and replay

---

## Category 19: Dream, Watcher & Capability (29 tools)

**Priority**: Medium — extends v3's dream cycle and adds watchers
**v2 Gana**: gana_star (29)

**Already ported to v3**: dream.status, dream.trigger, dream.analyze

### Unported — Dream variants (7 tools):
- `dream`, `dream_now`, `dream_start`, `dream_stop`, `dream_status` — Dream control (v2 aliases)
- `dream.expire`, `dream.list`, `dream.promote`, `dream.read` — Dream management

### Unported — Watcher (7 tools):
- `watcher_add`, `watcher_list`, `watcher_remove`, `watcher_start`, `watcher_stop` — Watcher lifecycle
- `watcher_status`, `watcher_stats`, `watcher_recent_events` — Watcher monitoring

### Unported — Capability (3 tools):
- `capabilities`, `capability.matrix`, `get_agent_capabilities` — Capability matrix

### Unported — Telemetry (2 tools):
- `get_telemetry_summary` — Telemetry summary

### Unported — Contest (4 tools):
- `contest.add_finding`, `contest.format`, `contest.prepare`, `contest.status` — Security contest

### Unported — Meta Galaxy (1 tool):
- `meta.galaxy.overview` — Meta galaxy overview

### Unported — Fool Guard (3 tools):
- `fool_guard.dare_to_die`, `fool_guard.ralph`, `fool_guard.status` — Fool guard

**Assessment**: The dream management tools (expire, list, promote, read) extend v3's dream cycle with dream content tracking. The watcher tools (7) are valuable — they provide event monitoring, which v3 lacks. The capability matrix tools overlap with v3's agent.capabilities. The contest tools are security-specific.

**Recommended for porting** (8 tools): dream.list, dream.read, dream.promote, watcher_add, watcher_list, watcher_start, watcher_status, watcher_recent_events — dream content and event watchers

---

## Category 20: Galaxy Management Extras (31 tools)

**Priority**: Low — v3 already has comprehensive galaxy tools
**v2 Gana**: gana_void (43, minus 12 ported)

**Already ported to v3**: galaxy.stats, galaxy.transfer, galaxy.merge, galaxy.snapshot, galaxy.restore, galaxy.backup, galaxy.dashboard, galaxy.taxonomy, galaxy.purge, galaxy.health, galaxy.export, galaxy.import

### Unported — Galaxy CRUD (8 tools):
- `galaxy.create`, `galaxy.delete`, `galaxy.list`, `galaxy.use`, `galaxy.switch` — Galaxy lifecycle
- `galaxy.status`, `galaxy.route`, `galaxy.search_multi` — Galaxy operations

### Unported — Galaxy Classification (5 tools):
- `galaxy.classify`, `galaxy.canonical_taxonomy`, `galaxy.list_types` — Galaxy classification
- `galaxy.export_tutorial`, `galaxy.ingest` — Galaxy content

### Unported — Galaxy Lineage (3 tools):
- `galaxy.lineage`, `galaxy.lineage_stats`, `galaxy.migrate` — Galaxy lineage

### Unported — Galactic (3 tools):
- `galactic.dashboard`, `galactic.stats`, `galactic.sweep`, `galactic_dashboard` — Galactic operations (v2 aliases)

### Unported — Memory (1 tool):
- `memory.rent` — Memory rent

### Unported — Gardens (12 tools):
- (See Category 9)

**Assessment**: The galaxy CRUD tools (create, delete, list, use, switch) are basic galaxy management that v3 handles via its Galaxy enum. The lineage tools (3) track galaxy evolution over time. The classification tools overlap with v3's galaxy.taxonomy. Most of these are v2 aliases or thin wrappers.

**Recommended for porting** (3 tools): galaxy.list, galaxy.lineage, galaxy.lineage_stats — galaxy listing and lineage tracking

---

## Category 21: Archaeology & Learning Extras (30 tools)

**Priority**: Low — v3 already has archaeology.search and learning tools
**v2 Gana**: gana_ox (46, minus 6 ported)

**Already ported to v3**: archaeology.search, learning.pattern, learning.suggest, pattern.search, salience.spotlight, serendipity.surface

### Unported — Archaeology variants (12 tools):
- `archaeology`, `archaeology_daily_digest`, `archaeology_find_changed`, `archaeology_find_unread` — Archaeology monitoring
- `archaeology_have_read`, `archaeology_mark_read`, `archaeology_mark_written` — Read tracking
- `archaeology_process_wisdom`, `archaeology_recent_reads`, `archaeology_report` — Archaeology reports
- `archaeology_scan_directory`, `archaeology_stats`, `archaeology_search` — Archaeology scanning

### Unported — Learning variants (5 tools):
- `continual_learner.recommend`, `continual_learner.summary` — Continual learning
- `learning.patterns`, `learning.stats`, `learning.status` — Learning stats

### Unported — Pattern tools (7 tools):
- `pattern.avoid`, `pattern.ingest`, `pattern.learn`, `pattern.list`, `pattern.lookup`, `pattern.resolve`, `pattern.summary` — Error pattern library

### Unported — Kaizen (2 tools):
- `kaizen_analyze`, `kaizen_apply_fixes` — Continuous improvement

### Unported — Knowledge Gap (1 tool):
- `knowledge_gap.run` — Knowledge gap detection

### Unported — Windsurf (10 tools):
- `windsurf.categorize`, `windsurf.compare`, `windsurf.export_all`, `windsurf.full_steps` — Windsurf conversation tools
- `windsurf.ingest`, `windsurf.mine`, `windsurf.semantic_search`, `windsurf.sync` — Windsurf mining
- `windsurf_export_conversation`, `windsurf_list_conversations`, `windsurf_read_conversation`, `windsurf_search_conversations`, `windsurf_stats` — Windsurf conversation management

### Unported — Other (2 tools):
- `rabbit_hole_research` — Deep research
- `learned_router.status` — Learned router

**Assessment**: The archaeology variants are v2's file monitoring system — tracking what's been read/written. The pattern library (7 tools) is an error pattern knowledge base. The kaizen tools are continuous improvement. The Windsurf tools are IDE-specific conversation mining. The knowledge_gap tool has cognitive value.

**Recommended for porting** (5 tools): pattern.lookup, pattern.learn, pattern.list, kaizen_analyze, knowledge_gap.run — error pattern library and knowledge gap detection

---

## Category 22: Mandala, Shelter & Model Management (35 tools)

**Priority**: Low — v3 has mandala compartments, shelter is sandbox concern
**v2 Gana**: gana_roof (35)

### Unported — Mandala (4 tools):
- `mandala.create`, `mandala.destroy`, `mandala.status`, `mandala.templates` — Mandala compartment management

### Unported — Shelter/Sandbox (5 tools):
- `shelter.create`, `shelter.destroy`, `shelter.execute`, `shelter.inspect`, `shelter.status` — Shelter sandbox
- `shelter.policy` — Shelter policy

### Unported — LLM Tools (5 tools):
- `llama.agent`, `llama.chat`, `llama.generate`, `llama.models`, `llama.warmup` — Llama.cpp integration
- `ollama.agent` — Ollama integration

### Unported — Model Management (5 tools):
- `model.hash`, `model.list`, `model.optimize`, `model.optimize_status`, `model.register` — Model management
- `model.signing_status`, `model.verify` — Model signing

### Unported — Edge/BitNet (4 tools):
- `bitnet_infer`, `bitnet_status` — BitNet inference
- `edge_add_rule`, `edge_batch_infer`, `edge_infer`, `edge_stats` — Edge inference

### Unported — Embedding Daemon (4 tools):
- `embedding.daemon_process`, `embedding.daemon_start`, `embedding.daemon_status`, `embedding.daemon_stop` — Embedding daemon

### Unported — Browser Embedder (2 tools):
- `browser_embedder.config`, `browser_embedder.status` — Browser embedder

**Assessment**: v3 already has mandala compartments in wm-governance. The mandala.create/destroy/status tools could be useful for runtime compartment management. The shelter tools are v2's sandbox — v3's governance system handles this differently. The LLM tools (llama, ollama) are external service integrations. The model management tools are infrastructure.

**Recommended for porting** (3 tools): mandala.create, mandala.destroy, mandala.status — runtime mandala compartment management

---

## Summary: Recommended Porting Priorities

### Tier 8 (High Priority — 40 tools)

| Category | Tools | Count |
|----------|-------|-------|
| Consciousness Extras | citta.continuity, citta.trajectory, citta.vector, consciousness.flow, consciousness.mode, sensorium.state, guna.balance.status, vitality | 8 |
| Agent & Swarm | swarm.decompose/route/complete/plan/resolve/vote/analyze/status, sabha.convene, sabha.status, corpus_callosum.debate, corpus_callosum.status | 12 |
| Simulation & Forecasting | simulation.create/run/status/forecast, mc.optimize, mc.rare_event, foresight.analyze, ensemble.query, possibility.explore, maturity.assess | 10 |
| Dream & Watcher | dream.list, dream.read, dream.promote, watcher_add/list/start/status/recent_events | 8 |
| Session/Scratchpad | scratchpad_create/update/finalize, working_memory.attend/context/status | 6 (reduced from 8) |

### Tier 9 (Medium Priority — 32 tools)

| Category | Tools | Count |
|----------|-------|-------|
| Pipeline & Skill | skill.amend/evaluate/history/import, prompt.list/render, task.complete/list/route_smart, selfmodel.forecast | 10 |
| Memory Lifecycle | memory.lifecycle/lifecycle_stats/retention_sweep, reconsolidation.mark/status, archive.run | 6 |
| Governance | governor_set_goal/check_drift/check_budget/stats, dharma.escalate/review_queue, sandbox.status/violations, rate_limiter.stats, verify_consent | 10 |
| Pattern Library | pattern.lookup/learn/list, kaizen_analyze, knowledge_gap.run | 5 |
| Galaxy Extras | galaxy.list, galaxy.lineage, galaxy.lineage_stats | 3 (reduced from 3) |

### Tier 10 (Low Priority — 6 tools)

| Category | Tools | Count |
|----------|-------|-------|
| Cache | cache.flush, cache.status, cache.tune | 3 |
| Karma | karma.verify_chain, replay.run, replay.stats | 3 |

### Skip (647 tools)

Security scanning (29), Web/Browser (27), Code Analysis (23), Distributed/Mesh (31), Quantum (23), Marketplace/Bounty (50), Gardens (12), War Room (20), Grimoire/Oracle (15), Mandala/Shelter (32), and various v2 aliases/wrappers.

---

## Next Steps

1. **Tier 8 porting** (40 tools) — consciousness, swarm, simulation, dream, scratchpad
2. **Tier 9 porting** (32 tools) — skill lifecycle, memory lifecycle, governance, patterns
3. **Tier 10 porting** (6 tools) — cache, karma chain, replay
4. **cargo bench** — benchmark regressions against Aug 2 baseline
5. **Migration tool** — SQLite → LMDB data transfer
