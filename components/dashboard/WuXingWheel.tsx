/**
 * Wu Xing Wheel — Five Elements Cognitive Phase Visualization
 *
 * Ported from whitemagic-aux/whitemagic-frontend/dashboard-app/WuXingWheel.tsx
 *
 * Displays the current Wu Xing (五行) elemental balance:
 * Wood (木) → Fire (火) → Earth (土) → Metal (金) → Water (水)
 *
 * Each element represents a cognitive phase:
 * - Wood: Growth, initiation, new ideas
 * - Fire: Radiance, execution, energy
 * - Earth: Stability, consolidation, grounding
 * - Metal: Harvest, refinement, precision
 * - Water: Storage, rest, reflection
 */

"use client";

import { useEffect, useRef, useState } from "react";

interface ElementPhase {
  name: string;
  chinese: string;
  color: string;
  angle: number;
  value: number;
  description: string;
}

const ELEMENTS: ElementPhase[] = [
  {
    name: "Wood",
    chinese: "木",
    color: "#22c55e",
    angle: 0,
    value: 0.2,
    description: "Growth & Initiation",
  },
  {
    name: "Fire",
    chinese: "火",
    color: "#ef4444",
    angle: 72,
    value: 0.2,
    description: "Radiance & Execution",
  },
  {
    name: "Earth",
    chinese: "土",
    color: "#eab308",
    angle: 144,
    value: 0.2,
    description: "Stability & Consolidation",
  },
  {
    name: "Metal",
    chinese: "金",
    color: "#a855f7",
    angle: 216,
    value: 0.2,
    description: "Harvest & Refinement",
  },
  {
    name: "Water",
    chinese: "水",
    color: "#3b82f6",
    angle: 288,
    value: 0.2,
    description: "Storage & Reflection",
  },
];

