import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import { MatrixRain } from "@/components/MatrixRain";
import { FloatingLibrarian } from "@/components/FloatingLibrarian";
import { JsonLd } from "@/components/JsonLd";
import { organizationLd, websiteLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "WhiteMagic Labs — Private AI Deployment",
  description:
    "Private AI systems deployed on your infrastructure. Persistent memory, tool use, governance, full audit — your data never leaves the building.",
  metadataBase: new URL("https://whitemagic.dev"),
  openGraph: {
    title: "WhiteMagic Labs",
    description: "Private AI deployment for regulated enterprises.",
    url: "https://whitemagic.dev",
    siteName: "WhiteMagic Labs",
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
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&family=Noto+Serif+SC:wght@400;700;900&family=JetBrains+Mono:wght@300;400;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <JsonLd data={[organizationLd(), websiteLd()]} />
        <ThemeProvider>
          <MatrixRain />
          <div className="relative z-10">
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
