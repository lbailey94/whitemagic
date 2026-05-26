"use client";

import { useState } from "react";
import { Search, Loader2, Hash, Link2, Database } from "lucide-react";

interface SearchResult {
  id: string;
  source: string;
  score: number;
  token_count: number;
  preview: string;
  label?: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

interface ClusterMatch {
  id: number;
  title: string;
  keywords: string[];
  chunk_count: number;
  score: number;
}

const SOURCE_COLORS: Record<string, string> = {
  library: "#60a5fa",
  conversations: "#4ade80",
  research: "#fb923c",
};

const MAX_PREVIEW_CHARS = 280;

function truncatePreview(text: string): string {
  if (!text) return "";
  if (text.length <= MAX_PREVIEW_CHARS) return text;
  return text.slice(0, MAX_PREVIEW_CHARS).replace(/\s+\S*$/, "") + "\u2026";
}

export function SemanticSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [clusters, setClusters] = useState<ClusterMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [backend, setBackend] = useState<string>("");

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(
        `/api/search?q=${encodeURIComponent(query.trim())}&limit=10`,
      );
      const data = await res.json();
      setResults(data.results || []);
      setClusters(data.clusters || []);
      setBackend(data.backend || "keyword");
    } catch {
      setResults([]);
      setClusters([]);
    }
    setLoading(false);
  }

  return (
    <div className="mb-8">
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search 10,768 knowledge nodes..."
            className="w-full rounded-xl border border-border bg-surface py-2.5 pl-10 pr-4 font-body text-fg placeholder:text-dim focus:border-lavender focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-lavender px-5 py-2.5 font-mono text-sm text-white transition hover:bg-lavender-dark disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </form>

      {searched && !loading && (
        <div className="mt-3 flex items-center gap-2 font-mono text-[10px] text-dim">
          <Database className="h-3 w-3" />
          <span>{backend}</span>
          {results.length > 0 && (
            <>
              <span>·</span>
              <span>{results.length} results</span>
            </>
          )}
          {clusters.length > 0 && (
            <>
              <span>·</span>
              <span>{clusters.length} clusters</span>
            </>
          )}
        </div>
      )}

      {searched && results.length === 0 && !loading && (
        <p className="mt-4 text-sm text-dim">No results found.</p>
      )}

      {clusters.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {clusters.map((c) => (
            <span
              key={c.id}
              className="inline-flex items-center gap-1 rounded-full border border-lavender/30 bg-lavender/10 px-2.5 py-1 font-mono text-[10px] text-lavender"
            >
              <Hash className="h-2.5 w-2.5" />
              {c.title}
              <span className="text-dim">({c.chunk_count})</span>
            </span>
          ))}
        </div>
      )}

      {results.length > 0 && (
        <ul className="mt-4 space-y-3">
          {results.map((r) => (
            <li
              key={r.id}
              className="rounded-xl border border-border bg-surface p-4 transition hover:border-lavender"
            >
              <div className="mb-2 flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: SOURCE_COLORS[r.source] || "#888" }}
                />
                <span className="font-mono uppercase tracking-wider text-lavender">
                  {r.source}
                </span>
                <span className="text-dim">·</span>
                <span className="font-mono text-dim">
                  {r.token_count.toLocaleString()} tokens
                </span>
                <span className="text-dim">·</span>
                <span className="font-mono text-dim">
                  score: {typeof r.score === "number" ? r.score.toFixed(0) : r.score}
                </span>
                {r.links?.length > 0 && (
                  <>
                    <span className="text-dim">·</span>
                    <span className="inline-flex items-center gap-1 font-mono text-dim">
                      <Link2 className="h-2.5 w-2.5" />
                      {r.links.length}
                    </span>
                  </>
                )}
              </div>
              {r.label && (
                <p className="mb-1 font-mono text-xs font-semibold text-ink">
                  {r.label}
                </p>
              )}
              <p className="text-sm leading-relaxed text-fg">
                {truncatePreview(r.preview)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
