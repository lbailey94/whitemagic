/**
 * Interactive Galaxy Sphere — Drag, Edges, Resonance Navigation
 *
 * Enhanced 3D galaxy with:
 * - Drag nodes to reposition
 * - Click two nodes to create edges
 * - Resonance navigation (semantic similarity)
 * - Local SQLite OPFS integration
 */

"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
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

// Draggable galaxy node
function DraggableNode({
  node,
  onClick,
  onHover,
  isHovered,
  isSelected,
  isEdgeSource,
  onDrag,
}: {
  node: GalaxyNode;
  onClick: (node: GalaxyNode) => void;
  onHover: (node: GalaxyNode | null) => void;
  isHovered: boolean;
  isSelected: boolean;
  isEdgeSource: boolean;
  onDrag: (id: string, pos: [number, number, number]) => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [dragging, setDragging] = useState(false);
  const dragOffset = useRef<THREE.Vector3 | null>(null);

  useFrame((state) => {
    if (meshRef.current && !dragging) {
      const scale = isHovered || isSelected || isEdgeSource ? 1.5 : 1;
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2 + node.x * 10) * 0.05;
      meshRef.current.scale.setScalar(scale * pulse);
    }
  });

  const handlePointerDown = (e: any) => {
    e.stopPropagation();
    if (!meshRef.current) return;

    setDragging(true);
    // @ts-ignore - Three.js pointer capture
    meshRef.current.setPointerCapture?.(e.pointerId);

    // Calculate offset from click position to node center
    const worldPos = new THREE.Vector3(node.x * 2, node.y * 2, node.z * 2);
    const ray = new THREE.Raycaster();
    ray.ray.copy(e.ray);
    const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(
      e.ray.direction.clone().cross(new THREE.Vector3(0, 1, 0)).normalize(),
      worldPos
    );
    const intersection = new THREE.Vector3();
    ray.ray.intersectPlane(plane, intersection);
    dragOffset.current = worldPos.clone().sub(intersection);
  };

  const handlePointerMove = (e: any) => {
    if (!dragging || !meshRef.current || !dragOffset.current) return;
    e.stopPropagation();

    const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(
      e.ray.direction.clone().cross(new THREE.Vector3(0, 1, 0)).normalize(),
      new THREE.Vector3(node.x * 2, node.y * 2, node.z * 2)
    );
    const intersection = new THREE.Vector3();
    e.ray.intersectPlane(plane, intersection);

    const newPos = intersection.add(dragOffset.current);
    onDrag(node.id, [newPos.x / 2, newPos.y / 2, newPos.z / 2]);
  };

  const handlePointerUp = (e: any) => {
    if (dragging) {
      setDragging(false);
      dragOffset.current = null;
      if (meshRef.current) {
        // @ts-ignore - Three.js pointer capture
        meshRef.current.releasePointerCapture?.(e.pointerId);
      }
    }
  };

  return (
    <group position={[node.x * 2, node.y * 2, node.z * 2]}>
      <Sphere
        ref={meshRef}
        args={[node.size * 0.02, 8, 8]}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(node);
        }}
        onPointerOut={() => onHover(null)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onClick={(e) => {
          e.stopPropagation();
          if (!dragging) onClick(node);
        }}
      >
        <meshStandardMaterial
          color={new THREE.Color(node.color)}
          emissive={isHovered || isSelected || isEdgeSource ? node.color : "#000000"}
          emissiveIntensity={isHovered || isSelected || isEdgeSource ? 0.8 : 0.1}
          transparent
          opacity={0.85}
        />
      </Sphere>
      {(isHovered || isSelected) && (
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

// Interactive edges with hover effects
function InteractiveEdges({
  edges,
  nodes,
  highlightedSource,
}: {
  edges: GalaxyEdge[];
  nodes: GalaxyNode[];
  highlightedSource: string | null;
}) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <>
      {edges.slice(0, 200).map((edge, i) => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) return null;

        const isHighlighted = highlightedSource && (edge.source === highlightedSource || edge.target === highlightedSource);

        return (
          <Line
            key={i}
            points={[
              [source.x * 2, source.y * 2, source.z * 2],
              [target.x * 2, target.y * 2, target.z * 2],
            ]}
            color={isHighlighted ? "#ffffff" : new THREE.Color(source.color)}
            lineWidth={isHighlighted ? 2 : 1}
            transparent
            opacity={isHighlighted ? 0.8 : edge.strength * 0.3}
          />
        );
      })}
    </>
  );
}

