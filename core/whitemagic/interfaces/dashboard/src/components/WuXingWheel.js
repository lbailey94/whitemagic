import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const phases = [
  { name: 'WOOD', label: '木 Planning', color: '#10b981', angle: 0 },
  { name: 'FIRE', label: '火 Execution', color: '#ef4444', angle: 72 },
  { name: 'EARTH', label: '土 Testing', color: '#f59e0b', angle: 144 },
  { name: 'METAL', label: '金 Refinement', color: '#6b7280', angle: 216 },
  { name: 'WATER', label: '水 Reflection', color: '#3b82f6', angle: 288 },
];

export default function WuXingWheel({ currentPhase }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 300;
    const height = 300;
    const radius = Math.min(width, height) / 2 - 30;
    const centerX = width / 2;
    const centerY = height / 2;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${centerX},${centerY})`);

    phases.forEach((phase, i) => {
      const angleRad = (phase.angle * Math.PI) / 180;
      
      const arc = d3.arc()
        .innerRadius(radius * 0.5)
        .outerRadius(radius)
        .startAngle(angleRad - Math.PI / 10)
        .endAngle(angleRad + Math.PI / 10);

      g.append('path')
        .attr('d', arc)
        .attr('fill', phase.color)
        .attr('opacity', phase.name === currentPhase ? 1 : 0.2)
        .attr('stroke', '#1f2937')
        .attr('stroke-width', 2);

      const labelRadius = radius * 1.25;
      const labelX = labelRadius * Math.cos(angleRad - Math.PI / 2);
      const labelY = labelRadius * Math.sin(angleRad - Math.PI / 2);

      g.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('fill', phase.name === currentPhase ? phase.color : '#6b7280')
        .attr('font-size', '10px')
        .attr('font-weight', phase.name === currentPhase ? 'bold' : 'normal')
        .text(phase.label);
    });

    g.append('circle')
      .attr('r', radius * 0.4)
      .attr('fill', 'rgba(255, 255, 255, 0.05)')
      .attr('stroke', phases.find(p => p.name === currentPhase)?.color || '#ccc')
      .attr('stroke-width', 2);

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('fill', '#374151')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .text(currentPhase || 'IDLE');

  }, [currentPhase]);

  return (
    <div className="flex items-center justify-center p-2">
      <svg ref={svgRef}></svg>
    </div>
  );
}
