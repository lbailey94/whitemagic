/**
 * GalacticVisualization — Canvas 2D top-down galaxy view
 *
 * Renders memories as glowing dots in 5 concentric galactic zones,
 * matching the core's galactic_map.py zone boundaries exactly:
 *   Core: 0.00-0.15, Inner Rim: 0.15-0.40, Mid Band: 0.40-0.65,
 *   Outer Rim: 0.65-0.85, Far Edge: 0.85-1.00
 *
 * Radial position = galactic_distance (importance proxy in browser demo)
 * Angular position = deterministic hash of content (stable distribution)
 * Dot size = importance
 * Dot brightness = access_count
 * Color = zone classification
 */

"use client";

import { useRef, useEffect, useState, useCallback } from "react";

export interface GalaxyMemory {
  id: number;
  content: string;
  memory_type: string;
  importance: number;
  galactic_distance: number;
  galactic_zone: string;
  tags: string[];
  access_count: number;
  created_at: string;
}

interface ZoneConfig {
  label: string;
  min: number;
  max: number;
  color: string;
  glow: string;
}

const ZONES: Record<string, ZoneConfig> = {
  CORE: { label: "Core", min: 0.0, max: 0.15, color: "#a855f7", glow: "#c084fc" },
  INNER_RIM: { label: "Inner Rim", min: 0.15, max: 0.4, color: "#6366f1", glow: "#818cf8" },
  MID_BAND: { label: "Mid Band", min: 0.4, max: 0.65, color: "#3b82f6", glow: "#60a5fa" },
  OUTER_RIM: { label: "Outer Rim", min: 0.65, max: 0.85, color: "#0891b2", glow: "#22d3ee" },
  FAR_EDGE: { label: "Far Edge", min: 0.85, max: 1.0, color: "#64748b", glow: "#94a3b8" },
};

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function classifyZone(distance: number): string {
  if (distance < 0.15) return "CORE";
  if (distance < 0.4) return "INNER_RIM";
  if (distance < 0.65) return "MID_BAND";
  if (distance < 0.85) return "OUTER_RIM";
  return "FAR_EDGE";
}

interface GalacticVisualizationProps {
  memories: GalaxyMemory[];
  height?: number;
  onSelect?: (mem: GalaxyMemory) => void;
  selectedId?: number | null;
}

