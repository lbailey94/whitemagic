import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Resonance Model API
 *
 * GET /api/resonance?doc=id1&doc=id2 — pairwise resonance
 * GET /api/resonance?query=text — query-document resonance
 * GET /api/resonance/overview — system-wide resonance heatmap
 *
 * Resonance = cosine similarity × novelty multiplier × source diversity bonus.
 * Higher resonance means stronger conceptual alignment across the knowledge base.
 */

interface SphereNode {
  id: string;
  label: string;
  source: string;
  content_preview?: string;
}

function loadNodes(): SphereNode[] {
  const fp = path.join(process.cwd(), "public", "sphere-nodes.json");
  return (JSON.parse(fs.readFileSync(fp, "utf-8")) as { nodes: SphereNode[] })
    .nodes;
}

// Simplified resonance: term overlap × source diversity
function computeResonance(a: string, b: string, sourceA: string, sourceB: string): number {
  const termsA = new Set(
    a.toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 2),
  );
  const termsB = b.toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 2);

  let overlap = 0;
  const allTerms = new Set([...termsA, ...termsB]);
  for (const t of termsB) {
    if (termsA.has(t) && t.length > 2) overlap++;
  }

  const jaccard = allTerms.size > 0 ? overlap / allTerms.size : 0;
  const sourceBonus = sourceA !== sourceB ? 0.15 : -0.1; // Cross-source diversity
  const noveltyMultiplier = 1.0 + (1.0 - jaccard) * 0.3;

  return Math.min(1.0, Math.max(0.0, jaccard * noveltyMultiplier + sourceBonus));
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const doc1 = searchParams.get("doc1");
  const doc2 = searchParams.get("doc2");
  const query = searchParams.get("query");
  const limit = Math.min(parseInt(searchParams.get("limit") || "5", 10), 20);

  // Overview mode — top resonating pairs from key topics
  if (searchParams.get("overview") !== null || (!doc1 && !query)) {
    const nodes = loadNodes();
    const keyTopics = [
      "consciousness", "intelligence", "governance", "systems",
      "ecology", "memory", "protocol", "architecture",
    ];

    const resonant: Array<{
      topic: string;
      top_pairs: Array<{ a: string; b: string; score: number }>;
    }> = [];

    for (const topic of keyTopics) {
      const matches = nodes.filter(
        (n) =>
          (n.content_preview || "").toLowerCase().includes(topic) ||
          (n.label || "").toLowerCase().includes(topic),
      );

      const pairs: Array<{ a: string; b: string; score: number }> = [];
      for (let i = 0; i < Math.min(matches.length, 6); i++) {
        for (let j = i + 1; j < Math.min(matches.length, 6); j++) {
          if (matches[i].source !== matches[j].source) {
            const score = computeResonance(
              matches[i].content_preview || "",
              matches[j].content_preview || "",
              matches[i].source,
              matches[j].source,
            );
            pairs.push({
              a: matches[i].label,
              b: matches[j].label,
              score: Math.round(score * 1000) / 1000,
            });
          }
        }
      }
      pairs.sort((a, b) => b.score - a.score);
      if (pairs.length > 0) {
        resonant.push({ topic, top_pairs: pairs.slice(0, 3) });
      }
    }

    return NextResponse.json({
      mode: "overview",
      topics_analyzed: keyTopics.length,
      active_topics: resonant.length,
      resonant_topics: resonant.sort((a, b) => a.top_pairs.length - b.top_pairs.length).reverse(),
      note: "Resonance = Jaccard overlap × novelty × source diversity. Cross-source pairs show emergent connections.",
      timestamp: new Date().toISOString(),
    });
  }

  // Pairwise resonance
  if (doc1) {
    const nodes = loadNodes();
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    if (doc2) {
      // Specific pair
      const n1 = nodeMap.get(doc1);
      const n2 = nodeMap.get(doc2);
      if (!n1 || !n2) {
        return NextResponse.json({ error: "One or both documents not found" }, { status: 404 });
      }
      const score = computeResonance(
        n1.content_preview || "",
        n2.content_preview || "",
        n1.source,
        n2.source,
      );
      return NextResponse.json({
        mode: "pair",
        doc1: { id: n1.id, label: n1.label, source: n1.source },
        doc2: { id: n2.id, label: n2.label, source: n2.source },
        resonance: Math.round(score * 1000) / 1000,
        source_diversity: n1.source !== n2.source,
      });
    }

    // doc1 vs all others (ranked)
    const n1 = nodeMap.get(doc1);
    if (!n1) {
      return NextResponse.json({ error: "Document not found" }, { status: 404 });
    }
    const ranked = nodes
      .filter((n) => n.id !== doc1)
      .map((n) => ({
        id: n.id,
        label: n.label,
        source: n.source,
        resonance: computeResonance(
          n1.content_preview || "",
          n.content_preview || "",
          n1.source,
          n.source,
        ),
      }))
      .sort((a, b) => b.resonance - a.resonance)
      .slice(0, limit);

    return NextResponse.json({
      mode: "ranked",
      anchor: { id: n1.id, label: n1.label, source: n1.source },
      results: ranked.map((r) => ({
        ...r,
        resonance: Math.round(r.resonance * 1000) / 1000,
      })),
    });
  }

  // Query resonance
  if (query) {
    const nodes = loadNodes();
    const ranked = nodes
      .map((n) => ({
        id: n.id,
        label: n.label,
        source: n.source,
        resonance: computeResonance(query, n.content_preview || "", "query", n.source),
      }))
      .sort((a, b) => b.resonance - a.resonance)
      .slice(0, limit);

    return NextResponse.json({
      mode: "query",
      query,
      results: ranked.map((r) => ({
        ...r,
        resonance: Math.round(r.resonance * 1000) / 1000,
      })),
      timestamp: new Date().toISOString(),
    });
  }

  return NextResponse.json({
    usage: {
      pairwise: "/api/resonance?doc1=id&doc2=id",
      ranked: "/api/resonance?doc1=id",
      query: "/api/resonance?query=text",
      overview: "/api/resonance?overview",
    },
  });
}
