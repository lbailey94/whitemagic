import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

interface SphereNode {
  id: string;
  label: string;
  color: string;
  source: string;
  token_count: number;
  content_preview?: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

interface ClusterNode {
  id: string;
  cluster_id: number;
  title: string;
  keywords: string[];
  token_count: number;
  source_chunks: string[];
  average_similarity: number;
}

let sphereCache: SphereNode[] | null = null;
let clusterCache: ClusterNode[] | null = null;

function loadSphereNodes(): SphereNode[] {
  if (sphereCache) return sphereCache;
  const raw = fs.readFileSync(
    path.join(process.cwd(), "public", "sphere-nodes.json"),
    "utf-8",
  );
  sphereCache = (JSON.parse(raw) as { nodes: SphereNode[] }).nodes;
  return sphereCache!;
}

function loadClusters(): ClusterNode[] {
  if (clusterCache) return clusterCache;
  const raw = fs.readFileSync(
    path.join(process.cwd(), "public", "consolidated_synthesized.jsonl"),
    "utf-8",
  );
  clusterCache = raw
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as ClusterNode);
  return clusterCache!;
}

function searchClusters(query: string, limit: number) {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const clusters = loadClusters();

  const scored = clusters
    .map((c) => {
      let score = 0;
      const text = `${c.title} ${c.keywords.join(" ")}`.toLowerCase();
      for (const term of terms) {
        const regex = new RegExp(
          term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
          "gi",
        );
        const matches = text.match(regex);
        if (matches) score += matches.length * 10;
        if (text.includes(term)) score += 5;
      }
      return { cluster: c, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return scored.map((s) => s.cluster);
}

function searchNodes(query: string, limit: number) {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const nodes = loadSphereNodes();

  const scored = nodes
    .map((n) => {
      let score = 0;
      const text = (n.content_preview || "").toLowerCase();
      for (const term of terms) {
        if (text.includes(term)) score += 10;
      }
      return { node: n, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return scored.map((s) => s.node);
}

export async function POST(request: Request) {
  let body: { question?: string; mode?: string; limit?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    );
  }

  const question = body.question?.trim();
  if (!question) {
    return NextResponse.json(
      { error: "Missing 'question' field" },
      { status: 400 },
    );
  }

  const mode = body.mode || "ask";
  const limit = Math.min(body.limit || 5, 10);

  // Search both cluster (semantic) and node (preview) layers
  const clusterResults = searchClusters(question, limit);
  const nodeResults = searchNodes(question, limit);

  // Determine epistemic posture based on result quality
  const hasStrongResults =
    clusterResults.length >= 3 || nodeResults.length >= 5;

  // Build Aria-formatted response
  const sources = clusterResults.slice(0, 3).map((c) => ({
    cluster_id: c.cluster_id,
    title: c.title,
    keywords: c.keywords,
    confidence: hasStrongResults ? "high" : "moderate",
  }));

  const previews = nodeResults.slice(0, 5).map((n) => ({
    id: n.id,
    source: n.source,
    preview: n.content_preview || "",
  }));

  const response = {
    question,
    mode,
    epistemic_tag: hasStrongResults ? "Proven" : "Promising",
    answer: hasStrongResults
      ? `I found ${clusterResults.length} relevant knowledge clusters and ${nodeResults.length} supporting fragments for your question.`
      : `I found limited direct matches. Here's what's available — treat this as preliminary.`,
    sources,
    fragments: previews,
    cluster_count: clusterResults.length,
    node_count: nodeResults.length,
    timestamp: new Date().toISOString(),
  };

  return NextResponse.json(response);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const question = searchParams.get("q")?.trim();

  if (!question) {
    return NextResponse.json(
      { mode: "ask", status: "ready", description: "Aria Ask endpoint. POST a JSON body with 'question' field." },
    );
  }

  // Reuse POST logic for GET convenience
  const body = { question, mode: "ask", limit: 5 };
  const req = new Request(request.url, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return POST(req);
}
