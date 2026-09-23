# Q08 — Dispatch-boundary matrix

**Baseline:** WhiteMagic 9.2.0 (`aa3c266`), 2026-09-19.
**Scope** (`V9_MASTER_CLOSURE_PLAN.md` M2): direct / wrapper / NLU / daemon /
federated / mesh, per-route with fixtures. **Acceptance:** this artifact
exists, every cell below is covered by a named test or a filed gap, and the
new fixtures pass in CI on Linux.

The route inventory in §2 is **generated from the live registry** by
`wm_mcp::boundary_matrix::render_block` and drift-checked by
`crates/wm-mcp/tests/dispatch_boundary_matrix.rs`. Regenerate with:

```bash
WM_UPDATE_Q08_MATRIX=1 cargo test -p whitemagic --test dispatch_boundary_matrix \
  matrix_block_matches_committed_artifact
```

## 1. Boundaries, classes, symbols

| # | Boundary | Entry / enforcement seam |
|---|---|---|
| B1 | Direct dispatch | `wm-dispatch/src/pipeline.rs` — brain-wave/effect gate, confirm gate (4b), firebreak scope law (4c), dharma (2), resource rules (2b), rate/circuit (3–4) |
| B2 | Wrapper / aliases | MCP discrete lifecycle aliases + underscore/dot fallback (`wm-mcp/src/server.rs` `handle_tools_call`, `wm-tools/src/expansion/common.rs::canonical_tool_alias`) through the same pipeline; profile filtering happens before the meta-tools (`wm-tools/src/profiles.rs`) |
| B3 | NLU (`thought=`) | `wm-tools/src/lib.rs` `WmMetaTool::call` — classifier (`nlu.rs`, `embedding_router.rs`), abstention, destructive structural gate |
| B4 | Daemon cycles | `wm-mcp/src/daemon.rs` + `wm-cognitive/src/autonomous.rs` — cycles mutate stores directly; health/time/novelty/human-review gates, **no pipeline dispatch** |
| B5 | Federated gateway | `wm-mcp/src/gateway.rs` — 5 federated read routes fan out; everything else pinned to an explicit scope; unknown scope fails closed |
| B6 | Mesh | `wm-sangha/src/transport.rs::require_can_execute` — bound-key identity + authority grants on chat/signal/lock/heartbeat frames |

**Route classes** (exclusive; first match wins: meta by name → destructive →
spawn → coordination → write → read) and **symbols**: `A` admitted
(standard pipeline gates apply) · `C` admitted only with `confirm: true` plus
an explicit `SCOPE_REGISTRY` scope · `R` refused (NLU structural
unreachability) · `P` pinned to an explicit gateway scope (write-without-scope
refused) · `F` federated read fan-out · `N` no registry dispatch path at this
boundary · `—` boundary does not carry registry routes.

## 2. Route inventory (generated)

<!-- BEGIN GENERATED: q08-route-matrix -->
Routes: 311 — read 204, write 85, destructive 12, spawn 3, coordination 2, meta 5 (exclusive class; first match wins in that order, meta by route name).

