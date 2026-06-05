import type { MetadataRoute } from "next";

const BASE_URL = "https://whitemagic.dev";

const ROUTES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/services", priority: 0.9, changeFrequency: "monthly" as const },
  {
    path: "/services/private-ai-deployment",
    priority: 0.9,
    changeFrequency: "monthly" as const,
  },
  {
    path: "/services/agent-governance",
    priority: 0.9,
    changeFrequency: "monthly" as const,
  },
  {
    path: "/services/mcp-engineering",
    priority: 0.9,
    changeFrequency: "monthly" as const,
  },
  { path: "/ladder", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/governance", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/prescience", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/timeline", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/about", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/contact", priority: 0.8, changeFrequency: "yearly" as const },
  { path: "/economy", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/fund", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/becoming", priority: 0.6, changeFrequency: "monthly" as const },
  { path: "/sphere", priority: 0.7, changeFrequency: "weekly" as const },
  { path: "/library", priority: 0.7, changeFrequency: "weekly" as const },
  { path: "/research", priority: 0.8, changeFrequency: "weekly" as const },
  { path: "/research/convergence-2026", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/research/may-2-window", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/research/survival-guide-2026", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/open-source", priority: 0.7, changeFrequency: "weekly" as const },
  { path: "/work", priority: 0.6, changeFrequency: "weekly" as const },
  { path: "/writing", priority: 0.7, changeFrequency: "weekly" as const },
  { path: "/zh", priority: 0.4, changeFrequency: "monthly" as const },
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
