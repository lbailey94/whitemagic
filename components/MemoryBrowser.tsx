/**
 * Memory Browser — 3D Galaxy Navigation
 *
 * Replaces the simple list view with an interactive 3D galaxy browser
 * where users navigate by zone/constellation. Clicking a node shows
 * memory details and related memories.
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Sphere } from "@react-three/drei";
import * as THREE from "three";

interface MemoryNode {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
  zone: string;
  importance: number;
  distance: number;
  access_count: number;
  content?: string;
  memory_type?: string;
  created_at?: string;
}

interface MemoryEdge {
  source: string;
  target: string;
  strength: number;
}

const ZONE_COLORS: Record<string, string> = {
  core: "#fbbf24",
  active: "#22c55e",
  architecture: "#3b82f6",
  research: "#a855f7",
  outer_rim: "#6b7280",
  tutorial: "#ec4899",
};

function MemoryNodePoint({
  node,
  onClick,
  onHover,
  isHovered,
  isSelected,
}: {
  node: MemoryNode;
  onClick: (node: MemoryNode) => void;
  onHover: (node: MemoryNode | null) => void;
  isHovered: boolean;
  isSelected: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = isHovered || isSelected ? 1.8 : 1;
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2 + node.x * 10) * 0.05;
      meshRef.current.scale.setScalar(scale * pulse);
    }
  });

  return (
    <group position={[node.x * 2.5, node.y * 2.5, node.z * 2.5]}>
      <Sphere
        ref={meshRef}
        args={[node.size * 0.015, 8, 8]}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(node);
        }}
        onPointerOut={() => onHover(null)}
        onClick={(e) => {
          e.stopPropagation();
          onClick(node);
        }}
      >
        <meshStandardMaterial
          color={new THREE.Color(node.color)}
          emissive={isHovered || isSelected ? node.color : "#000000"}
          emissiveIntensity={isHovered || isSelected ? 0.6 : 0.1}
          transparent
          opacity={0.85}
        />
      </Sphere>
      {(isHovered || isSelected) && (
        <Text
          position={[0, node.size * 0.02, 0]}
          fontSize={0.05}
          color="white"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.004}
          outlineColor="#000000"
        >
          {node.label}
        </Text>
      )}
    </group>
  );
}

function MemoryEdges({ edges, nodes }: { edges: MemoryEdge[]; nodes: MemoryNode[] }) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <>
      {edges.slice(0, 150).map((edge, i) => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) return null;
        return (
          <line key={i}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[new Float32Array([
                  source.x * 2.5, source.y * 2.5, source.z * 2.5,
                  target.x * 2.5, target.y * 2.5, target.z * 2.5,
                ]), 3]}
                count={2}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial
              color={new THREE.Color(source.color)}
              transparent
              opacity={edge.strength * 0.25}
            />
          </line>
        );
      })}
    </>
  );
}

function ZoneLabels({ zones }: { zones: string[] }) {
  const zonePositions: Record<string, [number, number, number]> = {
    core: [0, 0.3, 0],
    active: [0.6, 0, 0],
    architecture: [-0.6, 0, 0.4],
    research: [0, -0.6, -0.4],
    outer_rim: [0, 0, -0.8],
    tutorial: [0.4, 0.4, 0.4],
  };

  return (
    <>
      {zones.map((zone) => {
        const pos = zonePositions[zone] || [0, 0, 0];
        return (
          <Text
            key={zone}
            position={pos}
            fontSize={0.08}
            color={ZONE_COLORS[zone] || "#6b7280"}
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.005}
            outlineColor="#000000"
          >
            {zone.toUpperCase()}
          </Text>
        );
      })}
    </>
  );
}

function GalaxyScene({
  nodes,
  edges,
  zones,
  onNodeClick,
  onNodeHover,
  hoveredNode,
  selectedNode,
}: {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  zones: string[];
  onNodeClick: (node: MemoryNode) => void;
  onNodeHover: (node: MemoryNode | null) => void;
  hoveredNode: MemoryNode | null;
  selectedNode: MemoryNode | null;
}) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={1} />
      <pointLight position={[-5, -5, -5]} intensity={0.3} color="#8b5cf6" />

      <ZoneLabels zones={zones} />
      <MemoryEdges edges={edges} nodes={nodes} />

      {nodes.map((node) => (
        <MemoryNodePoint
          key={node.id}
          node={node}
          onClick={onNodeClick}
          onHover={onNodeHover}
          isHovered={hoveredNode?.id === node.id}
          isSelected={selectedNode?.id === node.id}
        />
      ))}

      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        autoRotate
        autoRotateSpeed={0.2}
        minDistance={1}
        maxDistance={10}
      />
    </>
  );
}

export function MemoryBrowser({
  apiUrl = "/api/wm",
  height = 500,
}: {
  apiUrl?: string;
  height?: number;
}) {
  const [nodes, setNodes] = useState<MemoryNode[]>([]);
  const [edges, setEdges] = useState<MemoryEdge[]>([]);
  const [zones, setZones] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: "200",
        include_coords: "true",
      });
      if (searchQuery) params.set("q", searchQuery);

      const res = await fetch(`${apiUrl}/memories?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Transform to galaxy nodes
      const transformedNodes: MemoryNode[] = data.memories.map((m: any) => {
        const dist = m.galactic_distance || 0.5;
        let zone = "outer_rim";
        if (dist < 0.2) zone = "core";
        else if (dist < 0.4) zone = "active";
        else if (dist < 0.6) zone = "architecture";
        else if (dist < 0.8) zone = "research";

        // Use coords if available
        const x = m.coords?.x ?? (Math.random() - 0.5) * 2 * dist;
        const y = m.coords?.y ?? (Math.random() - 0.5) * 2 * dist;
        const z = m.coords?.z ?? (Math.random() - 0.5) * 2 * dist;

        return {
          id: m.id,
          label: (m.title || m.id.slice(0, 12)) as string,
          x,
          y,
          z,
          color: ZONE_COLORS[zone] || "#6b7280",
          size: Math.max(2, Math.min(12, (m.importance || 0.5) * 12)),
          zone,
          importance: m.importance || 0.5,
          distance: dist,
          access_count: m.access_count || 0,
          content: m.content,
          memory_type: m.memory_type,
          created_at: m.created_at,
        };
      });

      // Filter by zone
      const filtered = zoneFilter
        ? transformedNodes.filter((n) => n.zone === zoneFilter)
        : transformedNodes;

      // Compute edges for filtered nodes
      const computedEdges: MemoryEdge[] = [];
      const limit = Math.min(filtered.length, 80);
      for (let i = 0; i < limit; i++) {
        const ni = filtered[i];
        const neighbors: [number, number][] = [];
        for (let j = 0; j < filtered.length; j++) {
          if (i === j) continue;
          const nj = filtered[j];
          const d = Math.sqrt(
            (ni.x - nj.x) ** 2 + (ni.y - nj.y) ** 2 + (ni.z - nj.z) ** 2
          );
          neighbors.push([j, d]);
        }
        neighbors.sort((a, b) => a[1] - b[1]);
        for (const [j, d] of neighbors.slice(0, 3)) {
          const strength = Math.max(0, 1 - d / 2);
          if (strength > 0.3) {
            computedEdges.push({
              source: ni.id,
              target: filtered[j].id,
              strength: Math.round(strength * 1000) / 1000,
            });
          }
        }
      }

      setNodes(filtered);
      setEdges(computedEdges);
      setZones([...new Set(filtered.map((n) => n.zone))]);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load memories");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, zoneFilter, searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="flex flex-col h-full" style={{ height }}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-purple-500/20">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="text-sm font-medium text-white">Memory Browser (3D Galaxy)</h3>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="text-xs bg-gray-800 text-gray-300 border border-gray-700 rounded px-2 py-1 w-32"
          />
          <select
            value={zoneFilter}
            onChange={(e) => setZoneFilter(e.target.value)}
            className="text-xs bg-gray-800 text-gray-300 border border-gray-700 rounded px-2 py-1"
          >
            <option value="">All Zones</option>
            {Object.keys(ZONE_COLORS).map((z) => (
              <option key={z} value={z}>{z.charAt(0).toUpperCase() + z.slice(1)}</option>
            ))}
          </select>
          <button
            onClick={fetchData}
            className="px-2 py-1 text-xs bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 3D Scene + Detail Panel */}
      <div className="flex-1 flex">
        {/* 3D Galaxy */}
        <div className="flex-1 relative">
          {loading && !nodes.length && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
              <div className="text-gray-400 text-sm">Loading memories...</div>
            </div>
          )}
          {error && !nodes.length && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
              <div className="text-red-400 text-sm">{error}</div>
            </div>
          )}
          {nodes.length > 0 && (
            <Canvas camera={{ position: [4, 3, 4], fov: 60 }}>
              <GalaxyScene
                nodes={nodes}
                edges={edges}
                zones={zones}
                onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode}
                hoveredNode={hoveredNode}
                selectedNode={selectedNode}
              />
            </Canvas>
          )}
        </div>

        {/* Detail Panel */}
        {selectedNode && (
          <div className="w-64 border-l border-purple-500/20 bg-black/30 p-3 overflow-y-auto">
            <div className="flex items-start justify-between mb-3">
              <h4 className="text-sm font-medium text-white">{selectedNode.label}</h4>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-500 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-gray-500">Zone:</span>
                <span
                  className="ml-1 font-medium"
                  style={{ color: ZONE_COLORS[selectedNode.zone] }}
                >
                  {selectedNode.zone}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Importance:</span>
                <span className="ml-1 text-white">{selectedNode.importance.toFixed(3)}</span>
              </div>
              <div>
                <span className="text-gray-500">Distance:</span>
                <span className="ml-1 text-white">{selectedNode.distance.toFixed(3)}</span>
              </div>
              <div>
                <span className="text-gray-500">Accesses:</span>
                <span className="ml-1 text-white">{selectedNode.access_count}</span>
              </div>
              {selectedNode.created_at && (
                <div>
                  <span className="text-gray-500">Created:</span>
                  <span className="ml-1 text-white">{selectedNode.created_at.slice(0, 10)}</span>
                </div>
              )}
              {selectedNode.content && (
                <div className="pt-2 border-t border-gray-700">
                  <p className="text-gray-400 line-clamp-6">{selectedNode.content}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Stats bar */}
      <div className="p-2 border-t border-purple-500/20 flex items-center justify-between text-[10px] text-gray-500">
        <span>{nodes.length} memories</span>
        <span>{edges.length} connections</span>
        <span>{zones.length} zones</span>
        {hoveredNode && <span>Hover: {hoveredNode.label}</span>}
      </div>
    </div>
  );
}