| Route | Gana | Class | Effects | B1 direct | B2 wrapper | B3 NLU | B4 daemon | B5 gateway | B6 mesh |
|---|---|---|---|---|---|---|---|---|---|
| actuator.command | Dipper | write | w | A | A | A | N | P | — |
| actuator.estop | Dipper | write | w | A | A | A | N | P | — |
| actuator.list | Dipper | read | r | A | A | A | N | P | — |
| agent.capabilities | Room | write | rw | A | A | A | N | P | — |
| agent.deregister | Room | write | rw | A | A | A | N | P | — |
| agent.descriptions | Room | write | rw | A | A | A | N | P | — |
| agent.heartbeat | Room | write | w | A | A | A | N | P | — |
| agent.heartbeat.history | Room | read | r | A | A | A | N | P | — |
| agent.list | Room | read | r | A | A | A | N | P | — |
| agent.register | Room | write | w | A | A | A | N | P | — |
| agent.trust | Room | write | rw | A | A | A | N | P | — |
| anomaly.detect | Heart | read | r | A | A | A | N | P | — |
| anti_loop.check | Wall | read | r | A | A | A | N | P | — |
| apotheosis.check | Ghost | read | r | A | A | A | N | P | — |
| archaeology.search | Ox | read | r | A | A | A | N | P | — |
| army.deploy | TurtleBeak | write | rw | A | A | A | N | P | — |
| association.mine | Net | write | w | A | A | A | N | P | — |
| bagua.dispatch | Ghost | write | rw | A | A | A | N | P | — |
| bicameral.reason | ThreeStars | read | r | A | A | A | N | P | — |
| bicameral.status | ThreeStars | read | - | A | A | A | N | P | — |
| boundary.enforce | Wall | read | r | A | A | A | N | P | — |
| bounty.evidence.package | Room | write | w | A | A | A | N | P | — |
| bounty.evidence.taxonomy | Room | read | - | A | A | A | N | P | — |
| bounty.import | Room | write | w | A | A | A | N | P | — |
| bounty.ledger.list | Room | read | - | A | A | A | N | P | — |
| bounty.ledger.record | Room | write | w | A | A | A | N | P | — |
| bounty.ledger.stats | Room | read | - | A | A | A | N | P | — |
| bounty.ledger.update | Room | write | w | A | A | A | N | P | — |
| bounty.scan | Room | read | - | A | A | A | N | P | — |
| breaker.reset | Horn | read | - | A | A | A | N | P | — |
| breaker.status | Horn | read | - | A | A | A | N | P | — |
| bus.emit | Heart | write | w | A | A | A | N | P | — |
| bus.recent | Heart | read | r | A | A | A | N | P | — |
| bus.stats | Heart | read | r | A | A | A | N | P | — |
| captain.deploy | Ghost | write | rw | A | A | A | N | P | — |
| citta.coherence | Ghost | read | - | A | A | A | N | P | — |
| citta.history | Ghost | read | r | A | A | A | N | P | — |
| citta.reflect | Ghost | read | r | A | A | A | N | P | — |
| citta.status | Ghost | read | - | A | A | A | N | P | — |
| claims | Mound | read | r | A | A | A | N | P | — |
| claims.add | Mound | write | rw | A | A | A | N | P | — |
| claims.calibration | Mound | read | r | A | A | A | N | P | — |
| claims.list | Mound | read | r | A | A | A | N | P | — |
| claims.resolve | Mound | write | rw | A | A | A | N | P | — |
| claims.status | Mound | read | r | A | A | A | N | P | — |
| code.affected_by | Chariot | read | r | A | A | A | N | P | — |
| code.check | Room | read | r | A | A | A | N | P | — |
| code.claim | Room | coordination | rw | A | A | A | N | P | — |
| code.graph | Chariot | read | r | A | A | A | N | P | — |
| code.list | Room | read | r | A | A | A | N | P | — |
| code.query | Chariot | read | r | A | A | A | N | P | — |
| code.release | Room | coordination | rw | A | A | A | N | P | — |
| conformal.export | Ghost | read | - | A | A | A | N | P | — |
| conformal.fit_classifier | Ghost | read | - | A | A | A | N | P | — |
| conformal.fit_regressor | Ghost | read | - | A | A | A | N | P | — |
| conformal.import | Ghost | read | - | A | A | A | N | P | — |
| conformal.monitor | Ghost | read | - | A | A | A | N | P | — |
| conformal.predict_interval | Ghost | read | - | A | A | A | N | P | — |
| conformal.predict_set | Ghost | read | - | A | A | A | N | P | — |
| conformal.status | Ghost | read | - | A | A | A | N | P | — |
| consciousness.depth | Ghost | read | r | A | A | A | N | P | — |
| consolidation.compress | Encampment | write | rw | A | A | A | N | P | — |
| consolidation.connect | Encampment | write | rw | A | A | A | N | P | — |
| constellation.detect | Star | read | r | A | A | A | N | P | — |
| constellation.list | Star | read | r | A | A | A | N | P | — |
| correlation.analyze | HairyHead | read | r | A | A | A | N | P | — |
| council.deliberate | ExtendedNet | read | r | A | A | A | N | P | — |
| dharma.acs | ExtendedNet | read | - | A | A | A | N | P | — |
| dharma.audit | ExtendedNet | read | r | A | A | A | N | P | — |
| dharma.escalate | ExtendedNet | read | - | A | A | A | N | P | — |
| dharma.profiles | ExtendedNet | read | - | A | A | A | N | P | — |
| dharma.resolve_review | ExtendedNet | write | w | A | A | A | N | P | — |
| dharma.review_queue | ExtendedNet | read | r | A | A | A | N | P | — |
| dharma.rules | ExtendedNet | read | - | A | A | A | N | P | — |
| dharma.status | ExtendedNet | read | - | A | A | A | N | P | — |
| dream.analyze | Ghost | read | r | A | A | A | N | P | — |
| dream.status | Abundance | read | r | A | A | A | N | P | — |
| dream.trigger | Abundance | write | w | A | A | A | N | P | — |
| drive.event | Ghost | read | - | A | A | A | N | P | — |
| drive.snapshot | Ghost | read | - | A | A | A | N | P | — |
| emergence.report | Net | read | - | A | A | A | N | P | — |
| emergence.scan | Encampment | write | rw | A | A | A | N | P | — |
| explain | ThreeStars | read | r | A | A | A | N | P | — |
| fragment.search | WinnowingBasket | read | r | A | A | A | N | P | — |
| friction.auto_log | Wall | write | wi | A | A | A | N | P | — |
| friction.log | Wall | write | wi | A | A | A | N | P | — |
| friction.resolve | Wall | read | - | A | A | A | N | P | — |
| friction.review | Wall | read | r | A | A | A | N | P | — |
| galaxy.backup | Void | write | w | A | A | A | N | P | — |
| galaxy.cold_rotate | Room | destructive | rwd | C | C | R | N | PC | — |
| galaxy.dashboard | Void | read | - | A | A | A | N | P | — |
| galaxy.export | Void | read | r | A | A | A | N | P | — |
| galaxy.health | Void | read | - | A | A | A | N | P | — |
| galaxy.import | Void | write | w | A | A | A | N | P | — |
| galaxy.merge | Neck | write | rw | A | A | A | N | P | — |
| galaxy.purge | Void | destructive | rwd | C | C | R | N | PC | — |
| galaxy.restore | Void | destructive | rwd | C | C | R | N | PC | — |
| galaxy.snapshot | Void | write | rw | A | A | A | N | P | — |
| galaxy.stats | Void | read | - | A | A | A | N | P | — |
| galaxy.taxonomy | Void | read | - | A | A | A | N | P | — |
| galaxy.transfer | Neck | destructive | rwd | C | C | R | N | PC | — |
| galaxy.triage_sweep | Room | write | rw | A | A | A | N | P | — |
| geneseed.mine | Ghost | write | rw | A | A | A | N | P | — |
| geneseed.stats | Ghost | read | r | A | A | A | N | P | — |
| gnosis | Root | meta | r | A | A | — | N | P | — |
| gnosis.explain | ThreeStars | read | - | A | A | A | N | P | — |
| gnosis.history | ThreeStars | read | - | A | A | A | N | P | — |
| gnosis.status | ThreeStars | read | - | A | A | A | N | P | — |
| god.nodes | HairyHead | read | r | A | A | A | N | P | — |
| graph.community | HairyHead | read | r | A | A | A | N | P | — |
| graph.propagate | WinnowingBasket | read | r | A | A | A | N | P | — |
| graph.walk | WinnowingBasket | read | r | A | A | A | N | P | — |
| harmony.history | Dipper | read | - | A | A | A | N | P | — |
| harmony.vector | Dipper | read | - | A | A | A | N | P | — |
| hermit.mediate | Room | write | w | A | A | A | N | P | — |
| hermit.resolve | Room | write | w | A | A | A | N | P | — |
| hermit.status | Room | read | r | A | A | A | N | P | — |
| hermit.withdraw | Room | write | w | A | A | A | N | P | — |
| hologram.query | Ghost | read | r | A | A | A | N | P | — |
| hologram.rebalance | Ghost | write | rw | A | A | A | N | P | — |
| homeostasis.adjust | Dipper | read | r | A | A | A | N | P | — |
| homeostasis.alerts | Dipper | read | r | A | A | A | N | P | — |
| homeostasis.check | Dipper | read | r | A | A | A | N | P | — |
| homeostasis.history | Dipper | read | r | A | A | A | N | P | — |
| imagine.predict | ThreeStars | read | r | A | A | A | N | P | — |
| imagine.reflect | ThreeStars | read | r | A | A | A | N | P | — |
| imagine.scenario | ThreeStars | read | r | A | A | A | N | P | — |
| improve.active_proposals | Wall | read | - | A | A | A | N | P | — |
| improve.proposals | Wall | write | rw | A | A | A | N | P | — |
| kaizen.correlate | ThreeStars | read | r | A | A | A | N | P | — |
| karma.anchor | Willow | write | w | A | A | A | N | P | — |
| karma.clear | Willow | destructive | wd | C | C | R | N | PC | — |
| karma.history | Willow | read | r | A | A | A | N | P | — |
| karma.report | Willow | read | r | A | A | A | N | P | — |
| karma.verify_chain | Willow | read | r | A | A | A | N | P | — |
| kg.extract | Net | write | rw | A | A | A | N | P | — |
| kg.query | Net | read | r | A | A | A | N | P | — |
| kg.top | HairyHead | read | r | A | A | A | N | P | — |
| learning.pattern | Ox | read | r | A | A | A | N | P | — |
| learning.suggest | Ox | read | r | A | A | A | N | P | — |
| mc.optimize | Mound | read | r | A | A | A | N | P | — |
| mc.rare_event | Mound | read | r | A | A | A | N | P | — |
| mc.sde | Mound | read | r | A | A | A | N | P | — |
| mc.superforecaster | Mound | read | r | A | A | A | N | P | — |
| mc.surrogate | Mound | read | r | A | A | A | N | P | — |
| memory.aggregate | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.associate | Net | write | wi | A | A | A | N | P | — |
| memory.associate_mine | Net | write | w | A | A | A | N | P | — |
| memory.associations | Net | read | r | A | A | A | N | P | — |
| memory.batch_create | Encampment | write | wix | A | A | A | N | P | — |
| memory.batch_delete | Encampment | destructive | rwid | C | C | R | N | PC | — |
| memory.batch_read | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.chat | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.consolidate | Encampment | destructive | rwd | C | C | R | N | PC | — |
| memory.corroborate | Net | write | rw | A | A | A | N | P | — |
| memory.count | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.create | Encampment | write | wix | A | A | A | N | P | — |
| memory.decay | WinnowingBasket | write | rw | A | A | A | N | P | — |
| memory.deduplicate | WinnowingBasket | destructive | rwd | C | C | R | N | PC | — |
| memory.delete | Encampment | destructive | rwidx | C | C | R | N | PC | — |
| memory.episodic_search | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.export | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.filter | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.hybrid_recall | WinnowingBasket | read | r | A | A | A | N | F | — |
| memory.ingest | Encampment | write | rwi | A | A | A | N | P | — |
| memory.list | WinnowingBasket | read | r | A | A | A | N | F | — |
| memory.nearby | Star | read | r | A | A | A | N | P | — |
| memory.query | WinnowingBasket | read | r | A | A | A | N | F | — |
| memory.read | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.recall_feedback | WinnowingBasket | write | w | A | A | A | N | P | — |
| memory.reembed | WinnowingBasket | write | rw | A | A | A | N | P | — |
| memory.relate | Net | write | w | A | A | A | N | P | — |
| memory.revisions | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.search | WinnowingBasket | read | r | A | A | A | N | F | — |
| memory.sort | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.stats | WinnowingBasket | read | r | A | A | A | N | P | — |
| memory.tag | Net | write | rw | A | A | A | N | P | — |
| memory.tags | Net | read | r | A | A | A | N | P | — |
| memory.update | Encampment | write | rwx | A | A | A | N | P | — |
| memory.vector.search | WinnowingBasket | read | r | A | A | A | N | P | — |
| meta.enhance | ThreeStars | read | r | A | A | A | N | P | — |
| meta.stats | ThreeStars | read | - | A | A | A | N | P | — |
| model.sign | ExtendedNet | read | - | A | A | A | N | P | — |
| model.verify | ExtendedNet | read | - | A | A | A | N | P | — |
| network.centrality | Net | read | - | A | A | A | N | P | — |
| network.clusters | Net | read | - | A | A | A | N | P | — |
| network.stats | Net | read | - | A | A | A | N | P | — |
| nlu.shadow_report | Horn | meta | - | A | A | — | N | P | — |
| oss.bounty.scan | ExtendedNet | spawn | rsx | A | A | A | N | P | — |
| oss.bounty.status | ExtendedNet | spawn | rsx | A | A | A | N | P | — |
| pattern.detect | Net | read | - | A | A | A | N | P | — |
| pattern.search | Ox | read | r | A | A | A | N | P | — |
| pipeline.create | Horn | write | w | A | A | A | N | P | — |
| pipeline.list | Horn | read | r | A | A | A | N | P | — |
| pipeline.status | Horn | read | r | A | A | A | N | P | — |
| reasoning.bicameral | ThreeStars | read | r | A | A | A | N | P | — |
| receipts.anchor | Willow | write | rwx | A | A | A | N | P | — |
| receipts.disclose | Willow | write | rwx | A | A | A | N | P | — |
| receipts.emit | Willow | write | rwx | A | A | A | N | P | — |
| receipts.list | Willow | read | r | A | A | A | N | P | — |
| receipts.read | Willow | read | r | A | A | A | N | P | — |
| receipts.verify | Willow | read | r | A | A | A | N | P | — |
| redteam.coverage_report | Wall | write | rw | A | A | A | N | P | — |
| redteam.from_friction | Wall | read | - | A | A | A | N | P | — |
| redteam.proposals | Wall | write | rw | A | A | A | N | P | — |
| reflex.add | Dipper | write | w | A | A | A | N | P | — |
| reflex.dispatch | Heart | read | - | A | A | A | N | P | — |
| reflex.evaluate | Dipper | write | w | A | A | A | N | P | — |
| reflex.list | Dipper | read | r | A | A | A | N | P | — |
| reflex.status | Heart | read | - | A | A | A | N | P | — |
| research.rabbit_hole | Mound | read | r | A | A | A | N | P | — |
| research.repo | Mound | read | r | A | A | A | N | P | — |
| research.topic | Mound | read | r | A | A | A | N | P | — |
| retention.prune | Encampment | write | rw | A | A | A | N | P | — |
| salience.spotlight | Ox | read | r | A | A | A | N | P | — |
| sandbox.limits | Room | read | r | A | A | A | N | P | — |
| sandbox.set_limits | Room | write | w | A | A | A | N | P | — |
| sangha.chat | Room | read | r | A | A | A | N | P | — |
| sangha.discover | Room | read | r | A | A | A | N | P | — |
| sangha.locks | Room | write | rw | A | A | A | N | P | — |
| sangha.mesh.chat | Room | write | w | A | A | A | N | P | — |
| sangha.mesh.join | Room | write | w | A | A | A | N | P | — |
| sangha.mesh.mail | Room | read | r | A | A | A | N | P | — |
| sangha.mesh.quarantine | Room | write | w | A | A | A | N | P | — |
| sangha.mesh.read | Room | read | r | A | A | A | N | P | — |
| sangha.mesh.status | Room | read | r | A | A | A | N | P | — |
| sangha.peers | Room | read | r | A | A | A | N | P | — |
| sangha.quarantine | Room | write | w | A | A | A | N | P | — |
| sangha.signal | Room | read | r | A | A | A | N | P | — |
| security.breaker.alerts | Wall | read | - | A | A | A | N | P | — |
| security.breaker.record | Wall | write | w | A | A | A | N | P | — |
| security.breaker.reset | Wall | write | w | A | A | A | N | P | — |
| security.breaker.status | Wall | read | - | A | A | A | N | P | — |
| security.probe.evaluate | Wall | read | - | A | A | A | N | P | — |
| security.probe.library | Wall | read | - | A | A | A | N | P | — |
| security.probe.plan | Wall | read | - | A | A | A | N | P | — |
| selfmodel.alerts | Ghost | read | - | A | A | A | N | P | — |
| selfmodel.forecast | Ghost | read | - | A | A | A | N | P | — |
| selfmodel.gnosis | Ghost | read | - | A | A | A | N | P | — |
| selfmodel.snapshot | Ghost | read | - | A | A | A | N | P | — |
| selfplay.export | Ox | read | - | A | A | A | N | P | — |
| selfplay.run | Ox | read | r | A | A | A | N | P | — |
| selfplay.status | Ox | read | - | A | A | A | N | P | — |
| sensor.history | Dipper | read | r | A | A | A | N | P | — |
| sensor.list | Dipper | read | r | A | A | A | N | P | — |
| sensor.poll | Dipper | read | r | A | A | A | N | P | — |
| sensor.read | Dipper | read | r | A | A | A | N | P | — |
| sensorimotor.scan | Encampment | write | rw | A | A | A | N | P | — |
| serendipity.surface | Star | read | r | A | A | A | N | P | — |
| session.checkpoint | StraddlingLegs | spawn | rws | A | A | A | N | P | — |
| session.checkpoint_nodiscovery | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.continuity | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.digest | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.end | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.export | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.handoff | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.import | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.list | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.recall | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.record | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.replay | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.start | StraddlingLegs | write | w | A | A | A | N | P | — |
| session.track_log | StraddlingLegs | read | r | A | A | A | N | P | — |
| session.verify | StraddlingLegs | read | r | A | A | A | N | P | — |
| sim.counterfactual | Mound | read | r | A | A | A | N | P | — |
| sim.forecast | Mound | read | r | A | A | A | N | P | — |
| sim.mc | Mound | read | r | A | A | A | N | P | — |
| simulation.calibrate | Mound | read | r | A | A | A | N | P | — |
| skill.invoke | Horn | read | r | A | A | A | N | P | — |
| skill.list | Horn | read | r | A | A | A | N | P | — |
| smarana.status | Ghost | read | r | A | A | A | N | P | — |
| smarana.trace | Ghost | read | r | A | A | A | N | P | — |
| speculative.decode | ThreeStars | read | r | A | A | A | N | P | — |
| speculative.stats | ThreeStars | read | - | A | A | A | N | P | — |
| spiral.report | Encampment | read | - | A | A | A | N | P | — |
| state.revert | Heart | read | r | A | A | A | N | P | — |
| state.snapshot | Heart | write | rw | A | A | A | N | P | — |
| system.config | Horn | read | - | A | A | A | N | P | — |
| system.flush | Root | destructive | rwd | C | C | R | N | PC | — |
| system.health | Horn | read | - | A | A | A | N | P | — |
| task.distribute | TurtleBeak | write | w | A | A | A | N | P | — |
| task.status | TurtleBeak | read | r | A | A | A | N | P | — |
| telemetry.prune | Ghost | destructive | rwd | C | C | R | N | PC | — |
| telemetry.record | Ghost | write | rw | A | A | A | N | P | — |
| telemetry.retention | Ghost | read | r | A | A | A | N | P | — |
| telemetry.rollup | Ghost | write | rw | A | A | A | N | P | — |
| think | ThreeStars | read | r | A | A | A | N | P | — |
| timescale.hooks | Dipper | read | - | A | A | A | N | P | — |
| timescale.status | Dipper | read | - | A | A | A | N | P | — |
| tools.effectiveness_report | Ghost | read | - | A | A | A | N | P | — |
| tools.list | Ghost | meta | - | A | A | — | N | P | — |
| tools.retire | Ghost | read | - | A | A | A | N | P | — |
| tools.usage_report | Ghost | meta | - | A | A | — | N | P | — |
| transaction.begin | Void | write | w | A | A | A | N | P | — |
| transaction.commit | Void | write | rw | A | A | A | N | P | — |
| transaction.rollback | Void | destructive | rwd | C | C | R | N | PC | — |
| tx_firewall.set_policy | Room | write | w | A | A | A | N | P | — |
| tx_firewall.status | Room | read | r | A | A | A | N | P | — |
| violet.engagement.issue | Room | write | w | A | A | A | N | P | — |
| violet.engagement.revoke | Room | write | w | A | A | A | N | P | — |
| violet.engagement.validate | Room | read | - | A | A | A | N | P | — |
| web.deep_fetch | Chariot | read | r | A | A | A | N | P | — |
| web.fetch | Chariot | read | r | A | A | A | N | P | — |
| web.search | Chariot | read | r | A | A | A | N | P | — |
| web.search_and_read | Chariot | read | r | A | A | A | N | P | — |
| whitemagic | Ghost | write | rw | A | A | A | N | P | — |
| wm | Horn | meta | - | A | A | — | N | P | — |
| workspace.events | Ghost | read | - | A | A | A | N | P | — |
| workspace.publish | Ghost | read | - | A | A | A | N | P | — |
| workspace.spotlight | Ghost | read | - | A | A | A | N | P | — |
| workspace.stats | Ghost | read | - | A | A | A | N | P | — |
<!-- END GENERATED: q08-route-matrix -->

