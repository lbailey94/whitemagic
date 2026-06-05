"use client";

import { useState, useEffect } from "react";
import { neoStore } from "@/store/neoStore";

/**
 * GOD Knowledge Sphere — an orbital constellation of connected nodes
 * visible from page load with constellation sparks between random points.
 */
export function GodSphere({
  size = 640,
}: {
  size?: number;
}) {
  const [entered, setEntered] = useState(false);
  const [sparks, setSparks] = useState<
    { id: number; x1: number; y1: number; x2: number; y2: number; hue: number; delay: number }[]
  >([]);

  // Fade in on mount
  useEffect(() => {
    const t = setTimeout(() => setEntered(true), 600);
    return () => clearTimeout(t);
  }, []);

  // Lightning chain sparks: nearest-neighbor hops, 2-7 segments, neuron-fire spread
  useEffect(() => {
    if (!entered) return;

    let timeout: ReturnType<typeof setTimeout>;
    const schedule = () => {
      const ls = neoStore.lightning;
      timeout = setTimeout(() => {
        const cx = size / 2;
        const cy = size / 2;
        const orbitR = size * 0.38;
        const rings = [
          { r: orbitR * 0.35, count: 6 },
          { r: orbitR * 0.6, count: 10 },
          { r: orbitR * 0.85, count: 14 },
        ];

        // Build all node positions
        const allNodes: { x: number; y: number }[] = [];
        rings.forEach((ring) => {
          for (let i = 0; i < ring.count; i++) {
            const angle = (i / ring.count) * Math.PI * 2;
            allNodes.push({
              x: cx + Math.cos(angle) * ring.r,
              y: cy + Math.sin(angle) * ring.r,
            });
          }
        });

        // Start from a random node
        let currentIdx = Math.floor(Math.random() * allNodes.length);
        const visited = new Set<number>([currentIdx]);
        const chainLen = ls.minHops + Math.floor(Math.random() * (ls.maxHops - ls.minHops + 1));
        const baseHue = Math.floor(Math.random() * 360);
        const chainBaseId = Date.now();

        // Build chain: hop to nearest unvisited neighbor
        const segments: { id: number; x1: number; y1: number; x2: number; y2: number; hue: number; delay: number }[] = [];
        for (let hop = 0; hop < chainLen; hop++) {
          const from = allNodes[currentIdx];

          let nearestIdx = -1;
          let nearestDist = Infinity;
          for (let i = 0; i < allNodes.length; i++) {
            if (visited.has(i)) continue;
            const dx = allNodes[i].x - from.x;
            const dy = allNodes[i].y - from.y;
            const dist = dx * dx + dy * dy;
            if (dist < nearestDist) {
              nearestDist = dist;
              nearestIdx = i;
            }
          }

          if (nearestIdx === -1) break;

          const to = allNodes[nearestIdx];
          segments.push({
            id: chainBaseId + hop,
            x1: from.x,
            y1: from.y,
            x2: to.x,
            y2: to.y,
            hue: (baseHue + hop * 25) % 360,
            delay: hop * 80,
          });

          visited.add(nearestIdx);
          currentIdx = nearestIdx;
        }

        setSparks((prev) => [
          ...prev.slice(-20),
          ...segments,
        ]);

        // Auto-remove this chain
        setTimeout(() => {
          setSparks((prev) => prev.filter((s) => s.id < chainBaseId || s.id >= chainBaseId + chainLen));
        }, 2200);

        schedule();
      }, ls.frequencyMs + Math.random() * ls.frequencyVariance);
    };
    schedule();

    return () => clearTimeout(timeout);
  }, [entered, size]);

  const cx = size / 2;
  const cy = size / 2;
  const orbitR = size * 0.38;

  const rings = [
    { r: orbitR * 0.35, count: 6, speed: 40 },
    { r: orbitR * 0.6, count: 10, speed: 60 },
    { r: orbitR * 0.85, count: 14, speed: 80 },
  ];

  const nodes: { x: number; y: number; ring: number; idx: number }[] = [];
  rings.forEach((ring, ri) => {
    for (let i = 0; i < ring.count; i++) {
      const angle = (i / ring.count) * Math.PI * 2;
      nodes.push({
        x: cx + Math.cos(angle) * ring.r,
        y: cy + Math.sin(angle) * ring.r,
        ring: ri,
        idx: i,
      });
    }
  });

  // Connections: connect some nodes to their neighbors
  const connections: { x1: number; y1: number; x2: number; y2: number }[] = [];
  rings.forEach((ring, ri) => {
    for (let i = 0; i < ring.count; i++) {
      const a = nodes.find((n) => n.ring === ri && n.idx === i)!;
      const b = nodes.find((n) => n.ring === ri && n.idx === (i + 1) % ring.count)!;
      connections.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
      if (ri < rings.length - 1 && i % 3 === 0) {
        const outer = nodes.find(
          (n) => n.ring === ri + 1 && n.idx === Math.floor((i / ring.count) * rings[ri + 1].count),
        );
        if (outer) connections.push({ x1: a.x, y1: a.y, x2: outer.x, y2: outer.y });
      }
    }
  });

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className={`pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-[2500ms] ${
        entered ? "opacity-100" : "opacity-0 scale-75"
      }`}
      style={{ width: size, height: size }}
    >
      {/* Orbital rings */}
      {rings.map((ring, i) => (
        <circle
          key={`ring-${i}`}
          cx={cx}
          cy={cy}
          r={ring.r}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.5}
          opacity={0.15 - i * 0.03}
          className="text-lavender"
          style={{
            animation: `god-orbit ${ring.speed}s linear infinite`,
            transformOrigin: `${cx}px ${cy}px`,
          }}
        />
      ))}

      {/* Connections */}
      {connections.map((c, i) => (
        <line
          key={`conn-${i}`}
          x1={c.x1}
          y1={c.y1}
          x2={c.x2}
          y2={c.y2}
          stroke="currentColor"
          strokeWidth={0.4}
          opacity={0.2}
          className="text-lavender"
        />
      ))}

      {/* Nodes */}
      {nodes.map((n, i) => (
        <circle
          key={`node-${i}`}
          cx={n.x}
          cy={n.y}
          r={n.ring === 0 ? 2.5 : n.ring === 1 ? 2 : 1.5}
          fill="currentColor"
          opacity={0.5 + n.ring * 0.15}
          className="text-lavender"
          style={{
            animation: `god-pulse ${3 + (i % 4)}s ease-in-out infinite`,
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}

      {/* Constellation Sparks */}
      {sparks.map((s) => (
        <line
          key={s.id}
          x1={s.x1}
          y1={s.y1}
          x2={s.x2}
          y2={s.y2}
          stroke={`hsl(${s.hue}, 90%, 72%)`}
          strokeWidth={1.4}
          strokeLinecap="round"
          opacity={0}
          style={{
            animation: "god-spark 1.4s ease-out forwards",
            animationDelay: `${s.delay}ms`,
          }}
        />
      ))}

      {/* Center glow */}
      <circle
        cx={cx}
        cy={cy}
        r={8}
        fill="none"
        stroke="currentColor"
        strokeWidth={0.5}
        opacity={0.4}
        className="text-lavender"
        style={{ animation: "god-pulse 4s ease-in-out infinite" }}
      />
    </svg>
  );
}
