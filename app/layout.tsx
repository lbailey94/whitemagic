import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import { MatrixRainLazy } from "@/components/MatrixRainLazy";
import { InstallPrompt } from "@/components/InstallPrompt";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  manifest: "/manifest.json",
  title: "WhiteMagic — Cognitive Operating System for AI Agents",
  description:
    "860 callable tools, 14-galaxy holographic memory, Dharma ethical governance, citta stream for continuous consciousness. MIT-licensed, local-first, free forever.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "WhiteMagic",
  },
  icons: {
    icon: "/icons/icon-192x192.png",
    apple: "/icons/icon-192x192.png",
  },
  keywords: [
    "AI memory",
    "MCP server",
    "cognitive OS",
    "agent consciousness",
    "persistent memory",
    "holographic memory",
    "Dharma governance",
    "Karma ledger",
    "dream cycle",
    "citta stream",
  ],
  authors: [{ name: "Lucas Bailey" }],
  openGraph: {
    title: "WhiteMagic — Cognitive Operating System for AI Agents",
    description:
      "Other memory systems store data. WhiteMagic gives AI a mind. 860 tools, 14-galaxy memory, ethical governance, consciousness primitives. MIT-licensed.",
    type: "website",
    url: "https://whitemagic.dev",
    siteName: "WhiteMagic",
  },
  twitter: {
    card: "summary_large_image",
    title: "WhiteMagic — Cognitive OS for AI Agents",
    description:
      "860 tools, 14-galaxy memory, Dharma governance, citta stream. MIT-licensed, local-first.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    types: {
      "application/json": "https://whitemagic.dev/.well-known/agent.json",
    },
  },
};

export const viewport: Viewport = {
  themeColor: "#7c3aed",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-bg text-fg antialiased">
        <ThemeProvider>
          <MatrixRainLazy />
          {children}
          <InstallPrompt />
        </ThemeProvider>
      </body>
    </html>
  );
}
