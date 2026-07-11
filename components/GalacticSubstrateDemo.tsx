/**
 * Galactic Substrate Demo — In-browser local-first memory system
 *
 * Ported from whitemagic-aux/browser-extension/scripts/galactic.js
 * Uses IndexedDB to store memories with galactic zone classification.
 * Demonstrates the 5-zone lifecycle: Core -> Inner Rim -> Mid Band -> Outer Rim -> Far Edge.
 *
 * galactic_distance is separate from importance (matching the core's Memory model):
 *   - Initial distance = 1.0 - importance (high importance starts closer to core)
 *   - Each access pulls the memory inward (distance decreases)
 *   - Time since last access drifts it outward (distance increases)
 *
 * No backend required — all data lives in the browser.
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { GalacticVisualization, type GalaxyMemory } from "@/components/GalacticVisualization";

const DB_NAME = "whitemagic_galactic_demo";
const DB_VERSION = 2;

const GALACTIC_ZONES = {
  CORE: { min: 0.0, max: 0.15, label: "Core", color: "#a855f7", desc: "Highest importance — active, frequently accessed" },
  INNER_RIM: { min: 0.15, max: 0.4, label: "Inner Rim", color: "#6366f1", desc: "High importance — recently active" },
  MID_BAND: { min: 0.4, max: 0.65, label: "Mid Band", color: "#3b82f6", desc: "Moderate importance — stable" },
  OUTER_RIM: { min: 0.65, max: 0.85, label: "Outer Rim", color: "#0891b2", desc: "Lower importance — aging" },
  FAR_EDGE: { min: 0.85, max: 1.0, label: "Far Edge", color: "#64748b", desc: "Lowest importance — archived, never deleted" },
} as const;

type ZoneKey = keyof typeof GALACTIC_ZONES;

interface Memory {
  id: number;
  content: string;
  memory_type: string;
  importance: number;
  galactic_distance: number;
  galactic_zone: ZoneKey;
  tags: string[];
  created_at: string;
  updated_at: string;
  access_count: number;
}

function classifyZone(distance: number): ZoneKey {
  for (const [key, zone] of Object.entries(GALACTIC_ZONES)) {
    if (distance >= zone.min && distance < zone.max) return key as ZoneKey;
  }
  return "FAR_EDGE";
}

function computeDistance(importance: number, accessCount: number, lastUpdated: string): number {
  // Base distance: high importance = close to core
  let distance = 1.0 - importance;
  // Each access pulls inward
  distance -= accessCount * 0.02;
  // Time drift: memories drift outward over time since last access
  const elapsed = (Date.now() - new Date(lastUpdated).getTime()) / (1000 * 60 * 60); // hours
  distance += elapsed * 0.005;
  return Math.max(0, Math.min(1, distance));
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      // v2: add galactic_distance field and index
      if (!db.objectStoreNames.contains("memories")) {
        const store = db.createObjectStore("memories", {
          keyPath: "id",
          autoIncrement: true,
        });
        store.createIndex("galactic_zone", "galactic_zone", { unique: false });
        store.createIndex("galactic_distance", "galactic_distance", { unique: false });
        store.createIndex("importance", "importance", { unique: false });
        store.createIndex("created_at", "created_at", { unique: false });
      }
    };
  });
}

export function GalacticSubstrateDemo() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [content, setContent] = useState("");
  const [importance, setImportance] = useState(0.5);
  const [memoryType, setMemoryType] = useState("SEMANTIC");
  const [tags, setTags] = useState("");
  const [status, setStatus] = useState<string>("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const dbRef = useRef<IDBDatabase | null>(null);

  const loadMemories = useCallback(async () => {
    if (!dbRef.current) return;
    const tx = dbRef.current.transaction("memories", "readonly");
    const store = tx.objectStore("memories");
    const all = await new Promise<Memory[]>((resolve, reject) => {
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result as Memory[]);
      req.onerror = () => reject(req.error);
    });
    // Recompute distances (time drift)
    const now = Date.now();
    for (const mem of all) {
      mem.galactic_distance = computeDistance(mem.importance, mem.access_count, mem.updated_at);
      mem.galactic_zone = classifyZone(mem.galactic_distance);
    }
    all.sort((a, b) => a.galactic_distance - b.galactic_distance);
    setMemories(all);
  }, []);

  useEffect(() => {
    openDB().then((db) => {
      dbRef.current = db;
      loadMemories();
    }).catch((err) => {
      setStatus(`Failed to open database: ${err.message}`);
    });
    return () => {
      dbRef.current?.close();
    };
  }, [loadMemories]);

  const addMemory = async () => {
    if (!content.trim() || !dbRef.current) return;
    const now = new Date().toISOString();
    const distance = computeDistance(importance, 0, now);
    const zone = classifyZone(distance);
    const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);

    const tx = dbRef.current.transaction("memories", "readwrite");
    const store = tx.objectStore("memories");
    await new Promise<void>((resolve, reject) => {
      const req = store.add({
        content: content.trim(),
        memory_type: memoryType,
        importance,
        galactic_distance: distance,
        galactic_zone: zone,
        tags: tagList,
        created_at: now,
        updated_at: now,
        access_count: 0,
      });
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });

    setContent("");
    setTags("");
    setStatus(`Memory stored in ${GALACTIC_ZONES[zone].label} zone`);
    loadMemories();
    setTimeout(() => setStatus(""), 3000);
  };

  const deleteMemory = async (id: number) => {
    if (!dbRef.current) return;
    const tx = dbRef.current.transaction("memories", "readwrite");
    await new Promise<void>((resolve, reject) => {
      const req = tx.objectStore("memories").delete(id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
    loadMemories();
  };

  const accessMemory = async (mem: Memory) => {
    if (!dbRef.current) return;
    const tx = dbRef.current.transaction("memories", "readwrite");
    const store = tx.objectStore("memories");
    const now = new Date().toISOString();
    const newAccessCount = mem.access_count + 1;
    const newDistance = computeDistance(mem.importance, newAccessCount, now);
    const updated = {
      ...mem,
      access_count: newAccessCount,
      galactic_distance: newDistance,
      galactic_zone: classifyZone(newDistance),
      updated_at: now,
    };
    await new Promise<void>((resolve, reject) => {
      const req = store.put(updated);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
    loadMemories();
  };

  const clearAll = async () => {
    if (!dbRef.current) return;
    const tx = dbRef.current.transaction("memories", "readwrite");
    await new Promise<void>((resolve, reject) => {
      const req = tx.objectStore("memories").clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
    loadMemories();
    setStatus("All memories cleared");
    setTimeout(() => setStatus(""), 2000);
  };

  // Zone distribution
  const zoneCounts = Object.keys(GALACTIC_ZONES).reduce(
    (acc, key) => {
      acc[key as ZoneKey] = memories.filter((m) => m.galactic_zone === key).length;
      return acc;
    },
    {} as Record<ZoneKey, number>,
  );

  // Map memories to galaxy format
  const galaxyMemories: GalaxyMemory[] = memories.map((m) => ({
    id: m.id,
    content: m.content,
    memory_type: m.memory_type,
    importance: m.importance,
    galactic_distance: m.galactic_distance,
    galactic_zone: m.galactic_zone,
    tags: m.tags,
    access_count: m.access_count,
    created_at: m.created_at,
  }));

  const selectedMemory = memories.find((m) => m.id === selectedId) || null;

  return (
    <div className="mx-auto max-w-5xl">
      {/* Galactic Visualization */}
      <div className="mb-8">
        <h3 className="mb-3 font-head text-lg font-semibold text-ink">
          Galactic Memory Map
        </h3>
        <p className="mb-4 text-sm text-muted">
          Each dot is a memory. Radial position reflects galactic distance —
          memories near the center are frequently accessed and high-importance.
          Memories drift outward over time, but are never deleted.
        </p>
        <GalacticVisualization
          memories={galaxyMemories}
          height={480}
          onSelect={(mem) => setSelectedId(mem.id)}
          selectedId={selectedId}
        />
      </div>

      {/* Selected Memory Detail */}
      {selectedMemory && (
        <div className="mb-8 rounded-2xl border-l-4 border border-border bg-surface p-6" style={{ borderLeftColor: GALACTIC_ZONES[selectedMemory.galactic_zone].color }}>
          <div className="mb-2 flex items-start justify-between">
            <h4 className="font-head text-lg font-semibold text-ink">Selected Memory</h4>
            <button onClick={() => setSelectedId(null)} className="text-dim hover:text-fg">
              {"\u2715"}
            </button>
          </div>
          <p className="mb-3 text-sm text-fg">{selectedMemory.content}</p>
          <div className="flex flex-wrap items-center gap-3 font-mono text-xs text-dim">
            <span style={{ color: GALACTIC_ZONES[selectedMemory.galactic_zone].color }}>
              {GALACTIC_ZONES[selectedMemory.galactic_zone].label}
            </span>
            <span>distance={selectedMemory.galactic_distance.toFixed(3)}</span>
            <span>imp={selectedMemory.importance.toFixed(2)}</span>
            <span>{selectedMemory.memory_type}</span>
            <span>accessed {selectedMemory.access_count}x</span>
            {selectedMemory.tags.length > 0 && (
              <span className="text-lavender">
                {selectedMemory.tags.map((t) => `#${t}`).join(" ")}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Zone Distribution Bar */}
      <div className="mb-8 rounded-2xl border border-border bg-surface p-6">
        <h3 className="mb-4 font-head text-lg font-semibold text-ink">
          Zone Distribution
        </h3>
        <div className="flex h-8 overflow-hidden rounded-lg">
          {Object.entries(GALACTIC_ZONES).map(([key, zone]) => {
            const count = zoneCounts[key as ZoneKey];
            const pct = memories.length > 0 ? (count / memories.length) * 100 : 0;
            if (pct === 0) return null;
            return (
              <div
                key={key}
                className="flex items-center justify-center transition-all"
                style={{
                  width: `${pct}%`,
                  backgroundColor: zone.color,
                }}
                title={`${zone.label}: ${count} memories`}
              >
                {pct > 10 && (
                  <span className="text-xs font-bold text-white">
                    {count}
                  </span>
                )}
              </div>
            );
          })}
          {memories.length === 0 && (
            <div className="flex w-full items-center justify-center bg-surface-alt text-sm text-dim">
              No memories yet
            </div>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-4">
          {Object.entries(GALACTIC_ZONES).map(([key, zone]) => (
            <div key={key} className="flex items-center gap-2">
              <div
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: zone.color }}
              />
              <span className="font-mono text-xs text-dim">
                {zone.label} ({zoneCounts[key as ZoneKey]})
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Create Memory Form */}
      <div className="mb-8 rounded-2xl border border-border bg-surface p-6">
        <h3 className="mb-4 font-head text-lg font-semibold text-ink">
          Create Memory
        </h3>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block font-mono text-xs uppercase tracking-wider text-dim">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-4 py-2 text-sm text-fg focus:border-lavender focus:outline-none"
              rows={3}
              placeholder="Enter memory content..."
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block font-mono text-xs uppercase tracking-wider text-dim">
                Type
              </label>
              <select
                value={memoryType}
                onChange={(e) => setMemoryType(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg focus:border-lavender focus:outline-none"
              >
                <option value="SEMANTIC">Semantic</option>
                <option value="EPISODIC">Episodic</option>
                <option value="PROCEDURAL">Procedural</option>
                <option value="SHORT_TERM">Short-term</option>
                <option value="LONG_TERM">Long-term</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block font-mono text-xs uppercase tracking-wider text-dim">
                Importance ({importance.toFixed(2)})
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={importance}
                onChange={(e) => setImportance(parseFloat(e.target.value))}
                className="w-full accent-lavender"
              />
              <div className="mt-1 font-mono text-xs" style={{ color: GALACTIC_ZONES[classifyZone(1.0 - importance)].color }}>
                {GALACTIC_ZONES[classifyZone(1.0 - importance)].label} (initial)
              </div>
            </div>

            <div>
              <label className="mb-1 block font-mono text-xs uppercase tracking-wider text-dim">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg focus:border-lavender focus:outline-none"
                placeholder="research, governance"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={addMemory}
              disabled={!content.trim()}
              className="btn-primary disabled:opacity-50"
            >
              Store Memory
            </button>
            {status && (
              <span className="font-mono text-sm text-lavender">{status}</span>
            )}
          </div>
        </div>
      </div>

      {/* Memory List */}
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-head text-lg font-semibold text-ink">
            Stored Memories ({memories.length})
          </h3>
          {memories.length > 0 && (
            <button
              onClick={clearAll}
              className="font-mono text-xs text-dim hover:text-red-400"
            >
              Clear all
            </button>
          )}
        </div>

        {memories.length === 0 ? (
          <p className="py-8 text-center text-sm text-dim">
            No memories stored. Create one above to see the galactic lifecycle in action.
          </p>
        ) : (
          <div className="space-y-3">
            {memories.map((mem) => {
              const zone = GALACTIC_ZONES[mem.galactic_zone];
              return (
                <div
                  key={mem.id}
                  className="rounded-xl border-l-4 bg-surface-alt p-4"
                  style={{ borderLeftColor: zone.color }}
                >
                  <div className="mb-2 flex items-start justify-between gap-4">
                    <p className="text-sm text-fg">{mem.content}</p>
                    <div className="flex shrink-0 gap-2">
                      <button
                        onClick={() => accessMemory(mem)}
                        className="font-mono text-xs text-lavender hover:underline"
                        title="Access memory (increments access count)"
                      >
                        access
                      </button>
                      <button
                        onClick={() => deleteMemory(mem.id)}
                        className="font-mono text-xs text-dim hover:text-red-400"
                      >
                        delete
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 font-mono text-xs text-dim">
                    <span style={{ color: zone.color }}>{zone.label}</span>
                    <span>dist={mem.galactic_distance.toFixed(3)}</span>
                    <span>imp={mem.importance.toFixed(2)}</span>
                    <span>{mem.memory_type}</span>
                    <span>accessed {mem.access_count}x</span>
                    {mem.tags.length > 0 && (
                      <span className="text-lavender">
                        {mem.tags.map((t) => `#${t}`).join(" ")}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Zone Reference */}
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Object.entries(GALACTIC_ZONES).map(([key, zone]) => (
          <div
            key={key}
            className="rounded-xl border border-border bg-surface p-3"
            style={{ borderTopColor: zone.color, borderTopWidth: 3 }}
          >
            <div className="mb-1 flex items-center gap-2">
              <div
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: zone.color }}
              />
              <span className="font-mono text-xs font-bold text-fg">
                {zone.label}
              </span>
            </div>
            <p className="text-xs text-dim">
              {zone.desc}
            </p>
            <p className="mt-1 font-mono text-xs text-dim">
              {zone.min.toFixed(2)} - {zone.max.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
