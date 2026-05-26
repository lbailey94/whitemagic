"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sphere, Line } from "@react-three/drei";
import * as THREE from "three";

interface SphereNode {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
  source: string;
  token_count: number;
  links: Array<{
    target: string;
    similarity: number;
    rank: number;
  }>;
}

interface SphereData {
  version: string;
  nodes: SphereNode[];
}

interface NodeContent {
  id: string;
  label: string;
  source: string;
  token_count: number;
  content_preview: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

const SOURCE_COLORS: Record<string, string> = {
  library: "#60a5fa",
  conversations: "#4ade80",
  research: "#fb923c",
};

// Seeded hash for deterministic downsampling (simple FNV-1a variant)
function hashId(id: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function NodePoint({
  node,
  onClick,
  onHover,
  isHovered,
  isSelected,
}: {
  node: SphereNode;
  onClick: (id: string) => void;
  onHover: (id: string | null) => void;
  isHovered: boolean;
  isSelected: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(
    () => new THREE.Vector3(node.x, node.y, node.z),
    [node.x, node.y, node.z],
  );

  useFrame(() => {
    if (meshRef.current) {
      const target = isSelected ? 2.5 : isHovered ? 2 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(target, target, target), 0.1);
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={pos}
      onClick={(e) => {
        e.stopPropagation();
        onClick(node.id);
      }}
      onPointerEnter={(e) => {
        e.stopPropagation();
        onHover(node.id);
      }}
      onPointerLeave={() => onHover(null)}
    >
      <sphereGeometry args={[node.size * 0.015, 16, 16]} />
      <meshBasicMaterial color={node.color} />
    </mesh>
  );
}

function SimilarityEdges({
  hoveredId,
  selectedId,
  nodeMap,
}: {
  hoveredId: string | null;
  selectedId: string | null;
  nodeMap: Map<string, SphereNode>;
}) {
  const activeId = selectedId || hoveredId;
  if (!activeId) return null;
  const source = nodeMap.get(activeId);
  if (!source) return null;

  return (
    <group>
      {source.links.slice(0, 8).map((link) => {
        const target = nodeMap.get(link.target);
        if (!target) return null;
        return (
          <Line
            key={link.target}
            points={[
              [source.x, source.y, source.z],
              [target.x, target.y, target.z],
            ]}
            color={selectedId ? "#b8a9d4" : "#a08cd8"}
            lineWidth={selectedId ? 1 : 0.5}
            opacity={link.similarity * (selectedId ? 0.7 : 0.4)}
            transparent
          />
        );
      })}
    </group>
  );
}

function MeridianRings() {
  const rings = useMemo(() => {
    const pts: THREE.Vector3[][] = [];
    const seg = 64;
    // 3 longitude rings (vertical)
    for (let offset of [0, Math.PI / 3, (2 * Math.PI) / 3]) {
      const ring: THREE.Vector3[] = [];
      for (let i = 0; i <= seg; i++) {
        const theta = (i / seg) * Math.PI * 2;
        ring.push(
          new THREE.Vector3(
            Math.cos(theta) * Math.cos(offset),
            Math.sin(theta),
            Math.cos(theta) * Math.sin(offset),
          ),
        );
      }
      pts.push(ring);
    }
    // 2 latitude rings (horizontal)
    for (let lat of [0.5, -0.5]) {
      const ring: THREE.Vector3[] = [];
      const r = Math.cos(lat);
      const y = Math.sin(lat);
      for (let i = 0; i <= seg; i++) {
        const theta = (i / seg) * Math.PI * 2;
        ring.push(new THREE.Vector3(Math.cos(theta) * r, y, Math.sin(theta) * r));
      }
      pts.push(ring);
    }
    return pts;
  }, []);

  return (
    <group>
      {rings.map((ring, i) => (
        <Line
          key={i}
          points={ring.map((p) => [p.x, p.y, p.z])}
          color="#b8a9d4"
          lineWidth={0.5}
          transparent
          opacity={0.18}
        />
      ))}
    </group>
  );
}

function RotatingNodes({
  nodes,
  selectedId,
  hoveredId,
  onSelect,
  onHover,
}: {
  nodes: SphereNode[];
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
    }
  });
  return (
    <group ref={groupRef}>
      {nodes.map((node) => (
        <NodePoint
          key={node.id}
          node={node}
          onClick={(id) => onSelect(selectedId === id ? null : id)}
          onHover={onHover}
          isHovered={hoveredId === node.id}
          isSelected={selectedId === node.id}
        />
      ))}
    </group>
  );
}

function Scene({
  nodes,
  selectedId,
  hoveredId,
  onSelect,
  onHover,
}: {
  nodes: SphereNode[];
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
}) {
  const nodeMap = useMemo(() => {
    const map = new Map<string, SphereNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.6} />
      <pointLight position={[-10, -10, -10]} intensity={0.2} color="#a08cd8" />

      {/* Wireframe globe shell */}
      <Sphere args={[1, 32, 32]}>
        <meshBasicMaterial
          color="#8b8680"
          transparent
          opacity={0.12}
          wireframe
        />
      </Sphere>

      {/* Visible meridian rings for globe shape */}
      <MeridianRings />

      <RotatingNodes
        nodes={nodes}
        selectedId={selectedId}
        hoveredId={hoveredId}
        onSelect={onSelect}
        onHover={onHover}
      />

      <SimilarityEdges
        hoveredId={hoveredId}
        selectedId={selectedId}
        nodeMap={nodeMap}
      />

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={1.2}
        maxDistance={5}
        autoRotate
        autoRotateSpeed={1.0}
      />
    </>
  );
}

export function KnowledgeSphere() {
  const [data, setData] = useState<SphereData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetch("/api/sphere-nodes")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: SphereData) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const displayNodes = useMemo(() => {
    if (!data) return [];
    let filtered =
      sourceFilter === "all"
        ? data.nodes
        : data.nodes.filter((n) => n.source === sourceFilter);

    // Keyword search: highlight matching nodes
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.source.toLowerCase().includes(q),
      );
      return filtered; // show all matches when searching
    }

    // Deterministic downsampling using hash of node ID (same nodes every load)
    return filtered.length > 2000
      ? filtered.filter((n) => hashId(n.id) % filtered.length < 2000)
      : filtered;
  }, [data, sourceFilter, searchQuery]);

  const [selectedContent, setSelectedContent] = useState<NodeContent | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  useEffect(() => {
    if (!selectedId) {
      setSelectedContent(null);
      return;
    }
    setContentLoading(true);
    fetch(`/api/sphere-node/${encodeURIComponent(selectedId)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((content: NodeContent) => {
        setSelectedContent(content);
        setContentLoading(false);
      })
      .catch(() => {
        setSelectedContent(null);
        setContentLoading(false);
      });
  }, [selectedId]);

  const selectedNode = useMemo(() => {
    if (!selectedId || !data) return null;
    return data.nodes.find((n) => n.id === selectedId) || null;
  }, [selectedId, data]);

  const navigateToLink = useCallback(
    (targetId: string) => {
      setSelectedId(targetId);
    },
    [],
  );

  if (loading) {
    return (
      <div className="flex h-[600px] items-center justify-center text-muted">
        <div className="animate-pulse font-mono text-sm">
          Loading knowledge sphere...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[600px] items-center justify-center text-dim">
        <p className="font-mono text-sm">Unable to load sphere data: {error}</p>
      </div>
    );
  }

  if (!data) return null;

  const counts = {
    library: data.nodes.filter((n) => n.source === "library").length,
    conversations: data.nodes.filter((n) => n.source === "conversations").length,
    research: data.nodes.filter((n) => n.source === "research").length,
  };

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      {/* Sphere */}
      <div className="relative h-[500px] w-full flex-1 overflow-hidden rounded-2xl border border-border bg-surface-alt/30 lg:h-[600px]">
        <Canvas
          camera={{ position: [0, 0, 2.5], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
        >
          <Scene
            nodes={displayNodes}
            selectedId={selectedId}
            hoveredId={hoveredId}
            onSelect={setSelectedId}
            onHover={setHoveredId}
          />
        </Canvas>

        {/* Search */}
        <div className="absolute top-4 left-4 right-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="w-full rounded-lg border border-border bg-surface/80 px-3 py-2 font-mono text-xs text-fg placeholder:text-dim backdrop-blur-sm focus:border-lavender focus:outline-none"
          />
        </div>

        {/* Legend + Filters */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-2">
          <div className="flex gap-4 font-mono text-xs text-dim">
            <button
              onClick={() => setSourceFilter("all")}
              className={`flex items-center gap-1.5 transition ${sourceFilter === "all" ? "text-fg" : "hover:text-fg"}`}
            >
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-lavender" />
              All ({data.nodes.length.toLocaleString()})
            </button>
            <button
              onClick={() => setSourceFilter("library")}
              className={`flex items-center gap-1.5 transition ${sourceFilter === "library" ? "text-fg" : "hover:text-fg"}`}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: SOURCE_COLORS.library }}
              />
              Library ({counts.library.toLocaleString()})
            </button>
            <button
              onClick={() => setSourceFilter("conversations")}
              className={`flex items-center gap-1.5 transition ${sourceFilter === "conversations" ? "text-fg" : "hover:text-fg"}`}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: SOURCE_COLORS.conversations }}
              />
              Conversations ({counts.conversations.toLocaleString()})
            </button>
            <button
              onClick={() => setSourceFilter("research")}
              className={`flex items-center gap-1.5 transition ${sourceFilter === "research" ? "text-fg" : "hover:text-fg"}`}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: SOURCE_COLORS.research }}
              />
              Research ({counts.research.toLocaleString()})
            </button>
          </div>
        </div>

        <div className="absolute bottom-4 right-4 font-mono text-xs text-dim">
          {displayNodes.length.toLocaleString()} visible · drag to rotate ·
          scroll to zoom · click node for details
        </div>
      </div>

      {/* Detail Panel */}
      {selectedNode ? (
        <div className="w-full rounded-2xl border border-border bg-surface p-6 lg:w-80">
          <div className="flex items-start justify-between">
            <div>
              <span
                className="inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                style={{
                  backgroundColor: `${SOURCE_COLORS[selectedNode.source]}22`,
                  color: SOURCE_COLORS[selectedNode.source],
                }}
              >
                {selectedNode.source}
              </span>
              <h3 className="mt-2 font-mono text-sm font-semibold text-ink">
                {selectedNode.label}
              </h3>
            </div>
            <button
              onClick={() => setSelectedId(null)}
              className="font-mono text-xs text-dim hover:text-fg"
            >
              ✕
            </button>
          </div>

          <p className="mt-1 font-mono text-[10px] text-dim">
            {selectedNode.token_count.toLocaleString()} tokens
          </p>

          {contentLoading ? (
            <div className="mt-4 flex items-center justify-center rounded-lg border border-border bg-surface-alt p-6">
              <div className="animate-pulse font-mono text-xs text-dim">
                Loading content…
              </div>
            </div>
          ) : selectedContent?.content_preview ? (
            <div className="mt-4 max-h-[300px] overflow-y-auto rounded-lg border border-border bg-surface-alt p-3">
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-fg">
                {selectedContent.content_preview}
              </pre>
            </div>
          ) : null}

          {selectedNode.links.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 font-mono text-xs font-semibold text-lavender">
                {selectedNode.links.length} Connections
              </h4>
              <div className="max-h-[200px] space-y-1 overflow-y-auto">
                {selectedNode.links.slice(0, 10).map((link) => {
                  const targetNode = data.nodes.find(
                    (n) => n.id === link.target,
                  );
                  return (
                    <button
                      key={link.target}
                      onClick={() => navigateToLink(link.target)}
                      className="flex w-full items-center justify-between rounded px-2 py-1 font-mono text-[10px] text-muted transition hover:bg-lavender-bg hover:text-fg"
                    >
                      <span className="truncate">{link.target}</span>
                      <span className="shrink-0 text-dim">
                        ×{link.similarity.toFixed(2)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="hidden w-80 items-center justify-center rounded-2xl border border-border bg-surface p-6 lg:flex">
          <p className="font-mono text-sm text-dim">
            Click a node to see its content and connections
          </p>
        </div>
      )}
    </div>
  );
}
