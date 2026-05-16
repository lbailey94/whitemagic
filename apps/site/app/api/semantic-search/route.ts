import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Semantic Search API — CODEX-powered with graceful degradation
 *
 * POST /api/semantic-search
 * Body: { query: string, limit?: number, semantic?: boolean }
 *
 * Routes to CODEX serve (Axum) when available, falls back to
 * TF-IDF keyword search over sphere-nodes + cluster index.
 */

interface SphereNode {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  color: string;
  source: string;
  token_count: number;
  content_preview?: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

interface SphereData {
  version: string;
  nodes: SphereNode[];
}

interface ClusterNode {
  id: string;
  cluster_id: number;
  title: string;
  keywords: string[];
  token_count: number;
  source_chunks: string[];
  average_similarity: number;
  original_title?: string;
  labeled_by?: string;
}

const CODEX_SERVE_URL = process.env.CODEX_SERVE_URL || "http://127.0.0.1:8080";

let cachedData: SphereData | null = null;
let clusterCache: ClusterNode[] | null = null;

function loadSphereData(): SphereData | null {
  if (cachedData) return cachedData;
  try {
    const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
    cachedData = JSON.parse(fs.readFileSync(fp, "utf-8")) as SphereData;
    return cachedData;
  } catch {
    return null;
  }
}

function loadClusters(): ClusterNode[] {
  if (clusterCache) return clusterCache;
  const relabeled = path.join(
    process.cwd(),
    "public",
    "consolidated_relabeled.jsonl",
  );
  const fallback = path.join(
    process.cwd(),
    "public",
    "consolidated_synthesized.jsonl",
  );
  const src = fs.existsSync(relabeled) ? relabeled : fallback;
  clusterCache = fs
    .readFileSync(src, "utf-8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as ClusterNode);
  return clusterCache!;
}

// --- CODEX Bridge ---

interface CodexResult {
  id: string;
  score: number;
  source: string;
  tokens: number;
  preview: string;
}

async function queryCodex(
  query: string,
  limit: number,
  semantic: boolean,
): Promise<CodexResult[] | null> {
  try {
    const res = await fetch(`${CODEX_SERVE_URL}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit, semantic }),
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    return (await res.json()) as CodexResult[];
  } catch {
    return null;
  }
}

// --- Keyword Fallback with TF-IDF ---

function keywordSearch(
  query: string,
  limit: number,
): Array<{
  id: string;
  source: string;
  score: number;
  tokens: number;
  preview: string;
  label: string;
}> {
  const data = loadSphereData();
  if (!data) return [];

  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const docCount = data.nodes.length;
  const termDocFreq = new Map<string, number>();

  for (const node of data.nodes) {
    const text = (node.content_preview || "").toLowerCase();
    const label = (node.label || "").toLowerCase();
    for (const term of terms) {
      if (text.includes(term) || label.includes(term)) {
        termDocFreq.set(term, (termDocFreq.get(term) || 0) + 1);
      }
    }
  }

  const scored = data.nodes
    .map((node) => {
      let score = 0;
      const text = (node.content_preview || "").toLowerCase();
      const label = (node.label || "").toLowerCase();

      for (const term of terms) {
        if (label.includes(term)) score += 20;
        const matches = text.match(
          new RegExp(
            term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
            "gi",
          ),
        );
        if (matches) {
          score += matches.length * 8;
          const df = termDocFreq.get(term) || 1;
          score += Math.log((docCount + 1) / (df + 1)) * 3;
        }
      }
      return { node, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => ({
      id: r.node.id,
      label: r.node.label,
      source: r.node.source,
      score: Math.round(r.score * 10) / 10,
      tokens: r.node.token_count,
      preview: r.node.content_preview || "",
    }));

  return scored;
}

function searchClusters(
  query: string,
  limit: number,
): Array<{
  cluster_id: number;
  title: string;
  keywords: string[];
  chunk_count: number;
  score: number;
}> {
  const clusters = loadClusters();
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);

  return clusters
    .map((c) => {
      let score = 0;
      const text = `${c.title} ${c.keywords.join(" ")}`.toLowerCase();
      for (const term of terms) {
        if (text.includes(term)) score += 15;
      }
      return { cluster: c, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => ({
      cluster_id: r.cluster.cluster_id,
      title: r.cluster.title,
      keywords: r.cluster.keywords,
      chunk_count: r.cluster.source_chunks.length,
      score: r.score,
    }));
}

// --- POST Handler ---

export async function POST(request: Request) {
  let body: { query?: string; limit?: number; semantic?: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    );
  }

  const query = body.query?.trim();
  if (!query) {
    return NextResponse.json(
      { error: "Missing 'query' field" },
      { status: 400 },
    );
  }

  const limit = Math.min(body.limit || 10, 50);
  const semantic = body.semantic !== false; // Default to true (semantic)
  let backend = "keyword-fallback";

  // Try CODEX first, fall back to keyword
  let codexResults: CodexResult[] | null = null;
  if (semantic) {
    codexResults = await queryCodex(query, limit, true);
    if (codexResults && codexResults.length > 0) {
      backend = "codex-semantic";
    }
  }

  const keywordResults = keywordSearch(query, limit);
  const clusterMatches = searchClusters(query, 3);

  // Prefer CODEX if available, merge with keyword as supplement
  const results = codexResults && codexResults.length > 0
    ? codexResults.map((r) => ({
        id: r.id,
        source: r.source,
        score: r.score,
        tokens: r.tokens,
        preview: r.preview,
      }))
    : keywordResults.map((r) => ({
        id: r.id,
        source: r.source,
        score: r.score,
        tokens: r.tokens,
        preview: r.preview,
        label: r.label,
      }));

  return NextResponse.json({
    query,
    backend,
    semantic_enabled: semantic,
    total_results: results.length,
    cluster_matches: clusterMatches.length,
    results,
    clusters: clusterMatches,
    deployment: backend === "codex-semantic"
      ? "CODEX Axum server (k-NN + embeddings)"
      : "Local keyword search (relabeled cluster index)",
    timestamp: new Date().toISOString(),
  });
}
