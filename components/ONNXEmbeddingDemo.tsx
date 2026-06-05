/**
 * ONNX Embedding Demo — Client-side memory embedding demo
 *
 * Demonstrates creating embeddings for memories entirely in the browser
 * using ONNX Runtime Web and a quantized MiniLM model.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { useWASM } from "@/components/WASMProvider";

export function ONNXEmbeddingDemo() {
  const { embeddingReady, embed, createMemoryWithEmbedding, searchBySimilarity, queryMemories } = useWASM();
  const [text, setText] = useState("");
  const [embedding, setEmbedding] = useState<number[] | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ content: string; garden: string; score: number }>>([]);
  const [memoryCount, setMemoryCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const refreshCount = useCallback(async () => {
    try {
      const result = await queryMemories({ limit: 1 });
      setMemoryCount(result.total);
    } catch {
      // ignore
    }
  }, [queryMemories]);

  useEffect(() => {
    refreshCount();
  }, [refreshCount]);

  const handleEmbed = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const result = await embed(text);
      setEmbedding(result.embedding);
      setLatency(result.latency);
    } catch (err) {
      console.error("Embedding failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMemory = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      await createMemoryWithEmbedding(text, "wisdom");
      setText("");
      setEmbedding(null);
      setLatency(null);
      await refreshCount();
    } catch (err) {
      console.error("Create memory failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const results = await searchBySimilarity(searchQuery, 5);
      setSearchResults(results.map(r => ({
        content: r.memory.content,
        garden: r.memory.garden,
        score: r.score,
      })));
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedMemories = async () => {
    const memories = [
      { content: "Machine learning models can learn patterns from data", garden: "wisdom" },
      { content: "Neural networks use layers of interconnected neurons", garden: "truth" },
      { content: "The galaxy visualization shows 5D memory coordinates", garden: "mystery" },
      { content: "WhiteMagic has 28 gardens organized in clusters", garden: "dharma" },
      { content: "WebAssembly runs at near-native speed in browsers", garden: "play" },
    ];

    setLoading(true);
    for (const mem of memories) {
      try {
        await createMemoryWithEmbedding(mem.content, mem.garden);
      } catch {
        // ignore individual failures
      }
    }
    await refreshCount();
    setLoading(false);
  };

  if (!embeddingReady) {
    return (
      <div className="p-6 rounded-lg bg-gray-900 border border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 rounded-full bg-yellow-500 animate-pulse" />
          <p className="text-gray-300">Loading ONNX embedding model (~22MB)...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg bg-gray-900 border border-gray-700 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">ONNX Embedding — Client-Side Vectors</h2>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-sm text-green-400">Ready</span>
          <span className="text-xs text-gray-500 ml-2">{memoryCount} memories with embeddings</span>
        </div>
      </div>

      {/* Embed Text */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-300">Embed Text</label>
        <div className="flex gap-3">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to embed..."
            className="flex-1 px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            onKeyDown={(e) => e.key === "Enter" && handleEmbed()}
          />
          <button
            onClick={handleEmbed}
            disabled={loading}
            className="px-6 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50"
          >
            Embed
          </button>
        </div>
        {latency !== null && (
          <p className="text-xs text-gray-400">
            Latency: {latency.toFixed(0)}ms | Dimensions: {embedding?.length ?? 0}
          </p>
        )}
      </div>

      {/* Embedding Preview */}
      {embedding && (
        <div className="p-3 rounded bg-gray-800 border border-gray-700">
          <p className="text-xs text-gray-400 mb-2">Embedding vector (first 16 of {embedding.length}):</p>
          <div className="flex flex-wrap gap-1">
            {embedding.slice(0, 16).map((v, i) => (
              <span
                key={i}
                className="px-1.5 py-0.5 rounded text-xs font-mono"
                style={{
                  backgroundColor: v > 0 ? `rgba(59, 130, 246, ${Math.abs(v)})` : `rgba(239, 68, 68, ${Math.abs(v)})`,
                  color: "white",
                }}
              >
                {v.toFixed(3)}
              </span>
            ))}
            <span className="text-gray-500 text-xs">...</span>
          </div>
        </div>
      )}

      {/* Create Memory with Embedding */}
      {text && (
        <button
          onClick={handleCreateMemory}
          disabled={loading}
          className="w-full px-4 py-2 rounded bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors disabled:opacity-50"
        >
          Create Memory with Embedding
        </button>
      )}

      {/* Semantic Search */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-300">Semantic Search</label>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memories by meaning..."
            className="flex-1 px-4 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2 rounded bg-green-600 hover:bg-green-700 text-white font-medium transition-colors disabled:opacity-50"
          >
            Search
          </button>
        </div>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="space-y-2">
          {searchResults.map((r, i) => (
            <div key={i} className="p-3 rounded bg-gray-800 border border-gray-700">
              <div className="flex items-center justify-between">
                <p className="text-white text-sm">{r.content}</p>
                <span className="text-xs text-green-400 font-mono">{(r.score * 100).toFixed(1)}%</span>
              </div>
              <span className="text-xs text-gray-500">{r.garden}</span>
            </div>
          ))}
        </div>
      )}

      {/* Seed Memories */}
      <button
        onClick={handleSeedMemories}
        disabled={loading}
        className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors disabled:opacity-50"
      >
        Seed Demo Memories with Embeddings
      </button>
    </div>
  );
}
