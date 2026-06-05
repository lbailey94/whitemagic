/**
 * Live Galaxy Sphere — Real-time 5D Holographic Visualization
 *
 * Fetches live memory data from the WhiteMagic REST API and renders
 * a 3D galaxy with nodes positioned by 5D holographic coordinates (x,y,z,w,v)
 * projected to 3D space. Nodes are colored by galactic zone.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Sphere, Line } from "@react-three/drei";
import * as THREE from "three";

interface GalaxyNode {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  w: number;
  v: number;
  color: string;
  size: number;
  zone: string;
  importance: number;
  distance: number;
  access_count: number;
  content?: string;
}

interface GalaxyEdge {
  source: string;
  target: string;
  strength: number;
}

interface GalaxyData {
  nodes: GalaxyNode[];
  edges: GalaxyEdge[];
  total: number;
  has_coords: number;
}

const ZONE_COLORS: Record<string, string> = {
  core: "#fbbf24",
  active: "#22c55e",
  architecture: "#3b82f6",
  research: "#a855f7",
  outer_rim: "#6b7280",
};

function GalaxyNodePoint({
  node,
  onClick,
  onHover,
  isHovered,
  isSelected,
}: {
  node: GalaxyNode;
  onClick: (node: GalaxyNode) => void;
  onHover: (node: GalaxyNode | null) => void;
  isHovered: boolean;
  isSelected: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = isHovered || isSelected ? 1.5 : 1;
      meshRef.current.scale.setScalar(scale);
      // Gentle pulse animation
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2 + node.x * 10) * 0.05;
      meshRef.current.scale.setScalar(scale * pulse);
    }
  });

  return (
    <group position={[node.x * 2, node.y * 2, node.z * 2]}>
      <Sphere
        ref={meshRef}
        args={[node.size * 0.02, 8, 8]}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          onHover(node);
        }}
        onPointerOut={() => {
          setHovered(false);
          onHover(null);
        }}
        onClick={(e) => {
          e.stopPropagation();
          onClick(node);
        }}
      >
        <meshStandardMaterial
          color={new THREE.Color(node.color)}
          emissive={isHovered || isSelected ? node.color : "#000000"}
          emissiveIntensity={isHovered || isSelected ? 0.5 : 0.1}
          transparent
          opacity={0.85}
        />
      </Sphere>
      {isHovered && (
        <Text
          position={[0, node.size * 0.03, 0]}
          fontSize={0.06}
          color="white"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.005}
          outlineColor="#000000"
        >
          {node.label}
        </Text>
      )}
    </group>
  );
}

function GalaxyEdges({ edges, nodes }: { edges: GalaxyEdge[]; nodes: GalaxyNode[] }) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <>
      {edges.slice(0, 200).map((edge, i) => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) return null;
        return (
          <Line
            key={i}
            points={[
              [source.x * 2, source.y * 2, source.z * 2],
              [target.x * 2, target.y * 2, target.z * 2],
            ]}
            color={new THREE.Color(source.color)}
            lineWidth={1}
            transparent
            opacity={edge.strength * 0.3}
          />
        );
      })}
    </>
  );
}

function ZoneRings() {
  const rings = [
    { radius: 0.4, color: "#fbbf24", label: "Core" },
    { radius: 0.8, color: "#22c55e", label: "Active" },
    { radius: 1.2, color: "#3b82f6", label: "Architecture" },
    { radius: 1.6, color: "#a855f7", label: "Research" },
    { radius: 2.0, color: "#6b7280", label: "Outer Rim" },
  ];

  return (
    <>
      {rings.map((ring, i) => (
        <mesh key={i} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[ring.radius * 1.98, ring.radius * 2.02, 64]} />
          <meshBasicMaterial color={ring.color} transparent opacity={0.15} />
        </mesh>
      ))}
    </>
  );
}

function GalaxyScene({
  data,
  onNodeClick,
  onNodeHover,
  hoveredNode,
  selectedNode,
}: {
  data: GalaxyData;
  onNodeClick: (node: GalaxyNode) => void;
  onNodeHover: (node: GalaxyNode | null) => void;
  hoveredNode: GalaxyNode | null;
  selectedNode: GalaxyNode | null;
}) {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.3} color="#8b5cf6" />

      <ZoneRings />
      <GalaxyEdges edges={data.edges} nodes={data.nodes} />

      {data.nodes.map((node) => (
        <GalaxyNodePoint
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
        autoRotateSpeed={0.3}
        minDistance={1}
        maxDistance={8}
      />
    </>
  );
}

export function LiveGalaxySphere({
  apiUrl = "/api/wm",
  maxNodes = 500,
  height = 600,
}: {
  apiUrl?: string;
  maxNodes?: number;
  height?: number;
}) {
  const [data, setData] = useState<GalaxyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GalaxyNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GalaxyNode | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: maxNodes.toString(),
        include_content: "false",
      });
      if (zoneFilter) params.set("zone", zoneFilter);

      const res = await fetch(`${apiUrl}/galaxy/nodes?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load galaxy data");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, maxNodes, zoneFilter]);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="flex flex-col h-full" style={{ height }}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-purple-500/20">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="text-sm font-medium text-white">Live Galaxy (5D Holographic)</h3>
          {lastUpdated && (
            <span className="text-[10px] text-gray-500">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={zoneFilter}
            onChange={(e) => setZoneFilter(e.target.value)}
            className="text-xs bg-gray-800 text-gray-300 border border-gray-700 rounded px-2 py-1"
          >
            <option value="">All Zones</option>
            <option value="core">Core</option>
            <option value="active">Active</option>
            <option value="architecture">Architecture</option>
            <option value="research">Research</option>
            <option value="outer_rim">Outer Rim</option>
          </select>
          <button
            onClick={fetchData}
            className="px-2 py-1 text-xs bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 3D Scene */}
      <div className="flex-1 relative">
        {loading && !data && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
            <div className="text-gray-400 text-sm">Loading galaxy...</div>
          </div>
        )}
        {error && !data && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
            <div className="text-red-400 text-sm">{error}</div>
          </div>
        )}
        {data && (
          <Canvas camera={{ position: [3, 2, 3], fov: 60 }}>
            <GalaxyScene
              data={data}
              onNodeClick={setSelectedNode}
              onNodeHover={setHoveredNode}
              hoveredNode={hoveredNode}
              selectedNode={selectedNode}
            />
          </Canvas>
        )}
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div className="p-3 border-t border-purple-500/20 bg-black/30">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-white">{selectedNode.label}</p>
              <p className="text-xs text-gray-400 mt-1">
                Zone: <span style={{ color: ZONE_COLORS[selectedNode.zone] }}>{selectedNode.zone}</span>
                {" • "}Importance: {selectedNode.importance.toFixed(3)}
                {" • "}Accesses: {selectedNode.access_count}
              </p>
              {selectedNode.content && (
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{selectedNode.content}</p>
              )}
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-500 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Zone legend */}
      <div className="p-2 border-t border-purple-500/20">
        <div className="flex flex-wrap gap-3">
          {Object.entries(ZONE_COLORS).map(([zone, color]) => (
            <div key={zone} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-gray-400 capitalize">{zone}</span>
              {data && (
                <span className="text-[10px] text-gray-600">
                  ({data.nodes.filter((n) => n.zone === zone).length})
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
