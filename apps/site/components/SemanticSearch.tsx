"use client";

import { useState } from "react";

interface SearchResult {
  id: string;
  source: string;
  score: number;
  token_count: number;
  preview: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

export function SemanticSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

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
    } catch {
      setResults([]);
    }
    setLoading(false);
  }

  const sourceColors: Record<string, string> = {
    library: "#60a5fa",
    conversations: "#4ade80",
    research: "#fb923c",
  };

  return (
    <div className="mb-8">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search 10,768 knowledge nodes..."
          className="flex-1 rounded-xl border border-border bg-surface px-4 py-2.5 font-body text-fg placeholder:text-dim focus:border-lavender focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-lavender px-5 py-2.5 font-mono text-sm text-white transition hover:bg-lavender-dark disabled:opacity-50"
        >
          {loading ? "..." : "Search"}
        </button>
      </form>

      {searched && results.length === 0 && !loading && (
        <p className="mt-4 text-sm text-dim">No results found.</p>
      )}

      {results.length > 0 && (
        <ul className="mt-4 space-y-3">
          {results.map((r) => (
            <li
              key={r.id}
              className="rounded-xl border border-border bg-surface p-4 transition hover:border-lavender"
            >
              <div className="mb-1 flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: sourceColors[r.source] || "#888" }}
                />
                <span className="font-mono uppercase tracking-wider text-lavender">
                  {r.source}
                </span>
                <span className="text-dim">·</span>
                <span className="font-mono text-dim">
                  {r.token_count} tokens
                </span>
                <span className="text-dim">·</span>
                <span className="font-mono text-dim">
                  sim: {r.score.toFixed(0)}
                </span>
              </div>
              <p className="text-sm text-fg">{r.preview}</p>
              {r.links.length > 0 && (
                <p className="mt-1 font-mono text-xs text-dim">
                  {r.links.length} related nodes
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
