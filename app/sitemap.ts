import type { MetadataRoute } from "next";

const BASE_URL = "https://whitemagic.dev";

const ROUTES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/app", priority: 0.9, changeFrequency: "weekly" as const },
  // Machine-readable agent surfaces
  { path: "/llms.txt", priority: 0.9, changeFrequency: "weekly" as const },
  { path: "/.well-known/agent.json", priority: 0.9, changeFrequency: "weekly" as const },
  { path: "/server.json", priority: 0.8, changeFrequency: "weekly" as const },
  { path: "/mcp-registry.json", priority: 0.8, changeFrequency: "weekly" as const },
  { path: "/manifest.json", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/api/manifest.json", priority: 0.7, changeFrequency: "weekly" as const },
  { path: "/api/prescience.json", priority: 0.6, changeFrequency: "monthly" as const },
  { path: "/robots.txt", priority: 0.5, changeFrequency: "monthly" as const },
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
