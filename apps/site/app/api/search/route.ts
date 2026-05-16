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

let cachedData: SphereData | null = null;

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

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim().toLowerCase();
  const limit = Math.min(
    parseInt(searchParams.get("limit") || "10", 10),
    50,
  );
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

  // Score nodes by term frequency in content_preview
  const scored = data.nodes
    .filter((node) => {
      if (source && node.source !== source) return false;
      return true;
    })
    .map((node) => {
      const preview = (node.content_preview || "").toLowerCase();
      let score = 0;
      for (const term of terms) {
        const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
        const matches = preview.match(regex);
        if (matches) score += matches.length * 10;
        if (preview.includes(term)) score += 5;
      }
      return { ...node, _score: score };
    })
    .filter((node) => node._score > 0)
    .sort((a, b) => b._score - a._score)
    .slice(0, limit)
    .map(({ _score, ...node }) => ({
      id: node.id,
      source: node.source,
      score: _score,
      token_count: node.token_count,
      preview: node.content_preview || "",
      links: node.links.slice(0, 3),
    }));

  return NextResponse.json({
    query: q,
    total_results: scored.length,
    results: scored,
  });
}
