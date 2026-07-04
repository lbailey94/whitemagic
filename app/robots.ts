import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const allowedCrawlers = [
    "GPTBot",
    "OAI-SearchBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "Bingbot",
    "Amazonbot",
    "Applebot",
    "Bytespider",
    "CCBot",
    "FacebookBot",
    "Googlebot",
  ];

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/admin", "/api/aria/", "/dashboard", "/api/librarian/"],
      },
      ...allowedCrawlers.map((ua) => ({
        userAgent: ua,
        allow: "/",
        disallow: ["/admin", "/api/aria/", "/dashboard"],
      })),
    ],
    sitemap: "https://whitemagic.dev/sitemap.xml",
    host: "https://whitemagic.dev",
  };
}