export function WuXingWheel({
  size = 300,
  elementValues,
  gardens,
}: {
  size?: number;
  elementValues?: number[];
  gardens?: Array<{ name: string; health: number; resonance: number; memory_count: number }>;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredElement, setHoveredElement] = useState<ElementPhase | null>(
    null
  );
  const [rotation, setRotation] = useState(0);

  // Calculate element values from garden data if provided
  const calculateElementValues = (): number[] => {
    if (!gardens || gardens.length === 0) {
      return [0.2, 0.2, 0.2, 0.2, 0.2]; // Default equal distribution
    }

    // Map gardens to Wu Xing elements based on their characteristics
    const totalMemories = gardens.reduce((sum, g) => sum + (g.memory_count || 0), 0);
    if (totalMemories === 0) return [0.2, 0.2, 0.2, 0.2, 0.2];

    // Wood: knowledge/research gardens (growth, learning)
    const wood = gardens
      .filter(g => g.name.includes("knowledge") || g.name.includes("research"))
      .reduce((sum, g) => sum + (g.memory_count || 0), 0) / totalMemories;

    // Fire: emotion/creative gardens (radiance, expression)
    const fire = gardens
      .filter(g => g.name.includes("emotion") || g.name.includes("creative"))
      .reduce((sum, g) => sum + (g.memory_count || 0), 0) / totalMemories;

    // Earth: core/wisdom gardens (stability, grounding)
    const earth = gardens
      .filter(g => g.name.includes("core") || g.name.includes("wisdom"))
      .reduce((sum, g) => sum + (g.memory_count || 0), 0) / totalMemories;

    // Metal: code/system gardens (precision, refinement)
    const metal = gardens
      .filter(g => g.name.includes("code") || g.name.includes("system"))
      .reduce((sum, g) => sum + (g.memory_count || 0), 0) / totalMemories;

    // Water: dream/ephemeral gardens (reflection, storage)
    const water = gardens
      .filter(g => g.name.includes("dream") || g.name.includes("ephemeral"))
      .reduce((sum, g) => sum + (g.memory_count || 0), 0) / totalMemories;

    return [
      Math.max(0.05, wood),
      Math.max(0.05, fire),
      Math.max(0.05, earth),
      Math.max(0.05, metal),
      Math.max(0.05, water),
    ];
  };

  const computedValues = elementValues || calculateElementValues();

  // Update element values if provided
  const elements = ELEMENTS.map((el, i) => ({
    ...el,
    value: computedValues[i] ?? el.value,
  }));

  // Animation loop
  useEffect(() => {
    let animationId: number;
    let lastTime = 0;

    const animate = (time: number) => {
      const delta = time - lastTime;
      lastTime = time;

      // Slow rotation
      setRotation((prev) => (prev + delta * 0.005) % 360);

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, []);

  // Draw wheel
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size / 2 - 20;

    // Clear
    ctx.clearRect(0, 0, size, size);

    // Draw background circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(124, 58, 237, 0.05)";
    ctx.fill();
    ctx.strokeStyle = "rgba(124, 58, 237, 0.2)";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Draw element segments
    elements.forEach((element, i) => {
      const startAngle =
        ((element.angle + rotation - 90) * Math.PI) / 180;
      const endAngle =
        ((element.angle + 72 + rotation - 90) * Math.PI) / 180;

      // Segment arc
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.closePath();

      // Fill with element color, alpha based on value
      const alpha = 0.1 + element.value * 0.4;
      ctx.fillStyle = element.color + Math.round(alpha * 255).toString(16).padStart(2, "0");
      ctx.fill();

      // Segment border
      ctx.strokeStyle = element.color + "80";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Element label
      const labelAngle =
        ((element.angle + 36 + rotation - 90) * Math.PI) / 180;
      const labelRadius = radius * 0.65;
      const labelX = centerX + Math.cos(labelAngle) * labelRadius;
      const labelY = centerY + Math.sin(labelAngle) * labelRadius;

      ctx.fillStyle = element.color;
      ctx.font = "bold 24px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(element.chinese, labelX, labelY);

      // Value bar
      const barRadius = radius * 0.85;
      const barX = centerX + Math.cos(labelAngle) * barRadius;
      const barY = centerY + Math.sin(labelAngle) * barRadius;
      const barWidth = 40;
      const barHeight = 4;

      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
      ctx.fillRect(barX - barWidth / 2, barY - barHeight / 2, barWidth, barHeight);

      ctx.fillStyle = element.color;
      ctx.fillRect(
        barX - barWidth / 2,
        barY - barHeight / 2,
        barWidth * element.value,
        barHeight
      );
    });

    // Center circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, 30, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(124, 58, 237, 0.3)";
    ctx.fill();
    ctx.strokeStyle = "rgba(124, 58, 237, 0.5)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Center text
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("五行", centerX, centerY);
  }, [elements, rotation, size]);

  return (
    <div className="relative flex flex-col items-center">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        className="cursor-pointer"
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const x = e.clientX - rect.left - size / 2;
          const y = e.clientY - rect.top - size / 2;
          const dist = Math.sqrt(x * x + y * y);

          if (dist < size / 2 - 20) {
            let angle =
              (Math.atan2(y, x) * 180) / Math.PI - rotation + 90;
            if (angle < 0) angle += 360;

            const elementIndex = Math.floor(angle / 72) % 5;
            setHoveredElement(elements[elementIndex]);
          } else {
            setHoveredElement(null);
          }
        }}
        onMouseLeave={() => setHoveredElement(null)}
      />

      {hoveredElement && (
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-black/80 backdrop-blur-sm rounded-lg border border-purple-500/30">
          <div className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: hoveredElement.color }}
            />
            <span className="text-sm font-medium text-white">
              {hoveredElement.name} ({hoveredElement.chinese})
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {hoveredElement.description}
          </p>
          <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${hoveredElement.value * 100}%`,
                backgroundColor: hoveredElement.color,
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
