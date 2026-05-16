import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Aria Oracle — Deep synthesis endpoint
 *
 * POST /api/aria/oracle
 * Body: { question: string, lenses?: string[], depth?: number }
 *
 * Searches across all knowledge layers (sphere nodes, clusters, LIBRARY)
 * and returns a multi-perspective oracle response with provenance.
 */

interface SphereNode {
  id: string;
  label: string;
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
  labeled_by?: string;
}

function loadSphere(): SphereNode[] {
  const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
  const raw = fs.readFileSync(fp, "utf-8");
  return (JSON.parse(raw) as { nodes: SphereNode[] }).nodes;
}

function loadClusters(): ClusterNode[] {
  const rp = path.join(process.cwd(), "public", "consolidated_relabeled.jsonl");
  const fp = fs.existsSync(rp)
    ? rp
    : path.join(process.cwd(), "public", "consolidated_synthesized.jsonl");
  return fs
    .readFileSync(fp, "utf-8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l) as ClusterNode);
}

function searchDeep(query: string, limit: number) {
  const nodes = loadSphere();
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);

  return nodes
    .map((n) => {
      let score = 0;
      const text = ((n.content_preview || "") + " " + (n.label || "")).toLowerCase();
      for (const term of terms) {
        if (text.includes(term)) score += 8;
      }
      if (n.source === "LIBRARY") score += 3;
      return { node: n, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function searchClustersDeep(query: string, limit: number) {
  const clusters = loadClusters();
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);

  return clusters
    .map((c) => {
      let score = 0;
      const text = `${c.title} ${c.keywords.join(" ")}`.toLowerCase();
      for (const term of terms) {
        if (text.includes(term)) score += 12;
      }
      if (c.labeled_by === "aria-phase2-synthesis") score += 5;
      return { cluster: c, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function wanderLinks(
  seedNodeId: string,
  maxSteps: number,
): Array<{ step: number; node: SphereNode; reason: string }> {
  const nodes = loadSphere();
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const visited = new Set<string>();
  const path: Array<{ step: number; node: SphereNode; reason: string }> = [];

  let current = nodeMap.get(seedNodeId);
  if (!current) return path;

  visited.add(current.id);
  path.push({ step: 0, node: current, reason: "seed" });

  for (let step = 1; step <= maxSteps; step++) {
    // Follow strongest unvisited link
    const links = (current.links || [])
      .filter((l) => l.similarity > 0.3)
      .sort((a, b) => b.similarity - a.similarity);

    let next: SphereNode | undefined;
    let linkReason = "";

    for (const link of links) {
      if (!visited.has(link.target)) {
        const candidate = nodeMap.get(link.target);
        if (candidate) {
          next = candidate;
          linkReason = `similarity ${link.similarity.toFixed(2)} (rank ${link.rank})`;
          break;
        }
      }
    }

    if (!next) break;

    visited.add(next.id);
    path.push({ step, node: next, reason: linkReason });
    current = next;
  }

  return path;
}

export async function POST(request: Request) {
  let body: {
    question?: string;
    mode?: "oracle" | "wander";
    lenses?: string[];
    seed?: string;
    depth?: number;
    steps?: number;
  };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const mode = body.mode || "oracle";

  if (mode === "wander") {
    const seed = body.seed || body.question;
    if (!seed) {
      return NextResponse.json(
        { error: "Missing 'seed' or 'question' for wander mode" },
        { status: 400 },
      );
    }

    // Find a seed node
    const results = searchDeep(seed, 1);
    if (results.length === 0) {
      return NextResponse.json(
        { mode: "wander", seed, path: [], error: "No seed node found for this topic" },
      );
    }

    const maxSteps = Math.min(body.steps || 8, 15);
    const path = wanderLinks(results[0].node.id, maxSteps);

    return NextResponse.json({
      mode: "wander",
      seed,
      seed_node: results[0].node.label,
      steps: path.length,
      path: path.map((p) => ({
        step: p.step,
        id: p.node.id,
        label: p.node.label,
        source: p.node.source,
        preview: p.node.content_preview || "",
        reason: p.reason,
      })),
      timestamp: new Date().toISOString(),
    });
  }

  // Oracle mode
  const question = body.question?.trim();
  if (!question) {
    return NextResponse.json(
      { error: "Missing 'question' field" },
      { status: 400 },
    );
  }

  const depth = Math.min(body.depth || 3, 5);
  const nodeResults = searchDeep(question, 20);
  const clusterResults = searchClustersDeep(question, 10);

  // Synthesize lenses: each cluster becomes a perspective
  const perspectives = clusterResults.slice(0, depth).map((c, i) => ({
    lens: body.lenses?.[i] || `perspective-${i + 1}`,
    source: c.cluster.title,
    keywords: c.cluster.keywords,
    fragments: nodeResults
      .filter((n) => n.node.label.toLowerCase().includes(
        c.cluster.keywords[0]?.toLowerCase() || "",
      ))
      .slice(0, 3)
      .map((n) => ({
        id: n.node.id,
        preview: n.node.content_preview || "",
        source: n.node.source,
      })),
    relevance: c.score,
  }));

  // Build oracle synthesis
  const strongSources = clusterResults.filter((c) => c.score >= 24);
  const moderateSources = clusterResults.filter(
    (c) => c.score >= 12 && c.score < 24,
  );

  const synthesis = {
    question,
    depth,
    total_clusters: clusterResults.length,
    total_fragments: nodeResults.length,
    strong_sources: strongSources.length,
    moderate_sources: moderateSources.length,
    verdict:
      strongSources.length >= 3
        ? "Well-supported — multiple knowledge clusters converge"
        : strongSources.length >= 1
          ? "Partially supported — some convergence, moderate confidence"
          : "Speculative — limited cluster convergence, treat as exploration",
    epistemic_tag:
      strongSources.length >= 3
        ? "Proven"
        : strongSources.length >= 1
          ? "Promising"
          : "Speculative",
    perspectives,
    top_clusters: clusterResults.slice(0, 5).map((c) => ({
      title: c.cluster.title,
      keywords: c.cluster.keywords,
      relevance: c.score,
    })),
    timestamp: new Date().toISOString(),
  };

  return NextResponse.json(synthesis);
}
