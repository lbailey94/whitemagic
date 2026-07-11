/**
 * Memory Graph — D3.js Force-Directed Graph Visualization
 *
 * Ported from whitemagic-aux/whitemagic-frontend/dashboard-app/MemoryGraph.tsx
 *
 * Displays memories as nodes and associations as edges in a force-directed graph.
 * - Node size = memory importance
 * - Node color = memory type / galactic band
 * - Edge thickness = association strength
 * - Interactive: hover for details, click to select, drag to rearrange
 */

"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { useDashboardStore, type Memory } from "@/store/dashboardStore";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  title: string;
  importance: number;
  memory_type: string;
  galactic_distance: number;
  x?: number;
  y?: number;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  strength: number;
  association_type: string;
}

// Color scale based on galactic distance
function getNodeColor(galacticDistance: number): string {
  if (galacticDistance === 0) return "#a855f7"; // Core (purple)
  if (galacticDistance <= 0.3) return "#22c55e"; // Active (green)
  if (galacticDistance <= 0.4) return "#3b82f6"; // Architecture (blue)
  if (galacticDistance <= 0.5) return "#eab308"; // Research (yellow)
  if (galacticDistance <= 0.7) return "#f97316"; // Mid-range (orange)
  return "#ef4444"; // Outer rim (red)
}

export function MemoryGraph({
  width = 800,
  height = 600,
  maxNodes = 100,
  maxEdges = 200,
}: {
  width?: number;
  height?: number;
  maxNodes?: number;
  maxEdges?: number;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { memories, selectMemory, selectedMemory } = useDashboardStore();
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(
    null
  );

  // Build graph from memories and associations
  useEffect(() => {
    if (!svgRef.current || memories.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Limit nodes for performance
    const limitedMemories = memories.slice(0, maxNodes);

    // Create nodes
    const nodes: GraphNode[] = limitedMemories.map((mem) => ({
      id: mem.id,
      title: mem.title || mem.id.slice(0, 20),
      importance: mem.importance,
      memory_type: mem.memory_type,
      galactic_distance: mem.galactic_distance,
    }));

    // Create mock edges (in real app, fetch from associations API)
    const edges: GraphLink[] = [];
    for (let i = 0; i < Math.min(nodes.length * 2, maxEdges); i++) {
      const source = Math.floor(Math.random() * nodes.length);
      let target = Math.floor(Math.random() * nodes.length);
      while (target === source) {
        target = Math.floor(Math.random() * nodes.length);
      }
      edges.push({
        source: nodes[source].id,
        target: nodes[target].id,
        strength: Math.random() * 0.5 + 0.3,
        association_type: "semantic_overlap",
      });
    }

    // Create force simulation
    const simulation = d3
      .forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>(edges)
          .id((d) => d.id)
          .distance(80)
          .strength((d) => d.strength * 0.5)
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(20))
      .force("x", d3.forceX(width / 2).strength(0.1))
      .force("y", d3.forceY(height / 2).strength(0.1));

    simulationRef.current = simulation;

    // Create groups
    const g = svg.append("g");

    // Zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#6b7280")
      .attr("stroke-opacity", 0.3)
      .attr("stroke-width", (d) => d.strength * 3);

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => 5 + d.importance * 15)
      .attr("fill", (d) => getNodeColor(d.galactic_distance))
      .attr("stroke", "#1e1e2e")
      .attr("stroke-width", 2)
      .attr("cursor", "pointer")
      .call(
        (d3.drag<SVGCircleElement, GraphNode>() as any)
          .on("start", (event: any, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("drag", (event: any, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event: any, d: any) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on("mouseover", (event, d) => {
        setHoveredNode(d);
        d3.select(event.currentTarget)
          .transition()
          .duration(200)
          .attr("r", 5 + d.importance * 15 + 5)
          .attr("stroke", "#ffffff");
      })
      .on("mouseout", (event, d) => {
        setHoveredNode(null);
        d3.select(event.currentTarget)
          .transition()
          .duration(200)
          .attr("r", 5 + d.importance * 15)
          .attr("stroke", "#1e1e2e");
      })
      .on("click", (event, d) => {
        const memory = memories.find((m) => m.id === d.id);
        if (memory) selectMemory(memory);
      });

    // Node labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => (d.title.length > 20 ? d.title.slice(0, 20) + "..." : d.title))
      .attr("font-size", "10px")
      .attr("fill", "#e2e8f0")
      .attr("text-anchor", "middle")
      .attr("dy", (d) => 5 + d.importance * 15 + 12)
      .attr("pointer-events", "none")
      .attr("opacity", 0.7);

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      node
        .attr("cx", (d) => d.x ?? 0)
        .attr("cy", (d) => d.y ?? 0);

      label
        .attr("x", (d) => d.x ?? 0)
        .attr("y", (d) => d.y ?? 0);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [memories, width, height, maxNodes, maxEdges, selectMemory]);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-black/20 rounded-lg border border-purple-500/20"
      />

      {/* Simulated connections notice */}
      <div className="absolute top-2 right-2 px-2 py-1 bg-black/60 backdrop-blur-sm rounded border border-purple-500/20">
        <span className="text-[10px] text-gray-400">Connections simulated · Real nodes</span>
      </div>

      {/* Hover tooltip */}
      {hoveredNode && (
        <div className="absolute top-2 left-2 p-3 bg-black/80 backdrop-blur-sm rounded-lg border border-purple-500/30 max-w-xs">
          <p className="text-sm font-medium text-white truncate">
            {hoveredNode.title}
          </p>
          <div className="mt-1 space-y-0.5 text-xs text-gray-400">
            <p>
              Importance:{" "}
              <span className="text-white">{hoveredNode.importance.toFixed(2)}</span>
            </p>
            <p>
              Type: <span className="text-white">{hoveredNode.memory_type}</span>
            </p>
            <p>
              Distance:{" "}
              <span className="text-white">
                {hoveredNode.galactic_distance.toFixed(2)}
              </span>
            </p>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-2 right-2 p-2 bg-black/60 backdrop-blur-sm rounded-lg border border-purple-500/20">
        <div className="text-[10px] text-gray-400 mb-1">Galactic Bands</div>
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-purple-500" />
            <span className="text-[10px] text-gray-400">Core (0.0)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-[10px] text-gray-400">Active (0.1-0.3)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-[10px] text-gray-400">Architecture (0.3-0.4)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-[10px] text-gray-400">Research (0.4-0.5)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-[10px] text-gray-400">Outer Rim (0.7+)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
