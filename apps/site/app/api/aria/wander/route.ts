import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Aria Wander — Serendipitous knowledge traversal
 *
 * GET /api/aria/wander?seed=consciousness&steps=8
 * POST /api/aria/wander
 * Body: { seed: string, steps?: number, diversity?: boolean }
 *
 * Follows link chains through the knowledge sphere, optionally
 * preferring diverse sources. Returns a wander path with step-by-step
 * narration.
 */

interface SphereNode {
  id: string;
  label: string;
  source: string;
  token_count: number;
  content_preview?: string;
  links: Array<{ target: string; similarity: number; rank: number }>;
}

function loadNodes(): SphereNode[] {
  const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
  const raw = fs.readFileSync(fp, "utf-8");
  return (JSON.parse(raw) as { nodes: SphereNode[] }).nodes;
}

function findSeed(seed: string): SphereNode | null {
  const nodes = loadNodes();
  const seedLower = seed.toLowerCase();
  const terms = seedLower.split(/\s+/).filter(Boolean);

  // First try: exact label match
  const exact = nodes.find(
    (n) => n.label.toLowerCase() === seedLower,
  );
  if (exact) return exact;

  // Second: best keyword match
  let best: { node: SphereNode; score: number } | null = null;
  for (const node of nodes) {
    let score = 0;
    const text = ((node.content_preview || "") + " " + (node.label || "")).toLowerCase();
    for (const term of terms) {
      if (text.includes(term)) score += term.length;
    }
    if (score > 0 && (!best || score > best.score)) {
      best = { node, score };
    }
  }

  return best?.node || null;
}

function wander(
  seedNode: SphereNode,
  steps: number,
  diversity: boolean,
): Array<{
  step: number;
  node: SphereNode;
  link_strength: number;
  narration: string;
}> {
  const nodes = loadNodes();
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const visited = new Set<string>();
  const path: Array<{
    step: number;
    node: SphereNode;
    link_strength: number;
    narration: string;
  }> = [];

  let current = seedNode;
  visited.add(current.id);
  path.push({
    step: 0,
    node: current,
    link_strength: 1.0,
    narration: `Starting at "${current.label}" — a ${current.source} document with ${current.token_count} tokens.`,
  });

  const seenSources = new Set<string>([current.source]);

  for (let step = 1; step <= steps; step++) {
    const links = (current.links || [])
      .filter((l) => !visited.has(l.target))
      .sort((a, b) => b.similarity - a.similarity);

    if (links.length === 0) break;

    let chosen = links[0];
    let chosenNode = nodeMap.get(chosen.target);

    // If diversity mode, prefer unvisited sources
    if (diversity && links.length > 1) {
      const novel = links.find(
        (l) => {
          const n = nodeMap.get(l.target);
          return n && !seenSources.has(n.source);
        },
      );
      if (novel) {
        chosen = novel;
        chosenNode = nodeMap.get(novel.target);
      }
    }

    if (!chosenNode) break;

    visited.add(chosenNode.id);
    seenSources.add(chosenNode.source);

    const sourceLabel =
      chosenNode.source !== current.source
        ? ` — new source: ${chosenNode.source}`
        : "";

    path.push({
      step,
      node: chosenNode,
      link_strength: chosen.similarity,
      narration: `Linked to "${chosenNode.label}" (similarity: ${chosen.similarity.toFixed(3)}, rank: ${chosen.rank})${sourceLabel}.`,
    });

    current = chosenNode;
  }

  return path;
}

function generateSummary(path: ReturnType<typeof wander>): string {
  if (path.length <= 1) return "The wander found no connected paths.";

  const sources = [...new Set(path.map((p) => p.node.source))];
  const avgStrength =
    path.slice(1).reduce((s, p) => s + p.link_strength, 0) /
      (path.length - 1) || 0;
  const topicSpread = path.map((p) => p.node.label);

  return `Wandered ${path.length} nodes across ${sources.length} sources (avg link strength: ${avgStrength.toFixed(3)}). Path: ${topicSpread.slice(0, 5).join(" → ")}${path.length > 5 ? " → …" : ""}.`;
}

export async function POST(request: Request) {
  let body: { seed?: string; steps?: number; diversity?: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  return handleWander(body.seed, body.steps, body.diversity);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const seed = searchParams.get("seed")?.trim();
  const steps = parseInt(searchParams.get("steps") || "8", 10);
  const diversity = searchParams.get("diversity") !== "false";

  if (!seed) {
    return NextResponse.json(
      {
        mode: "wander",
        status: "ready",
        description:
          "Aria Wander — serendipitous knowledge traversal.",
        usage: "GET /api/aria/wander?seed=consciousness&steps=8&diversity=true",
      },
    );
  }

  return handleWander(seed, steps, diversity);
}

function handleWander(
  seed: string | undefined,
  steps: number | undefined,
  diversity: boolean | undefined,
) {
  if (!seed) {
    return NextResponse.json(
      { error: "Missing 'seed' parameter" },
      { status: 400 },
    );
  }

  const maxSteps = Math.min(steps || 8, 20);
  const preferDiversity = diversity !== false;

  const seedNode = findSeed(seed);
  if (!seedNode) {
    return NextResponse.json(
      {
        mode: "wander",
        seed,
        error: "No matching seed node found",
        suggestion: "Try a broader topic or a specific concept",
      },
    );
  }

  const path = wander(seedNode, maxSteps, preferDiversity);

  return NextResponse.json({
    mode: "wander",
    seed,
    diversity_preference: preferDiversity,
    summary: generateSummary(path),
    steps: path.length,
    max_requested: maxSteps,
    path: path.map((p) => ({
      step: p.step,
      id: p.node.id,
      label: p.node.label,
      source: p.node.source,
      link_strength: p.link_strength,
      tokens: p.node.token_count,
      preview: p.node.content_preview || "",
      narration: p.narration,
    })),
    timestamp: new Date().toISOString(),
  });
}
