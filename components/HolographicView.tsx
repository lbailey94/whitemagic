/**
 * Holographic Memory View — 3D semantic cluster visualization
 *
 * Ported from whitemagic-aux/whitemagic-frontend/hub/src/components/HolographicView.tsx
 * Adapted for web. Clusters represent real WhiteMagic subsystems with
 * actual module counts and architectural principles from the core.
 * Uses @react-three/fiber + drei.
 *
 * Clusters appear as distorted nebulae, attractors as black holes
 * with accretion disks. Click a cluster for details.
 */

"use client";

import { useState, useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, Text, Float, MeshDistortMaterial } from "@react-three/drei";
import { Brain, Sparkles, Layers } from "lucide-react";
import * as THREE from "three";

interface Cluster {
  id: string;
  center: [number, number, number, number];
  size: number;
  label: string;
  macro_summary: string;
  principles: string[];
  memories: string[];
  quadrant: string;
}

interface Attractor {
  id: string;
  center: [number, number, number];
  mass: number;
  event_horizon: number;
  density: number;
}

// Real subsystem clusters — derived from the core's actual architecture.
// Each cluster represents a WhiteMagic subsystem with its real module count,
// architectural principles, and galactic zone classification.
const SUBSYSTEM_CLUSTERS: Cluster[] = [
  {
    id: "1",
    center: [0, 0, 0, 0.9],
    size: 1.8,
    label: "Memory Core",
    macro_summary: "89 modules: unified SQLite backend, 5D holographic coordinates, embeddings (43KB), graph engine (30KB), constellations (40KB), miners (56KB), HRR, mindful forgetting.",
    principles: ["5D coordinates: temporal, semantic, emotional, relational, importance", "SQLite with FTS5 + WAL mode", "Holographic Reduced Representations"],
    memories: [],
    quadrant: "core",
  },
  {
    id: "2",
    center: [3, 2, -1, 0.7],
    size: 1.2,
    label: "Rust Accelerator",
    macro_summary: "50K+ lines of Rust: EventRing, SIMD cosine batch, rate limiter, galactic accelerator, Fragment semantic search. PyO3 bridge with Python fallback.",
    principles: ["Zero-copy dispatch", "PyO3 boundary safety", "Graceful degradation to Python"],
    memories: [],
    quadrant: "east",
  },
  {
    id: "3",
    center: [-2.5, -1, 2, 0.5],
    size: 0.9,
    label: "Governance Pipeline",
    macro_summary: "8-stage dispatch: Governor, Input Sanitizer, Rate Limiter, Constitutional Checks, Tool Permissions, Dharma Engine, Karma Ledger, Audit Trail. Every tool call passes through here.",
    principles: ["8-stage safety pipeline", "DharmaLevel: Universal, Compassion, Integrity, Harmony, Wisdom", "Merkle-signed audit trail"],
    memories: [],
    quadrant: "south",
  },
  {
    id: "4",
    center: [2, -2.5, 1.5, 0.4],
    size: 0.7,
    label: "Dream Cycle",
    macro_summary: "41KB dream_cycle.py with 12 phases: triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay, constellation, prediction, enrichment, harmonize.",
    principles: ["12-phase consolidation cycle", "Serendipity mining", "Decay-aware retention"],
    memories: [],
    quadrant: "north",
  },
  {
    id: "5",
    center: [-3, 1.5, -2, 0.6],
    size: 1.0,
    label: "Galactic Substrate",
    macro_summary: "5-zone lifecycle: Core, Inner Rim, Mid Band, Outer Rim, Far Edge. 12,238 memories + 21,087 associations + 12,638 embeddings in the live substrate DB.",
    principles: ["Zone-based lifecycle", "Never delete, archive", "Lineage preservation"],
    memories: [],
    quadrant: "west",
  },
  {
    id: "6",
    center: [1.5, 3, 0.5, 0.3],
    size: 0.6,
    label: "Intelligence Layer",
    macro_summary: "103 modules: bicameral reasoning, cognitive modes, foresight engine, insight pipeline (23KB), knowledge graph v2, multi-spectral reasoning, self-model, working memory.",
    principles: ["Bicameral reasoning", "Multi-spectral analysis", "Self-model forecasting"],
    memories: [],
    quadrant: "east",
  },
  {
    id: "7",
    center: [-1, 2.5, -1.5, 0.45],
    size: 0.8,
    label: "Resonance Engine",
    macro_summary: "19 modules: resonance engine, Gan Ying async, Julia resonance (23KB), self-model forecast. Event-driven linking with confidence scoring.",
    principles: ["Event-driven linking", "Confidence scoring", "Async propagation"],
    memories: [],
    quadrant: "north",
  },
  {
    id: "8",
    center: [0.5, -3, 2.5, 0.35],
    size: 0.5,
    label: "Gardens",
    macro_summary: "73 items across 20+ thematic gardens: joy, grief, courage, love, wisdom, mystery, play. Emotional memory subsystems that gave the system its roots.",
    principles: ["20+ emotional themes", "Garden-specific retention", "Emotional valence scoring"],
    memories: [],
    quadrant: "south",
  },
];

