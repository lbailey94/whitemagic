"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  OrbitControls,
  Sphere,
  Text,
  Html,
  Line,
} from "@react-three/drei";
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
  content_preview?: string;
}

interface SphereData {
  version: string;
  nodes: SphereNode[];
}

function NodePoint({
  node,
  onClick,
  onHover,
  isHovered,
}: {
  node: SphereNode;
  onClick: (id: string | null) => void;
  onHover: (id: string | null) => void;
  isHovered: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(
    () => new THREE.Vector3(node.x, node.y, node.z),
    [node.x, node.y, node.z],
  );

  useFrame((_, delta) => {
    if (meshRef.current && isHovered) {
      meshRef.current.scale.lerp(
        new THREE.Vector3(2, 2, 2),
        0.1,
      );
    } else if (meshRef.current) {
      meshRef.current.scale.lerp(
        new THREE.Vector3(1, 1, 1),
        0.1,
      );
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

function NodeLabel({
  node,
  visible,
}: {
  node: SphereNode;
  visible: boolean;
}) {
  if (!visible) return null;
  return (
    <Html
      position={[node.x, node.y + node.size * 0.025, node.z]}
      center
      style={{ pointerEvents: "none" }}
    >
      <div className="whitespace-nowrap rounded-lg border border-border bg-surface/90 px-3 py-2 text-xs shadow-lg backdrop-blur-sm">
        <p className="font-mono text-dim">
          {node.source} · {node.token_count} tokens
        </p>
        {node.content_preview && (
          <p className="mt-1 max-w-xs text-fg line-clamp-2">
            {node.content_preview}
          </p>
        )}
        {node.links.length > 0 && (
          <p className="mt-1 font-mono text-xs text-lavender">
            {node.links.length} links
          </p>
        )}
      </div>
    </Html>
  );
}

function SimilarityEdges({
  nodes,
  hoveredId,
  nodeMap,
}: {
  nodes: SphereNode[];
  hoveredId: string | null;
  nodeMap: Map<string, SphereNode>;
}) {
  if (!hoveredId) return null;
  const source = nodeMap.get(hoveredId);
  if (!source) return null;

  return (
    <group>
      {source.links.slice(0, 5).map((link) => {
        const target = nodeMap.get(link.target);
        if (!target) return null;
        return (
          <Line
            key={link.target}
            points={[
              [source.x, source.y, source.z],
              [target.x, target.y, target.z],
            ]}
            color="#a08cd8"
            lineWidth={0.5}
            opacity={link.similarity * 0.5}
            transparent
          />
        );
      })}
    </group>
  );
}

function Scene({ nodes }: { nodes: SphereNode[] }) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const nodeMap = useMemo(() => {
    const map = new Map<string, SphereNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  const selectedNode = selectedId ? nodeMap.get(selectedId) : null;
  const hoveredNode = hoveredId ? nodeMap.get(hoveredId) : null;

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.6} />
      <pointLight position={[-10, -10, -10]} intensity={0.2} color="#a08cd8" />

      {/* Outer reference sphere (transparent) */}
      <Sphere args={[1, 32, 32]}>
        <meshBasicMaterial
          color="#3d3a36"
          transparent
          opacity={0.05}
          wireframe
        />
      </Sphere>

      {/* Nodes */}
      {nodes.map((node) => (
        <NodePoint
          key={node.id}
          node={node}
          onClick={(id) => setSelectedId(id)}
          onHover={(id) => setHoveredId(id)}
          isHovered={hoveredId === node.id}
        />
      ))}

      {/* Similarity edges on hover */}
      <SimilarityEdges
        nodes={nodes}
        hoveredId={hoveredId}
        nodeMap={nodeMap}
      />

      {/* Label for hovered/selected node */}
      {hoveredNode && !selectedNode && (
        <NodeLabel node={hoveredNode} visible={true} />
      )}
      {selectedNode && <NodeLabel node={selectedNode} visible={true} />}
      {!selectedNode && hoveredNode && (
        <NodeLabel node={hoveredNode} visible={true} />
      )}

      <OrbitControls
        enableDamping
        dampingFactor={0.1}
        minDistance={1.5}
        maxDistance={5}
      />
    </>
  );
}

export function KnowledgeSphere() {
  const [data, setData] = useState<SphereData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/sphere-nodes.json")
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

  // Downsample for performance — render up to 2,000 nodes
  const displayNodes =
    data.nodes.length > 2000
      ? data.nodes.filter(() => Math.random() < 2000 / data.nodes.length)
      : data.nodes;

  return (
    <div className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-border bg-surface-alt/30">
      <Canvas
        camera={{ position: [0, 0, 2.5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <Scene nodes={displayNodes} />
      </Canvas>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-4 font-mono text-xs text-dim">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: "#60a5fa" }}
          />
          Library ({data.nodes.filter((n) => n.source === "library").length})
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: "#4ade80" }}
          />
          Conversations (
          {data.nodes.filter((n) => n.source === "conversations").length})
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: "#fb923c" }}
          />
          Research ({data.nodes.filter((n) => n.source === "research").length})
        </span>
      </div>

      <div className="absolute bottom-4 right-4 font-mono text-xs text-dim">
        {data.nodes.length.toLocaleString()} nodes · drag to rotate · scroll to
        zoom
      </div>
    </div>
  );
}
