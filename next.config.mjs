import createMDX from "@next/mdx";
import withPWAInit from "@ducanh2912/next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  sw: "sw.js",
  buildExcludes: ["app-build-manifest.json"],
  cacheOnFrontEndNav: true,
  aggressiveFrontEndNavCaching: true,
  reloadOnOnline: true,
  swcMinify: true,
  workboxOptions: {
    disableDevLogs: true,
    navigateFallback: "",
    runtimeCaching: [
      {
        urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "google-fonts-cache",
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365,
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      {
        urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "gstatic-fonts-cache",
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365,
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      {
        urlPattern: /\/api\/.*/i,
        handler: "NetworkFirst",
        options: {
          cacheName: "api-cache",
          expiration: {
            maxEntries: 50,
            maxAgeSeconds: 60 * 60 * 24,
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
          networkTimeoutSeconds: 10,
        },
      },
      {
        urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
        handler: "CacheFirst",
        options: {
          cacheName: "static-images",
          expiration: {
            maxEntries: 100,
            maxAgeSeconds: 60 * 60 * 24 * 30,
          },
        },
      },
      // WASM modules — cache permanently
      {
        urlPattern: /\/wasm\/.*\.(?:wasm|js)$/i,
        handler: "CacheFirst",
        options: {
          cacheName: "wasm-modules",
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      // ONNX models — cache permanently
      {
        urlPattern: /\/models\/.*\.(?:onnx|bin)$/i,
        handler: "CacheFirst",
        options: {
          cacheName: "onnx-models",
          expiration: {
            maxEntries: 5,
            maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      // SQLite WASM (sql.js)
      {
        urlPattern: /^https:\/\/cdn\.jsdelivr\.net\/npm\/sql\.js@.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "sqljs-wasm",
          expiration: {
            maxEntries: 5,
            maxAgeSeconds: 60 * 60 * 24 * 365,
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      // ONNX Runtime Web WASM files
      {
        urlPattern: /^https:\/\/cdn\.jsdelivr\.net\/npm\/onnxruntime-web@.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "onnxruntime-wasm",
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365,
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
    ],
  },
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  pageExtensions: ["ts", "tsx", "md", "mdx"],
  // Pin file-tracing root to this project to silence the multi-lockfile
  // workspace-root inference warning (a stray package-lock.json exists in $HOME).
  outputFileTracingRoot: process.cwd(),
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
      // Expose .json variants of API endpoints for agent discoverability.
      // Agents in the wild fetch /api/foo.json by convention; these rewrites
      // strip the suffix and route to the actual handler.
      {
        source: "/api/manifest.json",
        destination: "/api/manifest",
      },
      {
        source: "/api/prescience.json",
        destination: "/api/prescience",
      },
      {
        source: "/api/sangha.json",
        destination: "/api/sangha",
      },
      {
        source: "/api/zodiac.json",
        destination: "/api/zodiac",
      },
      // WhiteMagic Core API proxy — disabled until Hetzner VPS is up.
      // Re-enable with the public Hetzner URL when ready:
      //   destination: "https://api.whitemagic.dev/:path*",
      // {
      //   source: "/api/wm/:path*",
      //   destination: "http://127.0.0.1:8770/:path*",
      // },
      // {
      //   source: "/sync",
      //   destination: "http://127.0.0.1:8770/sync",
      // },
    ];
  },
};

const withMDX = createMDX({});

export default withPWA(withMDX(nextConfig));
