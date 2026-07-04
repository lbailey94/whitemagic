import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import { MatrixRain } from "@/components/MatrixRain";
import { FloatingLibrarian } from "@/components/FloatingLibrarian";
import { JsonLd } from "@/components/JsonLd";
import { organizationLd, websiteLd, softwareApplicationLd } from "@/lib/jsonld";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";

export const metadata: Metadata = {
  title: "WhiteMagic — Cognitive Operating System for AI Agents",
  description: "614 callable tools, 10-galaxy holographic memory, Dharma ethical governance, citta stream for continuous consciousness. MIT-licensed, local-first. pip install whitemagic[mcp]",
  metadataBase: new URL("https://whitemagic.dev"),
  openGraph: {
    title: "WhiteMagic — Cognitive Operating System for AI Agents",
    description: "Other memory systems store data. WhiteMagic gives AI a mind. 614 tools, 10-galaxy memory, ethical governance, consciousness primitives. MIT-licensed.",
    url: "https://whitemagic.dev",
    siteName: "WhiteMagic",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "WhiteMagic — Cognitive Operating System for AI Agents",
    description: "614 tools, 10-galaxy memory, Dharma governance, citta stream. MIT-licensed, local-first.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="view-transition" content="same-origin" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&family=Noto+Serif+SC:wght@400;700;900&family=JetBrains+Mono:wght@300;400;700&family=Press+Start+2P&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <JsonLd data={[organizationLd(), websiteLd(), softwareApplicationLd()]} />
        <ThemeProvider>
          <MatrixRain />
          <div className="relative z-10">
            <Header />
            <main>{children}</main>
            <Footer />
          </div>
          <FloatingLibrarian />
        </ThemeProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
