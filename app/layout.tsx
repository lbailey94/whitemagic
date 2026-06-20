import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import { MatrixRain } from "@/components/MatrixRain";
import { FloatingLibrarian } from "@/components/FloatingLibrarian";
import { JsonLd } from "@/components/JsonLd";
import { WipBanner } from "@/components/WipBanner";
import { WipScrambleAll } from "@/components/WipScrambleAll";
import { WIP_MODE, WIP_SCRAMBLE } from "@/lib/wip";
import { organizationLd, websiteLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: WIP_MODE
    ? "WhiteMagic — A door is opening"
    : "WhiteMagic Labs — Private AI Deployment",
  description: WIP_MODE
    ? "A local-first cognitive substrate. Permanent, private, yours. Subscribe to be notified when the public beta opens."
    : "Private AI systems deployed on your infrastructure. Persistent memory, tool use, governance, full audit — your data never leaves the building.",
  metadataBase: new URL("https://whitemagic.dev"),
  openGraph: {
    title: WIP_MODE ? "WhiteMagic — A door is opening" : "WhiteMagic Labs",
    description: WIP_MODE
      ? "A local-first cognitive substrate. Permanent, private, yours."
      : "Private AI deployment for regulated enterprises.",
    url: "https://whitemagic.dev",
    siteName: WIP_MODE ? "WhiteMagic" : "WhiteMagic Labs",
    type: "website",
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
      <body className={WIP_SCRAMBLE ? "wip-scrambling" : ""}>
        <WipScrambleAll />
        <JsonLd data={[organizationLd(), websiteLd()]} />
        <ThemeProvider>
          <MatrixRain />
          <div className="relative z-10">
            <WipBanner />
            <Header />
            <main>{children}</main>
            <Footer />
          </div>
          <FloatingLibrarian />
        </ThemeProvider>
      </body>
    </html>
  );
}
