import type { MetadataRoute } from "next";

const BASE_URL = "https://whitemagic.dev";

const ROUTES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/mcp-bridge", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/open-source", priority: 0.9, changeFrequency: "weekly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/governance", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/about", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/research", priority: 0.8, changeFrequency: "weekly" as const },
  { path: "/timeline", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/performance", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/economy", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/fund", priority: 0.6, changeFrequency: "monthly" as const },
  { path: "/contact", priority: 0.6, changeFrequency: "yearly" as const },
  { path: "/library", priority: 0.6, changeFrequency: "weekly" as const },
  { path: "/chat", priority: 0.6, changeFrequency: "monthly" as const },
  { path: "/librarian", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/galaxy", priority: 0.5, changeFrequency: "weekly" as const },
  { path: "/work", priority: 0.4, changeFrequency: "monthly" as const },
  { path: "/writing", priority: 0.4, changeFrequency: "monthly" as const },
  // Machine-readable agent surfaces
  { path: "/llms.txt", priority: 0.5, changeFrequency: "weekly" as const },
  { path: "/llms-full.txt", priority: 0.5, changeFrequency: "weekly" as const },
  { path: "/.well-known/agent.json", priority: 0.5, changeFrequency: "weekly" as const },
  { path: "/api/manifest.json", priority: 0.4, changeFrequency: "weekly" as const },
  { path: "/api/mcp-bridge.json", priority: 0.4, changeFrequency: "weekly" as const },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map(({ path, priority, changeFrequency }) => ({
    url: `${BASE_URL}${path}`,
    lastModified,
    changeFrequency,
    priority,
  }));
}
