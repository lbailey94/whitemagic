import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import { InstallPrompt } from "@/components/InstallPrompt";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  manifest: "/manifest.json",
  title: "WhiteMagic — Local Memory OS",
  description:
    "Local-first cognitive OS running entirely in your browser via WASM. Memory, governance, karma, and self-introspection — zero network calls.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "WhiteMagic",
  },
  icons: {
    icon: "/icons/icon-192x192.png",
    apple: "/icons/icon-192x192.png",
  },
};

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-bg text-fg antialiased">
        <ThemeProvider>{children}<InstallPrompt /></ThemeProvider>
      </body>
    </html>
  );
}
