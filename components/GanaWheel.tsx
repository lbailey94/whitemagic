/**
 * Gana Celestial Wheel — Interactive 28-section mandala
 *
 * Ported from whitemagic-aux/whitemagic-frontend/web/js/gana-wheel.js
 * Adapted to React with Canvas 2D, drag physics, auto-rotation, and
 * a React-managed info card.
 *
 * Each section represents a Lunar Mansion (Xiu) engine, colored by
 * quadrant: East (Azure Dragon), South (Vermilion Bird), West (White
 * Tiger), North (Black Tortoise).
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface Gana {
  glyph: string;
  name: string;
  nameZh: string;
  desc: string;
  quadrant: "east" | "south" | "west" | "north";
  tools: string;
}

const GANAS: Gana[] = [
  // East — Azure Dragon (Wood/Spring) — Green hues
  { glyph: "\u89d2", name: "Horn", nameZh: "\u89d2\u5bbf", desc: "Session initialization — bootstrap, create, resume, checkpoint, handoff", quadrant: "east", tools: "create_session, resume_session, session_bootstrap, checkpoint_session, session_handoff" },
  { glyph: "\u4ea2", name: "Neck", nameZh: "\u4ea2\u5bbf", desc: "Memory creation — create, update, import, delete, clone memories", quadrant: "east", tools: "create_memory, update_memory, delete_memory, import_memories, thought_clone" },
  { glyph: "\u6c10", name: "Root", nameZh: "\u6c10\u5bbf", desc: "System health — health report, Rust status/audit, state summary, ship check", quadrant: "east", tools: "health_report, rust_status, rust_audit, state.summary, ship.check" },
  { glyph: "\u623f", name: "Room", nameZh: "\u623f\u5bbf", desc: "Resource locks & privacy — sangha locks, sandbox, hermit crab mode, MCP integrity", quadrant: "east", tools: "sangha_lock, hermit.status, sandbox.status, mcp_integrity.verify" },
  { glyph: "\u5fc3", name: "Heart", nameZh: "\u5fc3\u5bbf", desc: "Session context — scratchpad create/update/finalize, handoff, context pack", quadrant: "east", tools: "scratchpad, scratchpad_create, context.pack, session.handoff" },
  { glyph: "\u5c3e", name: "Tail", nameZh: "\u5c3e\u5bbf", desc: "Performance & acceleration — SIMD ops, cascade execution, token reporting", quadrant: "east", tools: "simd.cosine, simd.batch, execute_cascade, token_report" },
  { glyph: "\u7b95", name: "Basket", nameZh: "\u7b95\u5bbf", desc: "Wisdom & search — vector search, hybrid recall, graph walk, JIT research, batch read", quadrant: "east", tools: "search_memories, hybrid_recall, graph_walk, vector.search, jit_research" },
  // South — Vermilion Bird (Fire/Summer) — Red/Orange hues
  { glyph: "\u9b3c", name: "Ghost", nameZh: "\u9b3c\u5bbf", desc: "Introspection & web — gnosis, telemetry, capabilities, web search/fetch, browser automation", quadrant: "south", tools: "gnosis, capabilities, web_search, web_fetch, browser_navigate" },
  { glyph: "\u67f3", name: "Willow", nameZh: "\u67f3\u5bbf", desc: "Resilience — rate limiter, grimoire spells/suggest/cast, oracle divination", quadrant: "south", tools: "grimoire_list, grimoire_cast, cast_oracle, rate_limiter.stats" },
  { glyph: "\u661f", name: "Star", nameZh: "\u661f\u5bbf", desc: "Governance — governor validate/set-goal/drift/budget, dharma rules, forge", quadrant: "south", tools: "governor_validate, governor_set_goal, dharma_rules, forge.status" },
  { glyph: "\u5f20", name: "Net", nameZh: "\u5f20\u5bbf", desc: "Capture & filtering — prompt render/list/reload, karma verify chain", quadrant: "south", tools: "prompt.render, prompt.list, prompt.reload, karma.verify_chain" },
  { glyph: "\u7ffc", name: "Wings", nameZh: "\u7ffc\u5bbf", desc: "Deployment & export — export memories, audit export, mesh broadcast/status", quadrant: "south", tools: "export_memories, audit.export, mesh.broadcast, mesh.status" },
  { glyph: "\u8f78", name: "Chariot", nameZh: "\u8f78\u5bbf", desc: "Archaeology & KG — search/stats/digest, KG extract/query/top, marketplace", quadrant: "south", tools: "archaeology_search, archaeology_stats, kg.extract, kg.query, marketplace.discover" },
  { glyph: "\u8c50", name: "Abundance", nameZh: "\u8c50\u5bbf", desc: "Regeneration — dream cycle, serendipity, entity resolve, narrative compress, ILP payments", quadrant: "south", tools: "dream_start, dream_now, serendipity_surface, entity_resolve, ilp.send" },
  // West — White Tiger (Metal/Autumn) — Gold/Silver hues
  { glyph: "\u594e", name: "Legs", nameZh: "\u594e\u5bbf", desc: "Ethics & balance — ethics eval, boundaries, consent, harmony vector, wu xing balance", quadrant: "west", tools: "evaluate_ethics, check_boundaries, verify_consent, harmony_vector, wu_xing_balance" },
  { glyph: "\u5a04", name: "Mound", nameZh: "\u5a04\u5bbf", desc: "Metrics & caching — hologram view, metric tracking, yin-yang balance, green score", quadrant: "west", tools: "view_hologram, track_metric, get_yin_yang_balance, green.report" },
  { glyph: "\u80c3", name: "Stomach", nameZh: "\u80c3\u5bbf", desc: "Digestion & tasks — pipeline create/list/status, task distribute/route/complete", quadrant: "west", tools: "pipeline.create, task.distribute, task.route_smart, task.complete" },
  { glyph: "\u6634", name: "Hairy Head", nameZh: "\u6634\u5bbf", desc: "Detail & debug — salience, anomaly detection, otel metrics/spans, karma report/trace", quadrant: "west", tools: "salience.spotlight, anomaly.check, otel.metrics, karma_report, karmic_trace" },
  { glyph: "\u6bd5", name: "Extended Net", nameZh: "\u6bd5\u5bbf", desc: "Pattern connectivity — pattern search, cluster stats, learning, coherence boost, resonance", quadrant: "west", tools: "pattern_search, cluster_stats, learning.patterns, coherence_boost, resonance_trace" },
  { glyph: "\u89dc", name: "Turtle Beak", nameZh: "\u89dc\u5bbf", desc: "Precision — edge/bitnet inference, edge batch, low-latency compute stats", quadrant: "west", tools: "edge_infer, bitnet_infer, edge_batch_infer, edge_stats" },
  { glyph: "\u53c2", name: "Three Stars", nameZh: "\u53c2\u5bbf", desc: "Judgment & synthesis — bicameral reasoning, ensemble query, optimization, kaizen, sabha", quadrant: "west", tools: "reasoning.bicameral, ensemble.query, solve_optimization, kaizen_analyze, sabha.convene" },
  // North — Black Tortoise (Water/Winter) — Blue hues
  { glyph: "\u6597", name: "Dipper", nameZh: "\u6597\u5bbf", desc: "Strategy — homeostasis check/status, maturity assess, starter packs, cognitive modes", quadrant: "north", tools: "homeostasis.check, maturity.assess, starter_packs.list, cognitive.mode" },
  { glyph: "\u725b", name: "Ox", nameZh: "\u725b\u5bbf", desc: "Endurance — swarm decompose/route/complete/vote/plan/resolve/status", quadrant: "north", tools: "swarm.decompose, swarm.route, swarm.complete, swarm.vote, swarm.plan" },
  { glyph: "\u5973", name: "Girl", nameZh: "\u5973\u5bbf", desc: "Nurture — agent register/heartbeat/list/capabilities/deregister/trust", quadrant: "north", tools: "agent.register, agent.heartbeat, agent.list, agent.capabilities, agent.trust" },
  { glyph: "\u865a", name: "Void", nameZh: "\u865a\u5bbf", desc: "Stillness & galaxies — galaxy CRUD/transfer/merge/sync/lineage/taxonomy, OMS, gardens", quadrant: "north", tools: "galaxy.create, galaxy.transfer, galaxy.merge, oms.export, garden_status" },
  { glyph: "\u5371", name: "Roof", nameZh: "\u5371\u5bbf", desc: "Shelter — ollama models/generate/chat/agent, model signing/verify, sovereign sandbox", quadrant: "north", tools: "ollama.chat, ollama.generate, model.verify, shelter.create, shelter.execute" },
  { glyph: "\u5ba4", name: "Encampment", nameZh: "\u5ba4\u5bbf", desc: "Community — sangha chat, broker publish/history/status, gan ying emit/listeners", quadrant: "north", tools: "sangha_chat_send, broker.publish, ganying_emit, ganying_listeners" },
  { glyph: "\u58c1", name: "Wall", nameZh: "\u58c1\u5bbf", desc: "Boundaries — vote create/cast/analyze/list, engagement tokens issue/validate/revoke", quadrant: "north", tools: "vote.create, vote.cast, vote.analyze, engagement.issue, engagement.validate" },
];

const QUADRANT_COLORS: Record<string, { base: number; range: number; label: string; labelZh: string }> = {
  east: { base: 120, range: 60, label: "Wood \u00b7 Spring \u00b7 Azure Dragon \u9f8d", labelZh: "\u6728 \u00b7 \u6625 \u00b7 \u9752\u9f99" },
  south: { base: 10, range: 50, label: "Fire \u00b7 Summer \u00b7 Vermilion Bird \u9cf3", labelZh: "\u706b \u00b7 \u590f \u00b7 \u6731\u96c0" },
  west: { base: 40, range: 30, label: "Metal \u00b7 Autumn \u00b7 White Tiger \u864e", labelZh: "\u91d1 \u00b7 \u79cb \u00b7 \u767d\u864e" },
  north: { base: 220, range: 60, label: "Water \u00b7 Winter \u00b7 Black Tortoise \u9f9c", labelZh: "\u6c34 \u00b7 \u51ac \u00b7 \u7384\u6b66" },
};

const SLICE = (Math.PI * 2) / 28;

function getHue(idx: number, hueShift: number): number {
  const g = GANAS[idx];
  const qc = QUADRANT_COLORS[g.quadrant];
  const localIdx = idx % 7;
  return (qc.base + (localIdx / 7) * qc.range + hueShift) % 360;
}

export function GanaWheel({ size = 600 }: { size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const selectedRef = useRef(0);

  // Keep ref in sync for the animation loop
  useEffect(() => {
    selectedRef.current = selectedIdx;
  }, [selectedIdx]);

  const selectGana = useCallback((idx: number) => {
    setSelectedIdx(idx);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const SIZE = size;
    canvas.width = SIZE * dpr;
    canvas.height = SIZE * dpr;
    canvas.style.width = SIZE + "px";
    canvas.style.height = SIZE + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const CX = SIZE / 2;
    const CY = SIZE / 2;
    const OUTER_R = SIZE * 0.46;
    const INNER_R = SIZE * 0.26;
    const GLYPH_R = (OUTER_R + INNER_R) / 2;

    let rotation = 0;
    let velocity = 0;
    let isDragging = false;
    let lastAngle = 0;
    let autoTimer = 0;
    let hueShift = 0;
    let raf = 0;
    let disposed = false;

    function getAngle(x: number, y: number): number {
      return Math.atan2(y - CY, x - CX);
    }

    function getSelectedFromRotation(): number {
      const normalizedRot = (((-rotation % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2));
      return Math.floor(normalizedRot / SLICE) % 28;
    }

    function draw() {
      if (disposed) return;
      raf = requestAnimationFrame(draw);

      ctx!.clearRect(0, 0, SIZE, SIZE);
      if (!reducedMotion) {
        hueShift = (hueShift + 0.02) % 360;
      }

      // Physics
      if (!isDragging) {
        if (Math.abs(velocity) > 0.0001) {
          rotation += velocity;
          velocity *= 0.97;
        } else if (!reducedMotion) {
          autoTimer++;
          if (autoTimer > 300) {
            rotation += 0.002;
          }
        }
      }

      // Draw sections
      for (let i = 0; i < 28; i++) {
        const startAngle = i * SLICE + rotation - Math.PI / 2;
        const endAngle = startAngle + SLICE;
        const hue = getHue(i, hueShift);
        const isSelected = i === selectedRef.current;
        const sat = isSelected ? "85%" : "55%";
        const lit = isSelected ? "55%" : "35%";
        const alpha = isSelected ? 0.95 : 0.7;

        ctx!.beginPath();
        ctx!.arc(CX, CY, OUTER_R, startAngle, endAngle);
        ctx!.arc(CX, CY, INNER_R, endAngle, startAngle, true);
        ctx!.closePath();
        ctx!.fillStyle = `hsla(${hue},${sat},${lit},${alpha})`;
        ctx!.fill();
        ctx!.strokeStyle = `hsla(${hue},70%,70%,0.4)`;
        ctx!.lineWidth = isSelected ? 2.5 : 1;
        ctx!.stroke();

        if (isSelected) {
          ctx!.shadowColor = `hsla(${hue},100%,60%,0.6)`;
          ctx!.shadowBlur = 20;
          ctx!.beginPath();
          ctx!.arc(CX, CY, OUTER_R, startAngle, endAngle);
          ctx!.arc(CX, CY, INNER_R, endAngle, startAngle, true);
          ctx!.closePath();
          ctx!.strokeStyle = `hsla(${hue},100%,75%,0.8)`;
          ctx!.lineWidth = 3;
          ctx!.stroke();
          ctx!.shadowBlur = 0;
        }

        // Glyph
        const midAngle = startAngle + SLICE / 2;
        const gx = CX + Math.cos(midAngle) * GLYPH_R;
        const gy = CY + Math.sin(midAngle) * GLYPH_R;

        ctx!.save();
        ctx!.translate(gx, gy);
        ctx!.rotate(midAngle + Math.PI / 2);
        ctx!.font = `bold ${isSelected ? 22 : 17}px 'Noto Serif SC', serif`;
        ctx!.fillStyle = isSelected ? "#fff" : `hsla(${hue},60%,85%,0.9)`;
        ctx!.textAlign = "center";
        ctx!.textBaseline = "middle";
        ctx!.shadowColor = `hsla(${hue},100%,50%,0.5)`;
        ctx!.shadowBlur = isSelected ? 12 : 4;
        ctx!.fillText(GANAS[i].glyph, 0, 0);
        ctx!.shadowBlur = 0;
        ctx!.restore();
      }

      // Center circle
      const grad = ctx!.createRadialGradient(CX, CY, 0, CX, CY, INNER_R * 0.95);
      grad.addColorStop(0, "rgba(30,25,40,0.95)");
      grad.addColorStop(1, "rgba(20,15,30,0.8)");
      ctx!.beginPath();
      ctx!.arc(CX, CY, INNER_R * 0.95, 0, Math.PI * 2);
      ctx!.fillStyle = grad;
      ctx!.fill();

      // Center text
      ctx!.font = 'bold 28px "Noto Serif SC", serif';
      ctx!.fillStyle = "#b8a9d4";
      ctx!.textAlign = "center";
      ctx!.textBaseline = "middle";
      ctx!.fillText("\u4e8c\u5341\u516b\u5bbf", CX, CY - 14);
      ctx!.font = '13px "Crimson Pro", serif';
      ctx!.fillStyle = "#9a8c7e";
      ctx!.fillText("28 Lunar Mansions", CX, CY + 14);

      // Selection pointer (top)
      ctx!.beginPath();
      ctx!.moveTo(CX, CY - OUTER_R - 12);
      ctx!.lineTo(CX - 10, CY - OUTER_R - 28);
      ctx!.lineTo(CX + 10, CY - OUTER_R - 28);
      ctx!.closePath();
      ctx!.fillStyle = "#b8a9d4";
      ctx!.fill();
    }

    // Mouse interaction
    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      velocity = 0;
      autoTimer = 0;
      const rect = canvas.getBoundingClientRect();
      lastAngle = getAngle(e.clientX - rect.left, e.clientY - rect.top);
      canvas.style.cursor = "grabbing";
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const rect = canvas.getBoundingClientRect();
      const angle = getAngle(e.clientX - rect.left, e.clientY - rect.top);
      let delta = angle - lastAngle;
      if (delta > Math.PI) delta -= Math.PI * 2;
      if (delta < -Math.PI) delta += Math.PI * 2;
      rotation += delta;
      velocity = delta;
      lastAngle = angle;
      const newIdx = getSelectedFromRotation();
      if (newIdx !== selectedRef.current) {
        selectGana(newIdx);
      }
    };

    const onMouseUp = () => {
      if (isDragging) {
        isDragging = false;
        canvas.style.cursor = "grab";
      }
    };

    // Touch interaction
    const onTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      const rect = canvas.getBoundingClientRect();
      isDragging = true;
      velocity = 0;
      autoTimer = 0;
      lastAngle = getAngle(touch.clientX - rect.left, touch.clientY - rect.top);
    };

    const onTouchMove = (e: TouchEvent) => {
      if (!isDragging) return;
      const touch = e.touches[0];
      const rect = canvas.getBoundingClientRect();
      const angle = getAngle(touch.clientX - rect.left, touch.clientY - rect.top);
      let delta = angle - lastAngle;
      if (delta > Math.PI) delta -= Math.PI * 2;
      if (delta < -Math.PI) delta += Math.PI * 2;
      rotation += delta;
      velocity = delta;
      lastAngle = angle;
      const newIdx = getSelectedFromRotation();
      if (newIdx !== selectedRef.current) {
        selectGana(newIdx);
      }
    };

    const onTouchEnd = () => {
      isDragging = false;
    };

    // Click to select
    const onClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const angle = getAngle(x, y);
      const dist = Math.hypot(x - CX, y - CY);
      if (dist >= INNER_R && dist <= OUTER_R) {
        let clickAngle = angle + Math.PI / 2 - rotation;
        clickAngle = ((clickAngle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
        const idx = Math.floor(clickAngle / SLICE) % 28;
        selectGana(idx);
        // Spin to bring selected to top
        const targetRot = -(idx * SLICE + SLICE / 2);
        const diff = targetRot - (rotation % (Math.PI * 2));
        velocity = diff * 0.05;
      }
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("touchstart", onTouchStart, { passive: true });
    canvas.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd);
    canvas.addEventListener("click", onClick);
    canvas.style.cursor = "grab";

    raf = requestAnimationFrame(draw);

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      canvas.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("touchstart", onTouchStart);
      canvas.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      canvas.removeEventListener("click", onClick);
    };
  }, [size, selectGana]);

  const gana = GANAS[selectedIdx];
  const hue = getHue(selectedIdx, 0);
  const qc = QUADRANT_COLORS[gana.quadrant];

  return (
    <div className="flex flex-col items-center gap-8 lg:flex-row lg:items-start lg:justify-center">
      {/* Canvas */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`28 Gana Celestial Wheel — currently showing ${gana.name} (${gana.nameZh})`}
        />
      </div>

      {/* Info Card */}
      <div
        className="w-full max-w-md rounded-2xl border-2 bg-surface p-6 shadow-lg transition-all"
        style={{ borderColor: `hsla(${hue},60%,50%,0.4)` }}
      >
        <div
          className="mb-4 flex items-center gap-4 border-b pb-4"
          style={{ borderColor: `hsl(${hue},70%,50%)` }}
        >
          <span
            className="text-5xl font-bold"
            style={{ color: `hsl(${hue},80%,65%)` }}
          >
            {gana.glyph}
          </span>
          <div>
            <h3 className="font-head text-xl font-semibold text-ink">
              {gana.name}{" "}
              <span className="text-lg text-dim">{gana.nameZh}</span>
            </h3>
            <p className="mt-1 font-mono text-xs text-dim">{qc.label}</p>
          </div>
        </div>

        <p className="mb-4 text-sm leading-relaxed text-muted">{gana.desc}</p>

        <div className="space-y-2">
          <span className="font-mono text-xs uppercase tracking-wider text-dim">
            Key tools
          </span>
          <div className="flex flex-wrap gap-2">
            {gana.tools.split(", ").map((tool) => (
              <code
                key={tool}
                className="rounded bg-lavender-bg px-2 py-1 font-mono text-xs text-lavender"
              >
                {tool}
              </code>
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
          <span className="font-mono text-xs text-dim">
            Gana {selectedIdx + 1} of 28
          </span>
          <div className="flex gap-2">
            <button
              onClick={() =>
                selectGana((selectedIdx - 1 + 28) % 28)
              }
              className="rounded-lg border border-border px-3 py-1.5 font-mono text-xs text-muted transition hover:border-lavender hover:text-lavender"
            >
              Prev
            </button>
            <button
              onClick={() => selectGana((selectedIdx + 1) % 28)}
              className="rounded-lg border border-border px-3 py-1.5 font-mono text-xs text-muted transition hover:border-lavender hover:text-lavender"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
