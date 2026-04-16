import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function PolyglotBalance({ data }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current || !data) return;

    const width = 300;
    const height = 300;
    const radius = Math.min(width, height) / 2;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    const color = d3.scaleOrdinal()
      .domain(Object.keys(data))
      .range(['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#6366f1']);

    const pie = d3.pie()
      .value(d => d[1]);

    const data_ready = pie(Object.entries(data));

    const arc = d3.arc()
      .innerRadius(radius * 0.5)
      .outerRadius(radius * 0.8);

    svg.selectAll('pieces')
      .data(data_ready)
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', d => color(d.data[0]))
      .attr('stroke', 'white')
      .style('stroke-width', '2px')
      .style('opacity', 0.7);

    svg.selectAll('labels')
      .data(data_ready)
      .enter()
      .append('text')
      .text(d => d.data[0])
      .attr('transform', d => `translate(${arc.centroid(d)})`)
      .style('text-anchor', 'middle')
      .style('font-size', '10px')
      .style('fill', '#374151')
      .style('font-weight', 'bold');

    svg.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .style('fill', '#6b7280')
      .text('Lichen Balance');

  }, [data]);

  return (
    <div className="flex items-center justify-center p-2">
      <svg ref={svgRef}></svg>
    </div>
  );
}