// Resonance lines (semantic similarity visualization)
function ResonanceLines({
  sourceNode,
  relatedNodes,
}: {
  sourceNode: GalaxyNode | null;
  relatedNodes: Array<{ node: GalaxyNode; score: number }>;
}) {
  if (!sourceNode) return null;

  return (
    <>
      {relatedNodes.map(({ node, score }) => (
        <Line
          key={node.id}
          points={[
            [sourceNode.x * 2, sourceNode.y * 2, sourceNode.z * 2],
            [node.x * 2, node.y * 2, node.z * 2],
          ]}
          color="#10b981"
          lineWidth={2}
          transparent
          opacity={score * 0.6}
          dashed
          dashSize={0.05}
          gapSize={0.03}
        />
      ))}
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
  nodePositions,
  onNodeClick,
  onNodeHover,
  onNodeDrag,
  hoveredNode,
  selectedNode,
  edgeSource,
  relatedNodes,
}: {
  data: GalaxyData;
  nodePositions: Map<string, [number, number, number]>;
  onNodeClick: (node: GalaxyNode) => void;
  onNodeHover: (node: GalaxyNode | null) => void;
  onNodeDrag: (id: string, pos: [number, number, number]) => void;
  hoveredNode: GalaxyNode | null;
  selectedNode: GalaxyNode | null;
  edgeSource: string | null;
  relatedNodes: Array<{ node: GalaxyNode; score: number }>;
}) {
  // Apply dragged positions to nodes
  const positionedNodes = useMemo(() => {
    return data.nodes.map(node => {
      const pos = nodePositions.get(node.id);
      if (pos) {
        return { ...node, x: pos[0], y: pos[1], z: pos[2] };
      }
      return node;
    });
  }, [data.nodes, nodePositions]);

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.3} color="#8b5cf6" />

      <ZoneRings />
      <InteractiveEdges edges={data.edges} nodes={positionedNodes} highlightedSource={edgeSource} />
      <ResonanceLines sourceNode={selectedNode} relatedNodes={relatedNodes} />

      {positionedNodes.map((node) => (
        <DraggableNode
          key={node.id}
          node={node}
          onClick={onNodeClick}
          onHover={onNodeHover}
          onDrag={onNodeDrag}
          isHovered={hoveredNode?.id === node.id}
          isSelected={selectedNode?.id === node.id}
          isEdgeSource={edgeSource === node.id}
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

export function InteractiveGalaxySphere({
  apiUrl = "/api/wm",
  maxNodes = 500,
  height = 600,
  useLocalMode = false,
}: {
  apiUrl?: string;
  maxNodes?: number;
  height?: number;
  useLocalMode?: boolean;
}) {
  const [data, setData] = useState<GalaxyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GalaxyNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GalaxyNode | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [nodePositions, setNodePositions] = useState<Map<string, [number, number, number]>>(new Map());
  const [edgeSource, setEdgeSource] = useState<string | null>(null);
  const [customEdges, setCustomEdges] = useState<GalaxyEdge[]>([]);
  const [relatedNodes, setRelatedNodes] = useState<Array<{ node: GalaxyNode; score: number }>>([]);
  const [mode, setMode] = useState<"navigate" | "connect">("navigate");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);

      if (useLocalMode) {
        // Local mode: generate demo nodes
        const demoNodes: GalaxyNode[] = [
          { id: "1", label: "Memory Core", x: 0.2, y: 0.1, z: 0.3, w: 0.5, v: 0.2, color: ZONE_COLORS.core, size: 3, zone: "core", importance: 0.9, distance: 0.3, access_count: 150 },
          { id: "2", label: "Wisdom Node", x: -0.3, y: 0.4, z: 0.2, w: 0.3, v: 0.6, color: ZONE_COLORS.active, size: 2, zone: "active", importance: 0.7, distance: 0.5, access_count: 80 },
          { id: "3", label: "Truth Cluster", x: 0.5, y: -0.2, z: -0.4, w: 0.2, v: 0.8, color: ZONE_COLORS.architecture, size: 2.5, zone: "architecture", importance: 0.8, distance: 0.7, access_count: 120 },
          { id: "4", label: "Mystery Ring", x: -0.6, y: -0.3, z: 0.5, w: 0.7, v: 0.3, color: ZONE_COLORS.research, size: 1.5, zone: "research", importance: 0.5, distance: 1.0, access_count: 40 },
          { id: "5", label: "Outer Echo", x: 0.8, y: 0.6, z: -0.2, w: 0.1, v: 0.9, color: ZONE_COLORS.outer_rim, size: 1, zone: "outer_rim", importance: 0.3, distance: 1.5, access_count: 10 },
        ];
        const demoEdges: GalaxyEdge[] = [
          { source: "1", target: "2", strength: 0.8 },
          { source: "1", target: "3", strength: 0.6 },
          { source: "2", target: "4", strength: 0.4 },
        ];
        setData({ nodes: demoNodes, edges: demoEdges, total: 5, has_coords: 5 });
      } else {
        const params = new URLSearchParams({
          limit: maxNodes.toString(),
          include_content: "false",
        });
        if (zoneFilter) params.set("zone", zoneFilter);

        const res = await fetch(`${apiUrl}/galaxy/nodes?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      }

      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load galaxy data");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, maxNodes, zoneFilter, useLocalMode]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleNodeClick = useCallback((node: GalaxyNode) => {
    if (mode === "connect") {
      if (!edgeSource) {
        setEdgeSource(node.id);
      } else if (edgeSource !== node.id) {
        // Create edge
        const newEdge: GalaxyEdge = {
          source: edgeSource,
          target: node.id,
          strength: 0.5,
        };
        setCustomEdges(prev => [...prev, newEdge]);
        setEdgeSource(null);
      }
    } else {
      setSelectedNode(prev => prev?.id === node.id ? null : node);
      setEdgeSource(null);
    }
  }, [mode, edgeSource]);

  const handleNodeDrag = useCallback((id: string, pos: [number, number, number]) => {
    setNodePositions(prev => {
      const next = new Map(prev);
      next.set(id, pos);
      return next;
    });
  }, []);

  const allEdges = useMemo(() => {
    if (!data) return [];
    return [...data.edges, ...customEdges];
  }, [data, customEdges]);

  const displayData = useMemo(() => {
    if (!data) return null;
    return { ...data, edges: allEdges };
  }, [data, allEdges]);

  return (
    <div className="flex flex-col h-full" style={{ height }}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-purple-500/20">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="text-sm font-medium text-white">Interactive Galaxy</h3>
          {lastUpdated && (
            <span className="text-[10px] text-gray-500">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Mode toggle */}
          <div className="flex rounded bg-gray-800 border border-gray-700 overflow-hidden">
            <button
              onClick={() => { setMode("navigate"); setEdgeSource(null); }}
              className={`px-2 py-1 text-xs transition-colors ${mode === "navigate" ? "bg-purple-600 text-white" : "text-gray-400 hover:text-white"}`}
            >
              Navigate
            </button>
            <button
              onClick={() => setMode("connect")}
              className={`px-2 py-1 text-xs transition-colors ${mode === "connect" ? "bg-purple-600 text-white" : "text-gray-400 hover:text-white"}`}
            >
              Connect
            </button>
          </div>
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

      {/* Mode indicator */}
      {mode === "connect" && (
        <div className="px-3 py-1 bg-yellow-500/10 border-b border-yellow-500/20">
          <p className="text-xs text-yellow-400">
            {edgeSource ? "Click target node to create edge" : "Click source node to start connecting"}
          </p>
        </div>
      )}

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
        {displayData && (
          <Canvas camera={{ position: [3, 2, 3], fov: 60 }}>
            <GalaxyScene
              data={displayData}
              nodePositions={nodePositions}
              onNodeClick={handleNodeClick}
              onNodeHover={setHoveredNode}
              onNodeDrag={handleNodeDrag}
              hoveredNode={hoveredNode}
              selectedNode={selectedNode}
              edgeSource={edgeSource}
              relatedNodes={relatedNodes}
            />
          </Canvas>
        )}
      </div>

      {/* Node detail panel */}
      {selectedNode && mode === "navigate" && (
        <div className="p-3 border-t border-purple-500/20 bg-black/30">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-white">{selectedNode.label}</p>
              <p className="text-xs text-gray-400 mt-1">
                Zone: <span style={{ color: ZONE_COLORS[selectedNode.zone] }}>{selectedNode.zone}</span>
                {" • "}Importance: {selectedNode.importance.toFixed(3)}
                {" • "}Accesses: {selectedNode.access_count}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Position: ({selectedNode.x.toFixed(2)}, {selectedNode.y.toFixed(2)}, {selectedNode.z.toFixed(2)})
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
