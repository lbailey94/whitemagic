import createMDX from "@next/mdx";

/** @type {import('next').NextConfig} */
const nextConfig = {
  pageExtensions: ["ts", "tsx", "md", "mdx"],
  experimental: {
    mdxRs: true,
  },
  async rewrites() {
    return [
      // Expose agent-addressable well-known surfaces at canonical paths.
      {
        source: "/.well-known/agent-economy.json",
        destination: "/api/well-known/agent-economy",
      },
      {
        source: "/.well-known/ai-agent-policy",
        destination: "/api/well-known/ai-agent-policy",
      },
      {
        source: "/.well-known/ai-agent-policy.json",
        destination: "/api/well-known/ai-agent-policy",
      },
      // A2A Protocol v1.2 Agent Card. Spec: https://github.com/google/A2A
      {
        source: "/.well-known/agent.json",
        destination: "/api/well-known/agent",
      },
      {
        source: "/.well-known/agent",
        destination: "/api/well-known/agent",
      },
    ];
  },
};

const withMDX = createMDX({});

export default withMDX(nextConfig);
