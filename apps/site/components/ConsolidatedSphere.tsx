"use client";

import { useEffect, useState, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sphere, Html } from "@react-three/drei";
import * as THREE from "three";

interface ClusterNode {
  id: string;
  cluster_id: number;
  title: string;
  keywords: string[];
  token_count: number;
  source_chunks: string[];
  average_similarity: number;
}

interface ClusterSphereNode {
  id: string;
  cluster_id: number;
  title: string;
  keywords: string[];
  token_count: number;
  chunk_count: number;
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
}

function fibonacciSphere(index: number, total: number): [number, number, number] {
  const phi = Math.acos(1 - 2 * (index + 0.5) / total);
  const theta = Math.PI * (1 + Math.sqrt(5)) * index;
  return [
    Math.cos(theta) * Math.sin(phi),
    Math.sin(theta) * Math.sin(phi),
    Math.cos(phi),
  ];
}

const clusterColors = [
  "#a08cd8", "#60a5fa", "#4ade80", "#fb923c", "#f472b6",
  "#38bdf8", "#a3e635", "#fbbf24", "#e879f9", "#34d399",
];

function ClusterNodePoint({
  node,
  selectedId,
  onSelect,
}: {
  node: ClusterSphereNode;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const isSelected = selectedId === node.id;
  const pos = useMemo(
    () => new THREE.Vector3(node.x, node.y, node.z),
    [node.x, node.y, node.z],
  );

  return (
    <group>
      <mesh
        position={pos}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(isSelected ? null : node.id);
        }}
      >
        <sphereGeometry args={[node.size * 0.02, 16, 16]} />
        <meshBasicMaterial color={isSelected ? "#ffffff" : node.color} />
      </mesh>

      {isSelected && (
        <Html position={[node.x, node.y + node.size * 0.03, node.z]} center>
          <div className="whitespace-nowrap rounded-lg border border-border bg-surface/95 px-4 py-2.5 text-xs shadow-xl backdrop-blur-sm">
            <p className="mb-1 font-head font-semibold text-ink">
              {node.title}
            </p>
            <p className="font-mono text-dim">
              {node.token_count} tokens · {node.chunk_count} chunks · cluster {node.cluster_id}
            </p>
            {node.keywords.length > 0 && (
              <p className="mt-1 text-lavender">
                {node.keywords.slice(0, 5).join(", ")}
              </p>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

function ConsolidatedScene({ nodes }: { nodes: ClusterSphereNode[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.6} />
      <pointLight position={[-10, -10, -10]} intensity={0.2} color="#a08cd8" />

      <Sphere args={[1, 32, 32]}>
        <meshBasicMaterial color="#3d3a36" transparent opacity={0.05} wireframe />
      </Sphere>

      {nodes.map((node) => (
        <ClusterNodePoint
          key={node.id}
          node={node}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      ))}

      <OrbitControls enableDamping dampingFactor={0.1} minDistance={1.5} maxDistance={5} />
    </>
  );
}

export function ConsolidatedSphere() {
  const [nodes, setNodes] = useState<ClusterSphereNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/consolidated_relabeled.jsonl")
      .then((res) => res.text())
      .then((text) => {
        const clusters: ClusterNode[] = text
          .split("\n")
          .filter(Boolean)
          .map((line) => JSON.parse(line));

        const sphereNodes: ClusterSphereNode[] = clusters.map((c, i) => {
          const [x, y, z] = fibonacciSphere(i, clusters.length);
          return {
            id: c.id,
            cluster_id: c.cluster_id,
            title: c.title.length > 80 ? c.title.slice(0, 77) + "..." : c.title,
            keywords: c.keywords,
            token_count: c.token_count,
            chunk_count: c.source_chunks.length,
            x,
            y,
            z,
            color: clusterColors[c.cluster_id % clusterColors.length],
            size: Math.min(3, Math.max(0.5, c.token_count / 2000)),
          };
        });

        setNodes(sphereNodes);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-[600px] items-center justify-center text-muted">
        <div className="animate-pulse font-mono text-sm">
          Loading consolidated view...
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-border bg-surface-alt/30">
      <Canvas
        camera={{ position: [0, 0, 2.5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ConsolidatedScene nodes={nodes} />
      </Canvas>

      <div className="absolute bottom-4 left-4 font-mono text-xs text-dim">
        {nodes.length} semantic clusters · click for details
      </div>
    </div>
  );
}
