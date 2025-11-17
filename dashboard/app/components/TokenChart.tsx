'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface TokenData {
  timestamp: string;
  used: number;
  total: number;
}

export default function TokenChart({ data }: { data: TokenData[] }) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.length) return;

    const width = 400;
    const height = 250;
    const margin = { top: 20, right: 20, bottom: 30, left: 50 };

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const x = d3.scaleLinear()
      .domain([0, data.length - 1])
      .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
      .domain([0, 100])
      .range([height - margin.bottom, margin.top]);

    // Line generator
    const line = d3.line<TokenData>()
      .x((d, i) => x(i))
      .y(d => y((d.used / d.total) * 100));

    // Draw line
    svg.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#3b82f6')
      .attr('stroke-width', 2)
      .attr('d', line);

    // Add threshold lines
    [70, 50].forEach(threshold => {
      svg.append('line')
        .attr('x1', margin.left)
        .attr('x2', width - margin.right)
        .attr('y1', y(threshold))
        .attr('y2', y(threshold))
        .attr('stroke', threshold === 70 ? '#ef4444' : '#10b981')
        .attr('stroke-dasharray', '5,5')
        .attr('opacity', 0.5);
    });

    // Axes
    svg.append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(5))
      .attr('color', '#9ca3af');

    svg.append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d}%`))
      .attr('color', '#9ca3af');

  }, [data]);

  return (
    <div className="flex flex-col items-center">
      <svg ref={svgRef}></svg>
      <div className="mt-4 text-sm text-gray-400">
        <span className="inline-block w-3 h-3 bg-green-500 mr-2"></span>Safe (&lt;50%)
        <span className="inline-block w-3 h-3 bg-red-500 ml-4 mr-2"></span>Caution (&gt;70%)
      </div>
    </div>
  );
}
