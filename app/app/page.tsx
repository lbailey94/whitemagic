"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";

interface WasmExports {
  MemoryStore: new () => any;
  DharmaEngine: new () => any;
  KarmaLedger: new () => any;
  EdgeEngine: new () => any;
  gnosis_snapshot: (s: any, k: any, d: any, e: any) => any;
  wasm_ready: () => boolean;
  wasm_version: () => string;
  cosine_similarity: (a: string, b: string) => number;
  default: (input?: any) => Promise<any>;
}

interface MemoryRecord {
  id: string;
  title: string;
  content: string;
  tags: string[];
  importance: number;
  memory_type: string;
  created_at: string;
  updated_at: string;
}

interface GnosisData {
  memory_count: number;
  karma_balance: number;
  karma_entries: number;
  dharma_rules: number;
  edge_queries: number;
  edge_local: number;
  edge_tokens_saved: number;
  maturity_stage: string;
}

type Tab = "memories" | "create" | "governance" | "karma" | "gnosis";

export default function AppPage() {
  const [wasmLoaded, setWasmLoaded] = useState(false);
  const [wasmVersion, setWasmVersion] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [gnosis, setGnosis] = useState<GnosisData | null>(null);
  const [karmaBalance, setKarmaBalance] = useState(0);
  const [karmaEntries, setKarmaEntries] = useState<any[]>([]);
  const [dharmaRules, setDharmaRules] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("memories");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [privacyBytes, setPrivacyBytes] = useState(0);

  const storeRef = useRef<any>(null);
  const dharmaRef = useRef<any>(null);
  const karmaRef = useRef<any>(null);
  const engineRef = useRef<any>(null);
  const wasmRef = useRef<any>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [dharmaText, setDharmaText] = useState("");
  const [dharmaResult, setDharmaResult] = useState<any>(null);
  const [karmaAction, setKarmaAction] = useState("");
  const [karmaDelta, setKarmaDelta] = useState("1");
  const [karmaDesc, setKarmaDesc] = useState("");

  useEffect(() => {
    async function loadWasm() {
      try {
        const mod = await import("../../public/wasm/whitemagic_rust.js");
        await mod.default();
        const wasm = mod as unknown as WasmExports;
        wasmRef.current = wasm;

        const store = new wasm.MemoryStore();
        const dharma = new wasm.DharmaEngine();
        const karma = new wasm.KarmaLedger();
        const engine = new wasm.EdgeEngine();

        storeRef.current = store;
        dharmaRef.current = dharma;
        karmaRef.current = karma;
        engineRef.current = engine;

        try {
          const count = await store.hydrate();
          setHydrated(true);
          if (count > 0) refreshMemories();
        } catch {
          // IndexedDB might not be available yet
        }

        setWasmVersion(wasm.wasm_version());
        setWasmLoaded(true);
        refreshAll();
      } catch (err) {
        console.error("Failed to load WASM:", err);
      }
    }
    loadWasm();
  }, []);

  const refreshMemories = useCallback(() => {
    if (!storeRef.current) return;
    const list = JSON.parse(storeRef.current.list());
    setMemories(list);
  }, []);

  const refreshGnosis = useCallback(() => {
    if (!wasmRef.current || !storeRef.current || !karmaRef.current || !dharmaRef.current || !engineRef.current) return;
    const snap = wasmRef.current.gnosis_snapshot(
      storeRef.current,
      karmaRef.current,
      dharmaRef.current,
      engineRef.current,
    );
    const data = JSON.parse(snap.to_json());
    setGnosis(data);
  }, []);

  const refreshKarma = useCallback(() => {
    if (!karmaRef.current) return;
    setKarmaBalance(karmaRef.current.balance());
    setKarmaEntries(JSON.parse(karmaRef.current.recent_json(10)));
  }, []);

  const refreshDharma = useCallback(() => {
    if (!dharmaRef.current) return;
    setDharmaRules(JSON.parse(dharmaRef.current.list_rules()));
  }, []);

  const refreshAll = useCallback(() => {
    refreshMemories();
    refreshGnosis();
    refreshKarma();
    refreshDharma();
  }, [refreshMemories, refreshGnosis, refreshKarma, refreshDharma]);

  const handleCreate = async () => {
    if (!storeRef.current || !title.trim()) return;
    const tagsArr = tags.split(",").map((t) => t.trim()).filter(Boolean);
    const id = storeRef.current.create(title, content, JSON.stringify(tagsArr));
    try {
      await storeRef.current.persist_one(id);
    } catch {}
    setPrivacyBytes((b) => b);
    setTitle("");
    setContent("");
    setTags("");
    refreshAll();
  };

  const handleDelete = async (id: string) => {
    if (!storeRef.current) return;
    storeRef.current.delete(id);
    try {
      await storeRef.current.delete_persisted(id);
    } catch {}
    refreshAll();
  };

  const handleSearch = () => {
    if (!storeRef.current || !searchQuery.trim()) return;
    const results = JSON.parse(storeRef.current.search(searchQuery));
    setSearchResults(results);
  };

  const handleDharmaEval = () => {
    if (!dharmaRef.current || !dharmaText.trim()) return;
    const result = dharmaRef.current.evaluate(dharmaText);
    setDharmaResult({
      allowed: result.allowed,
      matched_rule: result.matched_rule,
      message: result.message,
      evaluated_rules: result.evaluated_rules,
    });
  };

  const handleKarmaRecord = () => {
    if (!karmaRef.current || !karmaAction.trim()) return;
    karmaRef.current.record(karmaAction, parseFloat(karmaDelta) || 0, karmaDesc);
    refreshKarma();
    refreshGnosis();
    setKarmaAction("");
    setKarmaDelta("1");
    setKarmaDesc("");
  };

  const handlePersist = async () => {
    if (!storeRef.current) return;
    try {
      await storeRef.current.persist();
    } catch {}
  };

  const handleExport = () => {
    if (!storeRef.current) return;
    const data = storeRef.current.export_json();
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `whitemagic-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!wasmLoaded) {
    return (
      <main className="relative z-10 flex min-h-screen flex-col items-center justify-center">
        <div className="triquetra-breathing text-lavender">
          <svg viewBox="0 0 200 200" className="h-32 w-32">
            <g className="triquetra-spin">
              <circle cx="100" cy="76.9" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
              <circle cx="80" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
              <circle cx="120" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
            </g>
          </svg>
        </div>
        <p className="mt-4 font-mono text-xs uppercase tracking-widest text-dim">
          Loading WASM module...
        </p>
        <p className="mt-1 font-zh text-xs text-dim/50">正在加載本地操作系統</p>
      </main>
    );
  }

  const tabs: { id: Tab; label: string; zh: string }[] = [
    { id: "memories", label: "Memories", zh: "記憶" },
    { id: "create", label: "Create", zh: "創建" },
    { id: "governance", label: "Governance", zh: "治理" },
    { id: "karma", label: "Karma", zh: "業力" },
    { id: "gnosis", label: "Gnosis", zh: "自省" },
  ];

  return (
    <main className="relative z-10 min-h-screen px-4 py-6">
      {/* Header */}
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-zh text-sm text-dim">白術 · 本地操作系統</p>
            <h1 className="font-head text-xl font-bold text-ink">
              WhiteMagic <span className="text-dim font-normal">Local OS</span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] text-dim/60">
              v{wasmVersion} · {hydrated ? "hydrated" : "fresh"}
            </span>
            <ThemeToggle />
          </div>
        </div>

        {/* Privacy indicator */}
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-border-light bg-surface/60 px-3 py-1.5">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          <span className="font-mono text-[10px] text-dim">
            {privacyBytes} bytes sent · 全本地運行 · Zero network calls
          </span>
        </div>

        {/* Gnosis bar */}
        {gnosis && (
          <div className="mt-3 flex flex-wrap gap-4 rounded-lg border border-border-light bg-surface/40 px-4 py-2">
            <Stat label="Memories" zh="記憶" value={gnosis.memory_count} />
            <Stat label="Karma" zh="業力" value={gnosis.karma_balance.toFixed(2)} />
            <Stat label="Rules" zh="規則" value={gnosis.dharma_rules} />
            <Stat label="Stage" zh="階段" value={gnosis.maturity_stage} />
            <Stat label="Edge queries" zh="邊緣查詢" value={gnosis.edge_queries} />
            <Stat label="Tokens saved" zh="節省令牌" value={gnosis.edge_tokens_saved} />
          </div>
        )}

        {/* Tabs */}
        <div className="mt-4 flex gap-1 border-b border-border-light">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 font-mono text-[11px] uppercase tracking-wider transition ${
                activeTab === tab.id
                  ? "border-b-2 border-lavender text-lavender"
                  : "text-dim hover:text-fg"
              }`}
            >
              <span className="font-zh text-[10px] text-dim/50 mr-1">{tab.zh}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="mt-4 pb-12">
          {activeTab === "memories" && (
            <div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Search memories... 搜索記憶"
                  className="flex-1 rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg placeholder:text-dim/40 focus:border-lavender focus:outline-none"
                />
                <button
                  onClick={handleSearch}
                  className="rounded-lg border border-border-light bg-surface/60 px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender"
                >
                  Search
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="mt-3">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60 mb-2">
                    Search results 搜索結果 ({searchResults.length})
                  </p>
                  {searchResults.map((r) => (
                    <div key={r.id} className="rounded-lg border border-border-light bg-surface/40 p-3 mb-2">
                      <p className="font-head text-sm font-bold text-ink">{r.title}</p>
                      <p className="font-mono text-xs text-dim mt-1">{r.snippet}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 flex items-center justify-between">
                <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  All memories 全部記憶 ({memories.length})
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={handlePersist}
                    className="rounded-lg border border-border-light bg-surface/60 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender"
                  >
                    Persist
                  </button>
                  <button
                    onClick={handleExport}
                    className="rounded-lg border border-border-light bg-surface/60 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender"
                  >
                    Export
                  </button>
                </div>
              </div>

              <div className="mt-2 space-y-2">
                {memories.length === 0 ? (
                  <p className="font-mono text-xs text-dim/40 py-8 text-center">
                    No memories yet. Create one to begin. 尚無記憶，創建一個開始吧。
                  </p>
                ) : (
                  memories.map((m) => (
                    <div
                      key={m.id}
                      className="rounded-lg border border-border-light bg-surface/40 p-3 group"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-head text-sm font-bold text-ink">{m.title}</p>
                          {m.tags && m.tags.length > 0 && (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {m.tags.map((t) => (
                                <span
                                  key={t}
                                  className="rounded bg-lavender/10 px-1.5 py-0.5 font-mono text-[9px] text-lavender/80"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                          <p className="font-mono text-[10px] text-dim/50 mt-1">
                            {m.id} · {m.importance.toFixed(2)} · {m.created_at.slice(0, 10)}
                          </p>
                        </div>
                        <button
                          onClick={() => handleDelete(m.id)}
                          className="ml-2 font-mono text-[10px] text-dim/40 opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === "create" && (
            <div className="space-y-3">
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Title 標題
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg focus:border-lavender focus:outline-none"
                />
              </div>
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Content 內容
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={6}
                  className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg focus:border-lavender focus:outline-none"
                />
              </div>
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Tags 標籤 (comma-separated)
                </label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="personal, work, research"
                  className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg placeholder:text-dim/40 focus:border-lavender focus:outline-none"
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={!title.trim()}
                className="rounded-lg border border-lavender bg-lavender/10 px-6 py-2 font-mono text-[10px] uppercase tracking-wider text-lavender transition hover:bg-lavender/20 disabled:opacity-40"
              >
                Create Memory 創建記憶
              </button>
            </div>
          )}

          {activeTab === "governance" && (
            <div className="space-y-4">
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Evaluate text 評估文本
                </label>
                <textarea
                  value={dharmaText}
                  onChange={(e) => setDharmaText(e.target.value)}
                  rows={3}
                  placeholder="Enter text to evaluate against Dharma rules..."
                  className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg placeholder:text-dim/40 focus:border-lavender focus:outline-none"
                />
                <button
                  onClick={handleDharmaEval}
                  disabled={!dharmaText.trim()}
                  className="mt-2 rounded-lg border border-border-light bg-surface/60 px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender disabled:opacity-40"
                >
                  Evaluate 評估
                </button>
              </div>

              {dharmaResult && (
                <div className={`rounded-lg border p-4 ${dharmaResult.allowed ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"}`}>
                  <p className="font-mono text-sm">
                    <span className={dharmaResult.allowed ? "text-green-400" : "text-red-400"}>
                      {dharmaResult.allowed ? "✓ Allowed" : "✕ Blocked"}
                    </span>
                    {dharmaResult.matched_rule && (
                      <span className="text-dim"> · rule: {dharmaResult.matched_rule}</span>
                    )}
                  </p>
                  {dharmaResult.message && (
                    <p className="mt-2 font-mono text-xs text-dim">{dharmaResult.message}</p>
                  )}
                  <p className="mt-1 font-mono text-[10px] text-dim/50">
                    Evaluated {dharmaResult.evaluated_rules} rules
                  </p>
                </div>
              )}

              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60 mb-2">
                  Active rules 活躍規則 ({dharmaRules.length})
                </p>
                <div className="space-y-1">
                  {dharmaRules.map((r) => (
                    <div key={r.id} className="rounded border border-border-light bg-surface/40 px-3 py-2">
                      <p className="font-mono text-xs text-fg">
                        <span className={`mr-2 ${r.action === "block" ? "text-red-400" : r.action === "warn" ? "text-yellow-400" : "text-green-400"}`}>
                          [{r.action}]
                        </span>
                        {r.id}
                      </p>
                      <p className="font-mono text-[10px] text-dim/50 mt-0.5">{r.pattern}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "karma" && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border-light bg-surface/40 p-4">
                <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Current balance 當前餘額
                </p>
                <p className="font-head text-2xl font-bold text-lavender mt-1">
                  {karmaBalance.toFixed(2)}
                </p>
              </div>

              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                  Action 行動
                </label>
                <input
                  type="text"
                  value={karmaAction}
                  onChange={(e) => setKarmaAction(e.target.value)}
                  placeholder="help_user, research, create_memory..."
                  className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg placeholder:text-dim/40 focus:border-lavender focus:outline-none"
                />
              </div>
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                    Delta 變化
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={karmaDelta}
                    onChange={(e) => setKarmaDelta(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg focus:border-lavender focus:outline-none"
                  />
                </div>
                <div className="flex-1">
                  <label className="font-mono text-[10px] uppercase tracking-widest text-dim/60">
                    Description 描述
                  </label>
                  <input
                    type="text"
                    value={karmaDesc}
                    onChange={(e) => setKarmaDesc(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border-light bg-surface/60 px-3 py-2 font-mono text-sm text-fg focus:border-lavender focus:outline-none"
                  />
                </div>
              </div>
              <button
                onClick={handleKarmaRecord}
                disabled={!karmaAction.trim()}
                className="rounded-lg border border-lavender bg-lavender/10 px-6 py-2 font-mono text-[10px] uppercase tracking-wider text-lavender transition hover:bg-lavender/20 disabled:opacity-40"
              >
                Record Karma 記錄業力
              </button>

              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60 mb-2">
                  Recent entries 最近記錄 ({karmaEntries.length})
                </p>
                <div className="space-y-1">
                  {karmaEntries.map((e) => (
                    <div key={e.id} className="rounded border border-border-light bg-surface/40 px-3 py-2">
                      <div className="flex items-center justify-between">
                        <p className="font-mono text-xs text-fg">{e.action}</p>
                        <p className={`font-mono text-xs ${e.delta >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {e.delta >= 0 ? "+" : ""}{e.delta.toFixed(2)}
                        </p>
                      </div>
                      {e.description && (
                        <p className="font-mono text-[10px] text-dim/50 mt-0.5">{e.description}</p>
                      )}
                      <p className="font-mono text-[9px] text-dim/40 mt-0.5">{e.id} · {e.timestamp.slice(0, 19)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "gnosis" && gnosis && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border-light bg-surface/40 p-6">
                <p className="font-zh text-sm text-dim mb-1">自省快照</p>
                <p className="font-mono text-[10px] uppercase tracking-widest text-dim/60 mb-4">
                  Gnosis Snapshot — System Self-Awareness
                </p>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                  <GnosisStat label="Memory Count" zh="記憶數量" value={gnosis.memory_count} />
                  <GnosisStat label="Karma Balance" zh="業力餘額" value={gnosis.karma_balance.toFixed(2)} />
                  <GnosisStat label="Karma Entries" zh="業力記錄" value={gnosis.karma_entries} />
                  <GnosisStat label="Dharma Rules" zh="法則數量" value={gnosis.dharma_rules} />
                  <GnosisStat label="Edge Queries" zh="邊緣查詢" value={gnosis.edge_queries} />
                  <GnosisStat label="Local Resolved" zh="本地解決" value={gnosis.edge_local} />
                  <GnosisStat label="Tokens Saved" zh="節省令牌" value={gnosis.edge_tokens_saved} />
                  <GnosisStat label="Maturity Stage" zh="成熟階段" value={gnosis.maturity_stage} />
                </div>
              </div>

              <button
                onClick={refreshGnosis}
                className="rounded-lg border border-border-light bg-surface/60 px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender"
              >
                Refresh Gnosis 刷新自省
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Back link */}
      <div className="fixed bottom-4 left-4 z-50">
        <a
          href="/"
          className="font-mono text-[10px] uppercase tracking-wide text-dim/60 transition hover:text-lavender"
        >
          <span className="font-zh text-[10px] text-dim/40 mr-1">← 返回</span>
          Back to sigil
        </a>
      </div>
    </main>
  );
}

function Stat({ label, zh, value }: { label: string; zh: string; value: string | number }) {
  return (
    <div>
      <p className="font-mono text-[9px] uppercase tracking-widest text-dim/50">
        <span className="font-zh mr-1">{zh}</span>
        {label}
      </p>
      <p className="font-head text-sm font-bold text-ink">{value}</p>
    </div>
  );
}

function GnosisStat({ label, zh, value }: { label: string; zh: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border-light bg-surface/30 p-3">
      <p className="font-mono text-[9px] uppercase tracking-widest text-dim/50">
        <span className="font-zh mr-1">{zh}</span>
        {label}
      </p>
      <p className="font-head text-lg font-bold text-lavender mt-1">{value}</p>
    </div>
  );
}
