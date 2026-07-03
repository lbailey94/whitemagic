"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface LibraryFile {
  id: string;
  title: string;
  category: string;
  preview: string;
  size: number;
  ext: string;
}

interface LibraryManifest {
  total_files_manifest: number;
  total_size_manifest: number;
  categories: string[];
  results: LibraryFile[];
}

export default function LibraryPage() {
  const [manifest, setManifest] = useState<LibraryManifest | null>(null);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<LibraryFile | null>(null);
  const [content, setContent] = useState("");
  const [contentLoading, setContentLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (category) params.set("category", category);
    params.set("page", String(page));
    params.set("per_page", "30");

    setLoading(true);
    fetch(`/api/library?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setManifest(data);
        setTotalPages(data.total_pages || 1);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [category, query, page]);

  const openFile = (file: LibraryFile) => {
    setSelected(file);
    setContentLoading(true);
    setContent("");
    fetch(`/api/library?id=${encodeURIComponent(file.id)}`)
      .then((r) => r.json())
      .then((data) => {
        setContent(data.content || "");
        setContentLoading(false);
      })
      .catch(() => setContentLoading(false));
  };

  const formatSize = (bytes: number) => {
    if (bytes > 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
    if (bytes > 1_000) return `${(bytes / 1_000).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const categoryColors: Record<string, string> = {
    "AI and Intelligence": "bg-blue-500/10 text-blue-400",
    "Consciousness & Philosophy": "bg-purple-500/10 text-purple-400",
    "Ecology & Systems": "bg-green-500/10 text-green-400",
    "Economics & Governance": "bg-amber-500/10 text-amber-400",
    "Technology & Code": "bg-cyan-500/10 text-cyan-400",
    "Society & Culture": "bg-pink-500/10 text-pink-400",
    "History & Future": "bg-orange-500/10 text-orange-400",
    "General": "bg-slate-500/10 text-slate-400",
  };

  return (
    <main className="container-site py-16">
      <header className="mb-10">
        <p className="font-mono text-sm uppercase tracking-wider text-lavender">
          Library
        </p>
        <h1 className="mt-2 font-head text-4xl font-semibold text-ink">
          CODEX Research Library
        </h1>
        <p className="mt-3 max-w-prose text-lg text-muted">
          {manifest
            ? `${manifest.total_files_manifest} research files across ${manifest.categories.length} domains — indexed and searchable.`
            : "Loading..."}
        </p>
      </header>

      {/* Filters */}
      <div className="mb-8 flex flex-wrap gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
          placeholder="Search the library..."
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-ink placeholder:text-dim focus:border-lavender focus:outline-none"
        />
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-ink"
        >
          <option value="">All categories</option>
          {manifest?.categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* File list + detail split */}
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          {loading && (
            <p className="font-mono text-sm text-dim animate-pulse">
              Loading...
            </p>
          )}
          {manifest && manifest.results.length === 0 && (
            <p className="font-mono text-sm text-dim">
              No files match your filters.
            </p>
          )}
          <ul className="space-y-2">
            {manifest?.results.map((f) => (
              <li key={f.id}>
                <button
                  onClick={() => openFile(f)}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                    selected?.id === f.id
                      ? "border-lavender bg-lavender/5"
                      : "border-border bg-surface hover:border-muted"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-sm font-semibold text-ink">
                      {f.title}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] text-dim">
                      {formatSize(f.size)}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${categoryColors[f.category] || "bg-slate-500/10 text-slate-400"}`}
                    >
                      {f.category}
                    </span>
                    <span className="font-mono text-[10px] uppercase text-dim">
                      .{f.ext}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] leading-relaxed text-muted">
                    {f.preview.slice(0, 140)}...
                  </p>
                </button>
              </li>
            ))}
          </ul>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-md border border-border px-3 py-1 font-mono text-xs text-ink disabled:opacity-30"
              >
                Prev
              </button>
              <span className="font-mono text-xs text-dim">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-md border border-border px-3 py-1 font-mono text-xs text-ink disabled:opacity-30"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* File detail */}
        <div>
          {!selected && (
            <div className="flex h-64 items-center justify-center rounded-2xl border border-border bg-surface">
              <p className="font-mono text-sm text-dim">
                Select a file to preview
              </p>
            </div>
          )}
          {selected && (
            <div className="rounded-2xl border border-border bg-surface p-6">
              <h2 className="font-head text-xl font-semibold text-ink">
                {selected.title}
              </h2>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${categoryColors[selected.category] || ""}`}
                >
                  {selected.category}
                </span>
                <span className="font-mono text-xs text-dim">
                  {formatSize(selected.size)} · .{selected.ext}
                </span>
              </div>
              {contentLoading && (
                <p className="mt-4 font-mono text-sm text-dim animate-pulse">
                  Loading content...
                </p>
              )}
              {content && (
                <pre className="mt-4 max-h-[60vh] overflow-y-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-alt p-4 font-mono text-[11px] leading-relaxed text-ink">
                  {content}
                </pre>
              )}
              <div className="mt-4 flex items-center gap-3">
                <Link
                  href={`/library?id=${encodeURIComponent(selected.id)}`}
                  className="font-mono text-xs text-lavender hover:underline"
                >
                  permalink
                </Link>
                <Link
                  href="/essays"
                  className="font-mono text-xs text-muted hover:text-ink"
                >
                  back to essays
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