## 3. Boundary × class expectations

Cells carry the verdict for the class; per-route symbols are in §2. Every
admitted cell still passes the full B1 gate stack (profile, brain-wave,
dharma, resource rules, rate limit, audit).

| Class | B1 direct | B2 wrapper | B3 NLU | B4 daemon | B5 gateway | B6 mesh |
|---|---|---|---|---|---|---|
| read | A | A | A | N | F (federated set) / P | — |
| write | A | A | A | N | P | — |
| destructive | C | C | R | N | PC | — |
| spawn | A | A | A | N | P | — |
| coordination | A | A | A | N | P | — |
| meta | A | A | — | N | P | — |

## 4. Fixture coverage

| Cell | Evidence |
|---|---|
| B1 × read/write | `wm-dispatch/tests/dispatch.rs` (registry + dispatch suite), `wm-dispatch/src/pipeline.rs` write-audit/gate tests |
| B1 × destructive | `pipeline.rs::pipeline_destructive_{blocked_without_confirm,allowed_with_confirm,blocked_with_false_confirm}`; scope law `pipeline_firebreak_scope_law_{blocks_unscoped,allows_scoped}_destructive`; `tests/redteam.rs::delta_blocks_all_tools_even_with_perfect_context` |
| B1 × coordination | `pipeline.rs::pipeline_strict_refusal_is_typed_and_distinct_from_starvation` (lease acquisition under stress); `wm-tools/src/expansion/coordination.rs` claim/conflict/owner-release suites |
| B1 × spawn | `wm-governance/src/firebreak.rs` dangerous-on-spawn tests; pipeline sandbox routing tests (`pipeline.rs` 4e) |
| B2 × read/write | `wm-mcp/src/server.rs::e2e_full_session_lifecycle`, `tools_list_exposes_meta_tool_and_lifecycle_catalog`; spawned surface `wm-mcp/tests/profile_serve_e2e.rs`; `scripts/curated_smoke_test.py` |
| B2 × destructive | **new** `wm-mcp/tests/dispatch_boundary_matrix.rs::destructive_alias_requires_confirm_and_preserves_the_record` (spawned binary: alias delete refused without confirm, record survives, confirmed delete admitted) |
| B3 × read/write | `wm-tools/src/lib.rs::wm_route_destructive_*` neighbours, `nlu.rs`/`embedding_router.rs` router suites, `tests/abstention_contract.rs`; smoke-test NLU step |
| B3 × destructive | `lib.rs::wm_thought_cannot_reach_destructive_tool{,_even_with_confirm}`, `nlu_cannot_reach_any_destructive_tool` (sweeps every registered destructive route) |
| B4 × all classes | `daemon_cycle_e2e.rs::daemon_cycle_e2e_health_gate_and_no_dispatch` — spawned, bounded daemon; health-gate skip vs run, empty write-audit journal, canary unchanged (closes **Q08-G1**) |
| B5 × read | `gateway.rs::federated_read_merges_labels_and_ranks`, `federated_read_degrades_visibly_when_a_scope_is_down` (mock backing); spawned `federated_gateway_e2e.rs::federated_gateway_e2e_pins_scopes_and_preserves_inner_payload` (closes **Q08-G2**; `scripts/q03_acceptance.py` stays for live-unit acceptance) |
| B5 × write | `gateway.rs::pinned_route_goes_to_exactly_one_scope`, `write_without_scope_or_home_fails_closed`, `unknown_scope_fails_closed_naming_reachable_scopes`, `inner_args_scope_does_not_satisfy_routing` |
| B5 × destructive | gap **Q08-G3** (no live-gateway fixture propagates a destructive route end-to-end; the B1 gate stack is covered, the gateway transport leg is mock-tested only) |
| B6 × peer actions | `wm-sangha/src/transport.rs::{chat,signal,lock}_authority_is_enforced`, replay/identity theft suites; `wm-mcp/tests/mesh_serve_e2e.rs::raw_frame_binding_and_authority_gates` (Unix-only; Windows lane gap already tracked in the work queue) |
| B6 × registry routes | `—` by construction: the mesh carries peer-action frames, not registry dispatch |