export function GalacticVisualization({
  memories,
  height = 480,
  onSelect,
  selectedId,
}: GalacticVisualizationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const rotationRef = useRef(0);
  const hoverRef = useRef<{ mem: GalaxyMemory; x: number; y: number } | null>(null);
  const [hovered, setHovered] = useState<{ mem: GalaxyMemory; x: number; y: number } | null>(null);
  const [width, setWidth] = useState(600);
  const memoriesRef = useRef(memories);
  const selectedRef = useRef(selectedId);

  useEffect(() => {
    memoriesRef.current = memories;
  }, [memories]);

  useEffect(() => {
    selectedRef.current = selectedId;
  }, [selectedId]);

  // Responsive width
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setWidth(containerRef.current.clientWidth);
      }
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf: number;

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const maxRadius = Math.min(w, h) / 2 - 30;
      const rotation = rotationRef.current;

      ctx.clearRect(0, 0, w, h);

      // Background — deep space gradient
      const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius * 1.3);
      bgGrad.addColorStop(0, "#0a0a1a");
      bgGrad.addColorStop(0.5, "#050510");
      bgGrad.addColorStop(1, "#000000");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Zone rings
      const zoneEntries = Object.entries(ZONES);
      for (const [, zone] of zoneEntries) {
        const innerR = zone.min * maxRadius;
        const outerR = zone.max * maxRadius;

        // Zone fill (very subtle)
        ctx.beginPath();
        ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
        ctx.arc(cx, cy, innerR, 0, Math.PI * 2, true);
        ctx.fillStyle = zone.color + "08";
        ctx.fill();

        // Zone boundary
        ctx.beginPath();
        ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
        ctx.strokeStyle = zone.color + "30";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Zone labels (rotated with the galaxy)
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      for (const [, zone] of zoneEntries) {
        const midR = ((zone.min + zone.max) / 2) * maxRadius;
        const angle = rotation + Math.PI / 2;
        const lx = cx + Math.cos(angle) * midR;
        const ly = cy + Math.sin(angle) * midR;
        ctx.fillStyle = zone.color + "60";
        ctx.fillText(zone.label.toUpperCase(), lx, ly);
      }

      // Core glow
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius * 0.15);
      coreGrad.addColorStop(0, "#a855f720");
      coreGrad.addColorStop(1, "#a855f700");
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, maxRadius * 0.15, 0, Math.PI * 2);
      ctx.fill();

      // Memory dots
      const mems = memoriesRef.current;
      for (const mem of mems) {
        const distance = mem.galactic_distance;
        const zoneKey = classifyZone(distance);
        const zone = ZONES[zoneKey];
        if (!zone) continue;

        // Angular position from content hash
        const hash = hashString(mem.content || String(mem.id));
        const angle = (hash % 360) * (Math.PI / 180) + rotation;

        // Radial position with slight jitter within zone
        const zoneWidth = zone.max - zone.min;
        const zoneProgress = (distance - zone.min) / zoneWidth;
        const jitter = ((hash >> 8) % 100) / 100 * 0.3;
        const r = (zone.min + zoneProgress * (1 - jitter) + jitter * 0.5) * maxRadius;

        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;

        // Dot size by importance (3-8px)
        const size = 3 + mem.importance * 5;

        // Brightness by access count
        const brightness = 0.4 + Math.min(mem.access_count / 10, 1) * 0.6;

        // Selected highlight
        const isSelected = selectedRef.current === mem.id;

        // Glow
        const glowSize = size * (isSelected ? 4 : 2.5);
        const glowGrad = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
        glowGrad.addColorStop(0, zone.glow + Math.round(brightness * 180).toString(16).padStart(2, "0"));
        glowGrad.addColorStop(1, zone.glow + "00");
        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        ctx.fill();

        // Dot
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fillStyle = zone.color;
        ctx.globalAlpha = brightness;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Selected ring
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(x, y, size + 4, 0, Math.PI * 2);
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Store position for hit testing
        (mem as GalaxyMemory & { _x?: number; _y?: number })._x = x;
        (mem as GalaxyMemory & { _x?: number; _y?: number })._y = y;
      }

      // Hover tooltip
      const hov = hoverRef.current;
      if (hov) {
        const text = hov.mem.content.length > 60
          ? hov.mem.content.slice(0, 57) + "..."
          : hov.mem.content;
        const zone = ZONES[classifyZone(hov.mem.galactic_distance)];

        ctx.font = "12px monospace";
        const metrics = ctx.measureText(text);
        const tw = Math.max(metrics.width + 16, 120);
        const th = 44;
        let tx = hov.x + 12;
        let ty = hov.y - th - 8;

        if (tx + tw > w) tx = hov.x - tw - 12;
        if (ty < 0) ty = hov.y + 12;

        ctx.fillStyle = "#0a0a0f";
        ctx.strokeStyle = zone.color + "80";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(tx, ty, tw, th, 6);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = zone.color;
        ctx.textAlign = "left";
        ctx.fillText(zone.label, tx + 8, ty + 16);

        ctx.fillStyle = "#c0c0c0";
        ctx.fillText(text, tx + 8, ty + 34);
      }

      // Slow rotation
      rotationRef.current += 0.0008;
      raf = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(raf);
  }, []);

  // Mouse interaction
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const mems = memoriesRef.current;
    let found: { mem: GalaxyMemory; x: number; y: number } | null = null;

    for (const mem of mems) {
      const x = (mem as GalaxyMemory & { _x?: number })._x;
      const y = (mem as GalaxyMemory & { _y?: number })._y;
      if (x === undefined || y === undefined) continue;
      const dx = mx - x;
      const dy = my - y;
      if (dx * dx + dy * dy < 100) {
        found = { mem, x: mx, y: my };
        break;
      }
    }

    hoverRef.current = found;
    setHovered(found);
    canvas.style.cursor = found ? "pointer" : "default";
  }, []);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hovered && onSelect) {
      onSelect(hovered.mem);
    }
  }, [hovered, onSelect]);

  return (
    <div ref={containerRef} className="relative w-full" style={{ height }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => {
          hoverRef.current = null;
          setHovered(null);
        }}
        onClick={handleClick}
        className="rounded-2xl border border-border"
        role="img"
        aria-label={`Galactic memory visualization showing ${memories.length} memories across 5 zones`}
      />
      {/* Zone legend overlay */}
      <div className="pointer-events-none absolute bottom-3 right-3 rounded-xl border border-border bg-black/70 p-3 backdrop-blur-sm">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-dim">
          Galactic Zones
        </div>
        <div className="space-y-1">
          {Object.entries(ZONES).map(([key, zone]) => {
            const count = memories.filter((m) => classifyZone(m.galactic_distance) === key).length;
            return (
              <div key={key} className="flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: zone.color }}
                />
                <span className="font-mono text-[10px]" style={{ color: zone.color }}>
                  {zone.label}
                </span>
                <span className="font-mono text-[10px] text-dim">
                  {count}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
