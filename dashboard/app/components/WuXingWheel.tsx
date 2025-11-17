'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface WuXingWheelProps {
  currentPhase: 'WOOD' | 'FIRE' | 'EARTH' | 'METAL' | 'WATER';
}

const phases = [
  { name: 'WOOD', label: '木 Planning', color: '#10b981', angle: 0 },
  { name: 'FIRE', label: '火 Execution', color: '#ef4444', angle: 72 },
  { name: 'EARTH', label: '土 Testing', color: '#f59e0b', angle: 144 },
  { name: 'METAL', label: '金 Refinement', color: '#6b7280', angle: 216 },
  { name: 'WATER', label: '水 Reflection', color: '#3b82f6', angle: 288 },
];

export default function WuXingWheel({ currentPhase }: WuXingWheelProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 400;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 40;
    const centerX = width / 2;
    const centerY = height / 2;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${centerX},${centerY})`);

    // Draw phase segments
    phases.forEach((phase, i) => {
      const angleRad = (phase.angle * Math.PI) / 180;
      const nextAngleRad = ((phases[(i + 1) % 5].angle) * Math.PI) / 180;

      // Create arc
      const arc = d3.arc()
        .innerRadius(radius * 0.5)
        .outerRadius(radius)
        .startAngle(angleRad - Math.PI / 10)
        .endAngle(angleRad + Math.PI / 10);

      // Draw segment
      g.append('path')
        .attr('d', arc as any)
        .attr('fill', phase.color)
        .attr('opacity', phase.name === currentPhase ? 1 : 0.3)
        .attr('stroke', '#1f2937')
        .attr('stroke-width', 2);

      // Add label
      const labelRadius = radius * 1.2;
      const labelX = labelRadius * Math.cos(angleRad - Math.PI / 2);
      const labelY = labelRadius * Math.sin(angleRad - Math.PI / 2);

      g.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('fill', phase.name === currentPhase ? phase.color : '#9ca3af')
        .attr('font-size', '14px')
        .attr('font-weight', phase.name === currentPhase ? 'bold' : 'normal')
        .text(phase.label);
    });

    // Center circle with current phase
    g.append('circle')
      .attr('r', radius * 0.4)
      .attr('fill', '#1f2937')
      .attr('stroke', phases.find(p => p.name === currentPhase)?.color)
      .attr('stroke-width', 4);

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('fill', '#fff')
      .attr('font-size', '20px')
      .attr('font-weight', 'bold')
      .text(currentPhase);

  }, [currentPhase]);

  return (
    <div className="flex items-center justify-center">
      <svg ref={svgRef}></svg>
    </div>
  );
}
