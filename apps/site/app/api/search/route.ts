import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

interface SphereNode {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
  source: string;
  token_count: number;
  links: Array<{ target: string; similarity: number; rank: number }>;
  content_preview?: string;
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

let cachedData: SphereData | null = null;
let clusterCache: ClusterNode[] | null = null;

function loadData(): SphereData | null {
  if (cachedData) return cachedData;
  try {
    const filePath = path.join(process.cwd(), "public", "sphere-nodes.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    cachedData = JSON.parse(raw) as SphereData;
    return cachedData;
  } catch {
    return null;
  }
}

function loadClusters(): ClusterNode[] {
  if (clusterCache) return clusterCache;
  const relabeledPath = path.join(
    process.cwd(),
    "public",
    "consolidated_relabeled.jsonl",
  );
  const fallbackPath = path.join(
    process.cwd(),
    "public",
    "consolidated_synthesized.jsonl",
  );
  const loadPath = fs.existsSync(relabeledPath) ? relabeledPath : fallbackPath;
  const raw = fs.readFileSync(loadPath, "utf-8");
  clusterCache = raw
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as ClusterNode);
  return clusterCache!;
}

function tfidfScoring(nodes: SphereNode[], terms: string[]): Map<string, number> {
  // Simplified TF-IDF: boost rare terms, penalize common ones
  const docCount = nodes.length;
  const termDocFreq = new Map<string, number>();

  // Count document frequency for each term
  for (const node of nodes) {
    const text = (node.content_preview || "").toLowerCase();
    for (const term of terms) {
      if (text.includes(term)) {
        termDocFreq.set(term, (termDocFreq.get(term) || 0) + 1);
      }
    }
  }

  // Score each node
  const scores = new Map<string, number>();
  for (const node of nodes) {
    let score = 0;
    const text = (node.content_preview || "").toLowerCase();
    const label = (node.label || "").toLowerCase();

    for (const term of terms) {
      // Title/label match = high weight
      if (label.includes(term)) score += 20;

      // Content preview matches
      const regex = new RegExp(
        term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
        "gi",
      );
      const matches = text.match(regex);
      if (matches) {
        // TF: count occurrences
        score += matches.length * 8;
        // IDF boost for rare terms
        const df = termDocFreq.get(term) || 1;
        const idf = Math.log((docCount + 1) / (df + 1));
        score += idf * 3;
      }
    }

    // Source diversity bonus
    if (node.source === "LIBRARY") score += 1;
    if (node.source === "RESEARCH") score += 2;

    scores.set(node.id, score);
  }

  return scores;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim().toLowerCase();
  const limit = Math.min(parseInt(searchParams.get("limit") || "10", 10), 50);
  const source = searchParams.get("source") || "";

  if (!q) {
    return NextResponse.json(
      { error: "Missing query parameter 'q'" },
      { status: 400 },
    );
  }

  const data = loadData();
  if (!data) {
    return NextResponse.json(
      { error: "Search index not available" },
      { status: 503 },
    );
  }

  const terms = q.split(/\s+/).filter(Boolean);

  // Filter by source if requested
  const candidateNodes = source
    ? data.nodes.filter((node) => node.source === source)
    : data.nodes;

  // TF-IDF scoring
  const scores = tfidfScoring(candidateNodes, terms);

  const results = candidateNodes
    .map((node) => ({
      node,
      score: scores.get(node.id) || 0,
    }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => ({
      id: r.node.id,
      label: r.node.label,
      source: r.node.source,
      score: r.score,
      token_count: r.node.token_count,
      preview: r.node.content_preview || "",
      links: r.node.links.slice(0, 3),
    }));

  // Also search clusters for relevant topics
  const clusters = loadClusters();
  const clusterResults = clusters
    .map((c) => {
      let cs = 0;
      const text = `${c.title} ${c.keywords.join(" ")}`.toLowerCase();
      for (const term of terms) {
        if (text.includes(term)) cs += 15;
      }
      return { cluster: c, score: cs };
    })
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  return NextResponse.json({
    query: q,
    backend: "TF-IDF keyword",
    total_results: results.length,
    cluster_matches: clusterResults.length,
    results,
    clusters: clusterResults.map((c) => ({
      id: c.cluster.cluster_id,
      title: c.cluster.title,
      keywords: c.cluster.keywords,
      chunk_count: c.cluster.source_chunks.length,
      score: c.score,
    })),
  });
}
