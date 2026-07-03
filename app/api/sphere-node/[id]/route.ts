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

let nodeMap: Map<string, SphereNode> | null = null;

function loadNodeMap(): Map<string, SphereNode> {
  if (nodeMap) return nodeMap;
  const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
  const raw = fs.readFileSync(fp, "utf-8");
  const data = JSON.parse(raw) as { version: string; nodes: SphereNode[] };
  nodeMap = new Map(data.nodes.map((n) => [n.id, n]));
  return nodeMap;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  try {
    const map = loadNodeMap();
    const node = map.get(id);

    if (!node) {
      return NextResponse.json({ error: "Node not found" }, { status: 404 });
    }

    return NextResponse.json({
      id: node.id,
      label: node.label,
      source: node.source,
      token_count: node.token_count,
      content_preview: node.content_preview || "",
      links: node.links,
    });
  } catch {
    return NextResponse.json(
      { error: "Sphere data not available" },
      { status: 503 },
    );
  }
}
