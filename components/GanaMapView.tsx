/**
 * Gana Map View — Card-based 28-Gana explorer with quadrant filtering
 *
 * Ported from whitemagic-aux/whitemagic-frontend/_legacy/unified/shared/components/GanaMapView.tsx
 * Adapted to use the site's Tailwind classes and GANA data from GanaWheel.
 * Uses CSS transitions for the detail panel animation.
 */

"use client";

import { useState } from "react";
import { Compass, ChevronRight, Brain, Zap, Shield, Droplets } from "lucide-react";

interface GanaEngine {
  glyph: string;
  name: string;
  nameZh: string;
  desc: string;
  quadrant: "east" | "south" | "west" | "north";
  tools: string[];
}

const GANA_ENGINES: GanaEngine[] = [
  { glyph: "\u89d2", name: "Horn", nameZh: "\u89d2\u5bbf", desc: "Session initialization \u2014 bootstrap, create, resume, checkpoint, handoff", quadrant: "east", tools: ["create_session", "resume_session", "session_bootstrap", "checkpoint_session", "session_handoff"] },
  { glyph: "\u4ea2", name: "Neck", nameZh: "\u4ea2\u5bbf", desc: "Memory creation \u2014 create, update, import, delete, clone memories", quadrant: "east", tools: ["create_memory", "update_memory", "delete_memory", "import_memories", "thought_clone"] },
  { glyph: "\u6c10", name: "Root", nameZh: "\u6c10\u5bbf", desc: "System health \u2014 health report, Rust status/audit, state summary, ship check", quadrant: "east", tools: ["health_report", "rust_status", "rust_audit", "state.summary", "ship.check"] },
  { glyph: "\u623f", name: "Room", nameZh: "\u623f\u5bbf", desc: "Resource locks & privacy \u2014 sangha locks, sandbox, hermit crab mode, MCP integrity", quadrant: "east", tools: ["sangha_lock", "hermit.status", "sandbox.status", "mcp_integrity.verify"] },
  { glyph: "\u5fc3", name: "Heart", nameZh: "\u5fc3\u5bbf", desc: "Session context \u2014 scratchpad create/update/finalize, handoff, context pack", quadrant: "east", tools: ["scratchpad", "scratchpad_create", "context.pack", "session.handoff"] },
  { glyph: "\u5c3e", name: "Tail", nameZh: "\u5c3e\u5bbf", desc: "Performance & acceleration \u2014 SIMD ops, cascade execution, token reporting", quadrant: "east", tools: ["simd.cosine", "simd.batch", "execute_cascade", "token_report"] },
  { glyph: "\u7b95", name: "Basket", nameZh: "\u7b95\u5bbf", desc: "Wisdom & search \u2014 vector search, hybrid recall, graph walk, JIT research, batch read", quadrant: "east", tools: ["search_memories", "hybrid_recall", "graph_walk", "vector.search", "jit_research"] },
  { glyph: "\u9b3c", name: "Ghost", nameZh: "\u9b3c\u5bbf", desc: "Introspection & web \u2014 gnosis, telemetry, capabilities, web search/fetch, browser automation", quadrant: "south", tools: ["gnosis", "capabilities", "web_search", "web_fetch", "browser_navigate"] },
  { glyph: "\u67f3", name: "Willow", nameZh: "\u67f3\u5bbf", desc: "Resilience \u2014 rate limiter, grimoire spells/suggest/cast, oracle divination", quadrant: "south", tools: ["grimoire_list", "grimoire_cast", "cast_oracle", "rate_limiter.stats"] },
  { glyph: "\u661f", name: "Star", nameZh: "\u661f\u5bbf", desc: "Governance \u2014 governor validate/set-goal/drift/budget, dharma rules, forge", quadrant: "south", tools: ["governor_validate", "governor_set_goal", "dharma_rules", "forge.status"] },
  { glyph: "\u5f20", name: "Net", nameZh: "\u5f20\u5bbf", desc: "Capture & filtering \u2014 prompt render/list/reload, karma verify chain", quadrant: "south", tools: ["prompt.render", "prompt.list", "prompt.reload", "karma.verify_chain"] },
  { glyph: "\u7ffc", name: "Wings", nameZh: "\u7ffc\u5bbf", desc: "Deployment & export \u2014 export memories, audit export, mesh broadcast/status", quadrant: "south", tools: ["export_memories", "audit.export", "mesh.broadcast", "mesh.status"] },
  { glyph: "\u8f78", name: "Chariot", nameZh: "\u8f78\u5bbf", desc: "Archaeology & KG \u2014 search/stats/digest, KG extract/query/top, marketplace", quadrant: "south", tools: ["archaeology_search", "archaeology_stats", "kg.extract", "kg.query", "marketplace.discover"] },
  { glyph: "\u8c50", name: "Abundance", nameZh: "\u8c50\u5bbf", desc: "Regeneration \u2014 dream cycle, serendipity, entity resolve, narrative compress, ILP payments", quadrant: "south", tools: ["dream_start", "dream_now", "serendipity_surface", "entity_resolve", "ilp.send"] },
  { glyph: "\u594e", name: "Legs", nameZh: "\u594e\u5bbf", desc: "Ethics & balance \u2014 ethics eval, boundaries, consent, harmony vector, wu xing balance", quadrant: "west", tools: ["evaluate_ethics", "check_boundaries", "verify_consent", "harmony_vector", "wu_xing_balance"] },
  { glyph: "\u5a04", name: "Mound", nameZh: "\u5a04\u5bbf", desc: "Metrics & caching \u2014 hologram view, metric tracking, yin-yang balance, green score", quadrant: "west", tools: ["view_hologram", "track_metric", "get_yin_yang_balance", "green.report"] },
  { glyph: "\u80c3", name: "Stomach", nameZh: "\u80c3\u5bbf", desc: "Digestion & tasks \u2014 pipeline create/list/status, task distribute/route/complete", quadrant: "west", tools: ["pipeline.create", "task.distribute", "task.route_smart", "task.complete"] },
  { glyph: "\u6634", name: "Hairy Head", nameZh: "\u6634\u5bbf", desc: "Detail & debug \u2014 salience, anomaly detection, otel metrics/spans, karma report/trace", quadrant: "west", tools: ["salience.spotlight", "anomaly.check", "otel.metrics", "karma_report", "karmic_trace"] },
  { glyph: "\u6bd5", name: "Extended Net", nameZh: "\u6bd5\u5bbf", desc: "Pattern connectivity \u2014 pattern search, cluster stats, learning, coherence boost, resonance", quadrant: "west", tools: ["pattern_search", "cluster_stats", "learning.patterns", "coherence_boost", "resonance_trace"] },
  { glyph: "\u89dc", name: "Turtle Beak", nameZh: "\u89dc\u5bbf", desc: "Precision \u2014 edge/bitnet inference, edge batch, low-latency compute stats", quadrant: "west", tools: ["edge_infer", "bitnet_infer", "edge_batch_infer", "edge_stats"] },
  { glyph: "\u53c2", name: "Three Stars", nameZh: "\u53c2\u5bbf", desc: "Judgment & synthesis \u2014 bicameral reasoning, ensemble query, optimization, kaizen, sabha", quadrant: "west", tools: ["reasoning.bicameral", "ensemble.query", "solve_optimization", "kaizen_analyze", "sabha.convene"] },
  { glyph: "\u6597", name: "Dipper", nameZh: "\u6597\u5bbf", desc: "Strategy \u2014 homeostasis check/status, maturity assess, starter packs, cognitive modes", quadrant: "north", tools: ["homeostasis.check", "maturity.assess", "starter_packs.list", "cognitive.mode"] },
  { glyph: "\u725b", name: "Ox", nameZh: "\u725b\u5bbf", desc: "Endurance \u2014 swarm decompose/route/complete/vote/plan/resolve/status", quadrant: "north", tools: ["swarm.decompose", "swarm.route", "swarm.complete", "swarm.vote", "swarm.plan"] },
  { glyph: "\u5973", name: "Girl", nameZh: "\u5973\u5bbf", desc: "Nurture \u2014 agent register/heartbeat/list/capabilities/deregister/trust", quadrant: "north", tools: ["agent.register", "agent.heartbeat", "agent.list", "agent.capabilities", "agent.trust"] },
  { glyph: "\u865a", name: "Void", nameZh: "\u865a\u5bbf", desc: "Stillness & galaxies \u2014 galaxy CRUD/transfer/merge/sync/lineage/taxonomy, OMS, gardens", quadrant: "north", tools: ["galaxy.create", "galaxy.transfer", "galaxy.merge", "oms.export", "garden_status"] },
  { glyph: "\u5371", name: "Roof", nameZh: "\u5371\u5bbf", desc: "Shelter \u2014 ollama models/generate/chat/agent, model signing/verify, sovereign sandbox", quadrant: "north", tools: ["ollama.chat", "ollama.generate", "model.verify", "shelter.create", "shelter.execute"] },
  { glyph: "\u5ba4", name: "Encampment", nameZh: "\u5ba4\u5bbf", desc: "Community \u2014 sangha chat, broker publish/history/status, gan ying emit/listeners", quadrant: "north", tools: ["sangha_chat_send", "broker.publish", "ganying_emit", "ganying_listeners"] },
  { glyph: "\u58c1", name: "Wall", nameZh: "\u58c1\u5bbf", desc: "Boundaries \u2014 vote create/cast/analyze/list, engagement tokens issue/validate/revoke", quadrant: "north", tools: ["vote.create", "vote.cast", "vote.analyze", "engagement.issue", "engagement.validate"] },
];

