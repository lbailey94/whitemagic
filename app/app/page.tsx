/**
 * WhiteMagic PWA — Local-First Blank Canvas
 *
 * Installable PWA that runs entirely in the browser.
 * Zero network calls for memory/governance.
 * User brings their own agent persona.
 */

"use client";

import { useState } from "react";
import { WASMProvider, useWASM } from "@/components/WASMProvider";
import { SQLiteOPFSDemo } from "@/components/SQLiteOPFSDemo";
import { ONNXEmbeddingDemo } from "@/components/ONNXEmbeddingDemo";
import { PWAInstallPrompt } from "@/components/PWAInstallPrompt";
import { AuthProvider } from "@/lib/auth";
import { ArrowRight, Shield, Database, Zap, Globe, Key, Play } from "lucide-react";

function WASMDemo() {
  const { initialized, error, version, infer, cosineSimilarity, getStats } = useWASM();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const handleInfer = () => {
    if (!query.trim()) return;
    const r = infer(query);
    setResult(`${r.answer} (confidence: ${r.confidence.toFixed(2)}, method: ${r.method})`);
  };

  const handleCosineTest = () => {
    const a = [1, 0, 0, 0];
    const b = [0.707, 0.707, 0, 0];
    const sim = cosineSimilarity(a, b);
    setResult(`Cosine([1,0,0,0], [0.707,0.707,0,0]) = ${sim.toFixed(4)}`);
  };

  if (!initialized) {
    return (
      <div className="p-6 text-center">
        {error ? (
          <p className="text-red-400 text-sm">WASM Error: {error}</p>
        ) : (
          <p className="text-gray-400 text-sm">Loading WASM runtime...</p>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-sm text-green-400">WASM v{version} — Ready</span>
      </div>

      {/* Inference Demo */}
      <div className="space-y-2">
        <label className="text-xs text-gray-400">Test Edge Inference</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Try: 'What version?' or 'How many gardens?'"
            className="flex-1 text-xs bg-gray-800 text-gray-300 border border-gray-700 rounded px-3 py-2"
            onKeyDown={(e) => e.key === "Enter" && handleInfer()}
          />
          <button
            onClick={handleInfer}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded transition-colors"
          >
            Infer
          </button>
        </div>
      </div>

      {/* Cosine Test */}
      <div>
        <button
          onClick={handleCosineTest}
          className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
        >
          Test Cosine Similarity
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="p-3 rounded-lg bg-black/30 border border-gray-700">
          <p className="text-xs text-gray-300">{result}</p>
        </div>
      )}

      {/* Stats */}
      <div className="text-[10px] text-gray-500 font-mono">
        {getStats()}
      </div>
    </div>
  );
}

export default function PWAAppPage() {
  return (
    <AuthProvider>
      <WASMProvider>
      <section className="container-site py-12">
        {/* Hero */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white mb-2">WhiteMagic PWA</h1>
          <p className="text-gray-400 text-sm">
            Local-first agent governance and metacognition substrate — runs entirely in your browser
          </p>
        </div>

        {/* WASM Demo */}
        <div className="mb-8 rounded-xl border border-purple-500/20 bg-black/30">
          <div className="p-3 border-b border-purple-500/20">
            <h2 className="text-sm font-medium text-white">WASM Runtime Demo</h2>
          </div>
          <WASMDemo />
        </div>

        {/* SQLite OPFS Demo */}
        <div className="mb-8 rounded-xl border border-blue-500/20 bg-black/30">
          <div className="p-3 border-b border-blue-500/20">
            <h2 className="text-sm font-medium text-white">SQLite OPFS — Browser Memory Storage</h2>
          </div>
          <SQLiteOPFSDemo />
        </div>

        {/* ONNX Embedding Demo */}
        <div className="mb-8 rounded-xl border border-green-500/20 bg-black/30">
          <div className="p-3 border-b border-green-500/20">
            <h2 className="text-sm font-medium text-white">ONNX Embedding — Client-Side Semantic Vectors</h2>
          </div>
          <ONNXEmbeddingDemo />
        </div>

        {/* Feature Cards */}
        <div className="mb-12 grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={Shield}
            title="100% Local"
            desc="Zero network calls for memory or governance. Your data never leaves your device."
          />
          <FeatureCard
            icon={Database}
            title="SQLite WASM + OPFS"
            desc="Persistent storage using SQLite compiled to WASM, backed by Origin Private File System."
          />
          <FeatureCard
            icon={Zap}
            title="WASM Accelerated"
            desc="Rust core compiled to WebAssembly — 10-100x faster than JavaScript."
          />
          <FeatureCard
            icon={Globe}
            title="Blank Canvas"
            desc="No preloaded personality. Bring your own agent or build from scratch."
          />
          <FeatureCard
            icon={Key}
            title="Encrypted Keys"
            desc="LLM API keys encrypted with WebCrypto AES-GCM, stored in IndexedDB."
          />
          <FeatureCard
            icon={Play}
            title="Live Demo Above"
            desc="The WASM runtime is running right now — try the inference and cosine tests."
          />
        </div>

        {/* Architecture */}
        <div className="rounded-2xl border border-border bg-surface-alt p-8">
          <h3 className="mb-4 font-head text-xl font-semibold text-ink">
            Architecture
          </h3>
          <pre className="text-xs text-muted leading-relaxed overflow-x-auto">
{`┌────────────────────────────────────────────────────────────┐
│  Browser Runtime (PWA)                                      │
│                                                             │
│  @whitemagic/sdk                                            │
│    ↓ LocalTransport                                         │
│  whitemagic_rust.wasm (178KB)                               │
│    ├─ EdgeEngine (inference rules)                          │
│    ├─ cosine_similarity (vector math)                       │
│    ├─ batch_similarity (top-k search)                       │
│    └─ text_search (substring matching)                      │
│                                                             │
│  SQLite OPFS (sql.js + Origin Private File System)          │
│    ├─ memories table (content, garden, type, coords)        │
│    ├─ associations table (source, target, weight)           │
│    ├─ sync_log table (pending server reconciliation)        │
│    └─ Persistent across reloads via OPFS                    │
│                                                             │
│  Next: ONNX embedding model for browser-side vectors        │
└────────────────────────────────────────────────────────────┘`}
          </pre>
          <div className="mt-4 flex gap-3">
            <a
              href="/dashboard"
              className="btn-primary inline-flex items-center gap-2"
            >
              Open Dashboard
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="/galaxy"
              className="btn-secondary inline-flex items-center gap-2"
            >
              Live Galaxy
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </section>
      <PWAInstallPrompt />
    </WASMProvider>
    </AuthProvider>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: typeof Shield;
  title: string;
  desc: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <Icon className="mb-3 h-5 w-5 text-lavender" />
      <h3 className="mb-2 font-head text-base font-semibold text-ink">{title}</h3>
      <p className="text-sm leading-relaxed text-muted">{desc}</p>
    </div>
  );
}
