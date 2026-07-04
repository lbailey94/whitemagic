import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const allowedCrawlers = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "anthropic-ai",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Bingbot",
    "Amazonbot",
    "Applebot",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "FacebookBot",
    "Meta-ExternalAgent",
    "Googlebot",
    "AhrefsBot",
  ];

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/admin", "/dashboard"],
      },
      ...allowedCrawlers.map((ua) => ({
        userAgent: ua,
        allow: "/",
      })),
    ],
    sitemap: "https://whitemagic.dev/sitemap.xml",
    host: "https://whitemagic.dev",
  };
}
