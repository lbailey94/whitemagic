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

interface LiteNode {
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
}

let liteCache: { version: string; nodes: LiteNode[] } | null = null;

export async function GET() {
  if (liteCache) {
    return NextResponse.json(liteCache);
  }

  try {
    const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
    const raw = fs.readFileSync(fp, "utf-8");
    const data = JSON.parse(raw) as { version: string; nodes: SphereNode[] };

    const liteNodes: LiteNode[] = data.nodes.map(
      ({ content_preview: _, ...rest }) => rest,
    );

    liteCache = { version: data.version, nodes: liteNodes };
    return NextResponse.json(liteCache);
  } catch {
    return NextResponse.json(
      { error: "Sphere data not available" },
      { status: 503 },
    );
  }
}