const SUBSYSTEM_ATTRACTORS: Attractor[] = [
  {
    id: "a1",
    center: [0, 0, 0],
    mass: 150,
    event_horizon: 0.8,
    density: 0.95,
  },
  {
    id: "a2",
    center: [-2.5, -1, 2],
    mass: 80,
    event_horizon: 0.5,
    density: 0.7,
  },
];

function HolographicCore({
  clusters,
  attractors,
  onClusterSelect,
}: {
  clusters: Cluster[];
  attractors: Attractor[];
  onClusterSelect: (c: Cluster) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.001;
    }
  });

  return (
    <group ref={groupRef}>
      <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />

      {/* Clusters as nebulae */}
      {clusters.map((cluster) => (
        <Float
          key={cluster.id}
          speed={1.5}
          rotationIntensity={0.5}
          floatIntensity={0.5}
        >
          <mesh
            position={[
              cluster.center[0] * 5,
              cluster.center[1] * 5,
              cluster.center[2] * 5,
            ]}
            onClick={(e) => {
              e.stopPropagation();
              onClusterSelect(cluster);
            }}
          >
            <sphereGeometry args={[cluster.size * 0.3, 32, 32]} />
            <MeshDistortMaterial
              color={new THREE.Color().setHSL(
                0.6 + cluster.center[3] * 0.4,
                0.8,
                0.6,
              )}
              speed={3}
              distort={0.3 + cluster.center[3] * 0.2}
              transparent
              opacity={0.7}
            />
          </mesh>
          <Text
            position={[
              cluster.center[0] * 5,
              cluster.center[1] * 5 + cluster.size * 0.5,
              cluster.center[2] * 5,
            ]}
            fontSize={0.25}
            color="white"
            anchorX="center"
            anchorY="middle"
            maxWidth={2}
          >
            {cluster.label}
          </Text>
        </Float>
      ))}

      {/* Black hole attractors */}
      {attractors.map((attractor) => (
        <Float
          key={attractor.id}
          speed={0.5}
          rotationIntensity={0.2}
          floatIntensity={0.2}
        >
          <mesh
            position={attractor.center}
          >
            <sphereGeometry args={[attractor.event_horizon, 64, 64]} />
            <meshStandardMaterial
              color="#000000"
              roughness={0.1}
              metalness={0.8}
              emissive="#1a0033"
              emissiveIntensity={0.5}
              transparent
              opacity={0.9}
            />
          </mesh>
          {/* Accretion disk */}
          <mesh
            position={attractor.center}
            rotation={[Math.PI / 2, 0, 0]}
          >
            <ringGeometry
              args={[
                attractor.event_horizon * 1.2,
                attractor.event_horizon * 2.5,
                64,
              ]}
            />
            <meshBasicMaterial
              color="#8a2be2"
              side={THREE.DoubleSide}
              transparent
              opacity={0.3}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

export function HolographicView({ height = 500 }: { height?: number }) {
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);

  const clusters = useMemo(() => SUBSYSTEM_CLUSTERS, []);
  const attractors = useMemo(() => SUBSYSTEM_ATTRACTORS, []);

  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-border bg-black"
      style={{ height }}
      role="img"
      aria-label="3D holographic view of WhiteMagic subsystem clusters — Memory, Tools, Intelligence, Governance, Resonance, Gardens"
    >
      {/* Header overlay */}
      <div className="absolute left-0 right-0 top-0 z-10 flex items-start justify-between p-4">
        <div>
          <h3 className="flex items-center gap-2 font-head text-lg font-bold text-white">
            <Brain className="text-lavender" size={22} />
            Holographic Memory
          </h3>
          <p className="mt-1 text-xs text-gray-400">
            Semantic clusters and emergent patterns in 5D space
          </p>
        </div>
      </div>

      {/* 3D Canvas */}
      <Canvas camera={{ position: [0, 5, 15], fov: 50 }}>
        <HolographicCore
          clusters={clusters}
          attractors={attractors}
          onClusterSelect={setSelectedCluster}
        />
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
        />
      </Canvas>

      {/* Detail overlay */}
      {selectedCluster && (
        <div className="absolute right-4 top-20 z-20 w-72 rounded-2xl border border-border bg-surface/90 p-5 backdrop-blur-xl">
          <div className="mb-3 flex items-start justify-between">
            <h4 className="font-head text-lg font-bold leading-tight text-ink">
              {selectedCluster.label}
            </h4>
            <button
              onClick={() => setSelectedCluster(null)}
              className="text-dim hover:text-fg"
            >
              {"\u2715"}
            </button>
          </div>

          <div className="mb-3 inline-block rounded bg-lavender-bg px-2 py-1 font-mono text-xs capitalize text-lavender">
            {selectedCluster.quadrant.replace("_", " ")} sector
          </div>

          <p className="mb-4 text-sm italic leading-relaxed text-muted">
            &ldquo;{selectedCluster.macro_summary}&rdquo;
          </p>

          {selectedCluster.principles.length > 0 && (
            <div className="mb-4">
              <div className="mb-2 font-mono text-xs uppercase tracking-wider text-dim">
                Sector Principles
              </div>
              <ul className="space-y-1.5">
                {selectedCluster.principles.map((p, i) => (
                  <li
                    key={i}
                    className="flex gap-2 text-sm text-muted"
                  >
                    <span className="text-lavender">{"\u2022"}</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Footer stats */}
      <div className="absolute bottom-4 left-4 right-4 z-10 flex gap-3">
        <div className="flex-1 rounded-xl border border-border bg-surface/80 p-3 backdrop-blur-md">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-fg">
            <Sparkles size={14} className="text-lavender" />
            Detected Patterns
          </div>
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-lg border border-border/50 bg-black/50 p-2">
              <div className="text-xs text-dim">Clusters</div>
              <div className="font-bold text-lavender">{clusters.length}</div>
            </div>
            <div className="rounded-lg border border-border/50 bg-black/50 p-2">
              <div className="text-xs text-dim">Attractors</div>
              <div className="font-bold text-purple-400">
                {attractors.length}
              </div>
            </div>
            <div className="rounded-lg border border-border/50 bg-black/50 p-2">
              <div className="text-xs text-dim">Stability</div>
              <div className="font-bold text-green-400">94%</div>
            </div>
            <div className="rounded-lg border border-border/50 bg-black/50 p-2">
              <div className="text-xs text-dim">Resonance</div>
              <div className="font-bold text-lavender">0.82</div>
            </div>
          </div>
        </div>

        <div className="w-48 rounded-xl border border-border bg-surface/80 p-3 backdrop-blur-md">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-fg">
            <Layers size={14} className="text-lavender" />
            Legend
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs text-muted">
              <div className="h-2 w-2 rounded-full bg-purple-500" />
              <span>Semantic core</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <div className="h-2 w-2 rounded-full bg-cyan-500" />
              <span>Active resonance</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <div className="h-2 w-2 rounded-full bg-yellow-500" />
              <span>Emergent insight</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <div className="h-2 w-2 rounded-full border border-purple-500 bg-black" />
              <span>Black hole attractor</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