const QUADRANTS = [
  { key: "east", name: "East \u00b7 Azure Dragon", element: "Wood", animal: "Dragon", season: "Spring", color: "#22c55e" },
  { key: "south", name: "South \u00b7 Vermilion Bird", element: "Fire", animal: "Phoenix", season: "Summer", color: "#ef4444" },
  { key: "west", name: "West \u00b7 White Tiger", element: "Metal", animal: "Tiger", season: "Autumn", color: "#eab308" },
  { key: "north", name: "North \u00b7 Black Tortoise", element: "Water", animal: "Tortoise", season: "Winter", color: "#3b82f6" },
] as const;

function getQuadrantIcon(q: string) {
  switch (q) {
    case "east": return <Brain size={16} />;
    case "south": return <Zap size={16} />;
    case "west": return <Shield size={16} />;
    case "north": return <Droplets size={16} />;
    default: return <Compass size={16} />;
  }
}

export function GanaMapView() {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [filterQuadrant, setFilterQuadrant] = useState<string | null>(null);

  const filteredEngines = filterQuadrant
    ? GANA_ENGINES.filter((g) => g.quadrant === filterQuadrant)
    : GANA_ENGINES;

  const selectedEngine = selectedIdx !== null ? GANA_ENGINES[selectedIdx] : null;
  const selectedQuadrant = selectedEngine
    ? QUADRANTS.find((q) => q.key === selectedEngine.quadrant)
    : null;

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      {/* Engine Map */}
      <div className="flex-1 overflow-auto">
        {/* Filter Bar */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="font-head text-xl font-bold tracking-tight uppercase text-ink">
              28 Gana Engines
            </h2>
            <p className="mt-1 font-mono text-xs uppercase tracking-widest text-dim">
              Neural Architecture of the Mandala OS
            </p>
          </div>

          <div className="flex gap-1 rounded-xl border border-border bg-surface p-1">
            <button
              onClick={() => setFilterQuadrant(null)}
              className={`rounded-lg px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition-all ${
                !filterQuadrant
                  ? "bg-lavender text-white shadow-md"
                  : "text-dim hover:text-fg"
              }`}
            >
              All
            </button>
            {QUADRANTS.map((q) => (
              <button
                key={q.key}
                onClick={() =>
                  setFilterQuadrant(filterQuadrant === q.key ? null : q.key)
                }
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition-all ${
                  filterQuadrant === q.key
                    ? "bg-lavender text-white shadow-md"
                    : "text-dim hover:text-fg"
                }`}
              >
                {getQuadrantIcon(q.key)}
                <span className="hidden lg:inline">{q.key}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Quadrant Sections */}
        <div className="space-y-10">
          {QUADRANTS.filter(
            (q) => !filterQuadrant || filterQuadrant === q.key,
          ).map((q) => {
            const engines = filteredEngines
              .map((e, i) => ({ ...e, idx: i }))
              .filter((e) => e.quadrant === q.key);
            if (engines.length === 0) return null;

            return (
              <div key={q.key}>
                <div className="mb-4 flex items-center gap-3">
                  <div
                    className="rounded-lg border border-border bg-surface p-2"
                    style={{ color: q.color }}
                  >
                    {getQuadrantIcon(q.key)}
                  </div>
                  <div>
                    <h3
                      className="font-mono text-sm font-bold uppercase tracking-widest"
                      style={{ color: q.color }}
                    >
                      {q.name}
                    </h3>
                    <p className="font-mono text-xs text-dim">
                      {q.element} \u00b7 {q.animal} \u00b7 {q.season}
                    </p>
                  </div>
                  <div className="ml-4 h-px flex-1 bg-gradient-to-r from-border to-transparent opacity-50" />
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {engines.map((engine) => (
                    <button
                      key={engine.idx}
                      onClick={() => setSelectedIdx(engine.idx)}
                      className={`group rounded-2xl border p-4 text-left transition-all ${
                        selectedIdx === engine.idx
                          ? "border-lavender bg-lavender-bg shadow-sm"
                          : "border-transparent bg-surface hover:border-border hover:shadow-md"
                      }`}
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="text-lg font-bold"
                            style={{ color: q.color }}
                          >
                            {engine.glyph}
                          </span>
                          <span
                            className={`font-mono text-xs uppercase tracking-wider ${
                              selectedIdx === engine.idx
                                ? "text-lavender"
                                : "text-fg"
                            }`}
                          >
                            {engine.name}
                          </span>
                        </div>
                        <ChevronRight
                          size={14}
                          className={`transition-transform duration-300 ${
                            selectedIdx === engine.idx
                              ? "rotate-90 text-lavender"
                              : "text-dim opacity-0 group-hover:translate-x-0.5 group-hover:opacity-100"
                          }`}
                        />
                      </div>
                      <p className="line-clamp-2 text-xs italic leading-relaxed text-muted">
                        {engine.desc}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail Inspector */}
      {selectedEngine && selectedQuadrant && (
        <div className="z-10 flex w-full flex-col rounded-2xl border border-border bg-surface shadow-2xl transition-all duration-300 lg:w-[340px]">
          {/* Header */}
          <div className="border-b border-border bg-surface-alt/30 p-6">
            <div className="mb-4 flex items-center gap-4">
              <div
                className="rounded-2xl border border-border bg-bg p-3 text-4xl font-bold"
                style={{ color: selectedQuadrant.color }}
              >
                {selectedEngine.glyph}
              </div>
              <div>
                <h3 className="font-head text-xl font-bold tracking-tight uppercase text-ink">
                  {selectedEngine.name}
                </h3>
                <div className="mt-0.5 font-mono text-xs uppercase tracking-widest text-dim">
                  {selectedEngine.nameZh} \u00b7 {selectedEngine.quadrant} quadrant
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-border/50 bg-bg p-2 text-center">
                <div className="font-mono text-xs uppercase tracking-tighter text-dim">
                  Element
                </div>
                <div className="text-sm font-bold capitalize text-fg">
                  {selectedQuadrant.element}
                </div>
              </div>
              <div className="rounded-xl border border-border/50 bg-bg p-2 text-center">
                <div className="font-mono text-xs uppercase tracking-tighter text-dim">
                  Guardian
                </div>
                <div className="text-sm font-bold capitalize text-fg">
                  {selectedQuadrant.animal}
                </div>
              </div>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 space-y-8 overflow-auto p-6">
            <section>
              <h4 className="mb-3 font-mono text-xs uppercase tracking-widest text-dim">
                Functional Role
              </h4>
              <p className="border-l-2 border-lavender/20 pl-4 text-sm italic leading-relaxed text-muted">
                {selectedEngine.desc}
              </p>
            </section>

            <section>
              <h4 className="mb-4 font-mono text-xs uppercase tracking-widest text-dim">
                Associated Tools ({selectedEngine.tools.length})
              </h4>
              <div className="space-y-2">
                {selectedEngine.tools.map((tool) => (
                  <div
                    key={tool}
                    className="group flex cursor-pointer items-center gap-3 rounded-xl border border-border/50 bg-bg p-2.5 transition-all hover:border-lavender/30"
                  >
                    <div className="h-1.5 w-1.5 rounded-full bg-lavender/40 transition-colors group-hover:bg-lavender" />
                    <span className="truncate font-mono text-xs font-bold text-muted transition-colors group-hover:text-lavender">
                      {tool}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
