/**
 * SQLite OPFS Demo — Browser-side memory persistence demo
 *
 * Demonstrates creating, querying, and managing memories
 * entirely in the browser using SQLite + OPFS.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { useWASM } from "@/components/WASMProvider";
import type { MemoryRecord } from "@/lib/sqlite-opfs";

export function SQLiteOPFSDemo() {
  const { sqliteReady, insertMemory, queryMemories, getDBStats, getGardenStats, deleteMemory } = useWASM();
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [stats, setStats] = useState({ memoryCount: 0, associationCount: 0, unsyncedCount: 0, dbSizeBytes: 0 });
  const [gardenStats, setGardenStats] = useState<Record<string, number>>({});
  const [newContent, setNewContent] = useState("");
  const [newGarden, setNewGarden] = useState("joy");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!sqliteReady) return;
    setLoading(true);
    try {
      const result = await queryMemories({ limit: 50 });
      setMemories(result.memories);
      const dbStats = await getDBStats();
      setStats(dbStats);
      const gStats = await getGardenStats();
      setGardenStats(gStats);
    } catch (err) {
      console.error("Failed to refresh:", err);
    } finally {
      setLoading(false);
    }
  }, [sqliteReady, queryMemories, getDBStats, getGardenStats]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleAddMemory = async () => {
    if (!newContent.trim()) return;
    try {
      await insertMemory({
        content: newContent,
        garden: newGarden,
        type: "memory",
        metadata: { source: "browser-demo" },
      });
      setNewContent("");
      await refresh();
    } catch (err) {
      console.error("Failed to insert memory:", err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMemory(id);
      await refresh();
    } catch (err) {
      console.error("Failed to delete memory:", err);
    }
  };

  const handleSeedDemo = async () => {
    const demoMemories = [
      { content: "WhiteMagic is a cognitive operating system for agentic AI", garden: "wisdom" },
      { content: "The galaxy has 28 gardens organized in 7 ganYing clusters", garden: "mystery" },
      { content: "Memory holography uses 5D coordinates (x, y, z, w, t)", garden: "truth" },
      { content: "The dispatch pipeline has 8 stages with Dharma governance", garden: "dharma" },
      { content: "WASM runtime provides 10-100x speedup for edge inference", garden: "play" },
      { content: "SQLite OPFS enables persistent browser-side storage", garden: "practice" },
    ];

    for (const mem of demoMemories) {
      await insertMemory({ ...mem, type: "memory", metadata: { source: "seed" } });
    }
    await refresh();
  };

  if (!sqliteReady) {
    return (
      <div className="p-6 rounded-lg bg-gray-900 border border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 rounded-full bg-yellow-500 animate-pulse" />
          <p className="text-gray-300">Initializing SQLite OPFS...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg bg-gray-900 border border-gray-700 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">SQLite OPFS — Browser Memory Storage</h2>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-sm text-green-400">Ready</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-3 rounded bg-gray-800">
          <p className="text-2xl font-bold text-blue-400">{stats.memoryCount}</p>
          <p className="text-sm text-gray-400">Memories</p>
        </div>
        <div className="p-3 rounded bg-gray-800">
          <p className="text-2xl font-bold text-purple-400">{stats.associationCount}</p>
          <p className="text-sm text-gray-400">Associations</p>
        </div>
        <div className="p-3 rounded bg-gray-800">
          <p className="text-2xl font-bold text-yellow-400">{stats.unsyncedCount}</p>
          <p className="text-sm text-gray-400">Unsynced</p>
        </div>
        <div className="p-3 rounded bg-gray-800">
          <p className="text-2xl font-bold text-green-400">{(stats.dbSizeBytes / 1024).toFixed(1)}KB</p>
          <p className="text-sm text-gray-400">DB Size</p>
        </div>
      </div>

      {/* Garden Stats */}
      {Object.keys(gardenStats).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-400 mb-2">Memories by Garden</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(gardenStats).map(([garden, count]) => (
              <span key={garden} className="px-3 py-1 rounded-full bg-gray-800 text-sm text-gray-300">
                {garden}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Add Memory Form */}
      <div className="space-y-3">
        <div className="flex gap-3">
          <input
            type="text"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Enter memory content..."
            className="flex-1 px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            onKeyDown={(e) => e.key === "Enter" && handleAddMemory()}
          />
          <select
            value={newGarden}
            onChange={(e) => setNewGarden(e.target.value)}
            className="px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:border-blue-500"
          >
            {["joy", "wisdom", "truth", "mystery", "play", "dharma", "practice", "presence"].map(g => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
          <button
            onClick={handleAddMemory}
            className="px-6 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors"
          >
            Add
          </button>
        </div>
        <button
          onClick={handleSeedDemo}
          className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
        >
          Seed Demo Memories
        </button>
      </div>

      {/* Memory List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {loading ? (
          <p className="text-gray-400 text-center py-4">Loading...</p>
        ) : memories.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No memories yet. Add one above or seed demo data.</p>
        ) : (
          memories.map(mem => (
            <div key={mem.id} className="p-3 rounded bg-gray-800 border border-gray-700 flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm truncate">{mem.content}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="px-2 py-0.5 rounded bg-gray-700 text-xs text-gray-400">{mem.garden}</span>
                  <span className="text-xs text-gray-500">{new Date(mem.created_at).toLocaleString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(mem.id)}
                className="px-2 py-1 rounded text-red-400 hover:bg-red-900/30 text-xs transition-colors"
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