## 5. Divergences (documented asymmetries)

- **D1 — `wm session` CLI bypasses the pipeline.** `crates/wm-mcp/src/bin/wm.rs`
  (`run_session_command`) calls session tools directly against the store
  (`BrainWave::Beta`, no dispatch gates). Bounded to the `session.*` surface,
  which contains no destructive routes; the MCP alias path for the same
  routes is pipeline-gated. Guard fixture filed as **Q08-G5**.
- **D2 — Daemon cycles do not dispatch through the registry.** Autonomous
  cycles operate on store APIs directly (`wm-cognitive/src/autonomous.rs`),
  gated by health/time/novelty and `requires_human_review` rather than the
  firebreak. No destructive registry route is reachable from a cycle body
  today; E2E proof is `daemon_cycle_e2e.rs::daemon_cycle_e2e_health_gate_and_no_dispatch`
  (bounded spawned run; **Q08-G1 closed 2026-09-22**).
- **D3 — Two destructive routes were missing from `SCOPE_REGISTRY` (fixed
  2026-09-19).** `galaxy.cold_rotate` declared `destructive: true` but was
  absent from the scope registry, so unscoped dispatches took the
  fail-loud-but-open path while the tool defaulted to all memory galaxies;
  registered as `ArgFields(&["galaxy"])` and pinned by
  `scope_law_blocks_cold_rotate_without_galaxy`. `telemetry.prune` was the
  same class of hole; it is self-bounded by construction (telemetry galaxy
  windows/rollups only, retention horizons, `dry_run` default true) and is
  registered as `SelfBounded` — no admission change, the per-dispatch warn
  disappears and the audit record exists. The registry invariant in
  `dispatch_boundary_matrix.rs` now fails CI if a destructive route is ever
  added without a scope entry; AGENTS.md/SECURITY.md/BULK_OPERATIONS.md
  counts corrected to 12.

## 6. Filed gaps

| ID | Gap | Suggested first slice |
|---|---|---|
| Q08-G1 | **CLOSED 2026-09-22** — `daemon_cycle_e2e.rs::daemon_cycle_e2e_health_gate_and_no_dispatch` (bounded spawned daemon: health-gate skip vs run, empty write-audit, canary unchanged) | closed |
| Q08-G2 | **CLOSED 2026-09-22** — `federated_gateway_e2e.rs::federated_gateway_e2e_pins_scopes_and_preserves_inner_payload` (spawned 2 backings + gateway: federated read labels, pinned write lands on `dev` only, release, unknown-scope refusal) | closed |
| Q08-G3 | Destructive route through a live gateway (pinned + confirm + scope at backing) untested end-to-end | two-store federated fixture with a real destructive alias call |
| Q08-G4 | `registry_classification` invariants exist only in this artifact's test | keep; extend if `EffectRow` grows classes |
| Q08-G5 | No guard proving the `wm session` CLI surface stays bounded to non-destructive routes | enumeration fixture over the session subcommand map |
