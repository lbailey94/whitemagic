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
import { WipUnregisterSw } from "@/components/WipUnregisterSw";
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
        {/* Synchronous scramble shim. Runs as soon as the body is
            parsed, before React hydrates. Scrambles every text node
            immediately so there's no flicker. React re-renders that
            reset the text are caught by the MutationObserver in
            WipScrambleAll. */}
        {WIP_SCRAMBLE ? (
          <script
            dangerouslySetInnerHTML={{
              __html: `(function(){if(typeof document==="undefined")return;var G="0123456789",S=1597334671>>>0,SK=new Set(["SCRIPT","STYLE","CODE","PRE","TEXTAREA","INPUT","SELECT","OPTION","NOSCRIPT","TEMPLATE","SVG","IFRAME","EMBED","OBJECT"]);function sc(t){var o="",s=S>>>0;for(var i=0;i<t.length;i++){var c=t[i];if(c===" "||c==="\\n"||c==="\\t"){o+=c}else if(/[a-zA-Z0-9]/.test(c)){s=(s*1664525+1013904223)>>>0;o+=G[s%G.length]}else{o+=c}}return o}function sk(e){for(var c=e;c;){if(SK.has(c.tagName))return true;if(c.hasAttribute&&(c.hasAttribute("data-no-scramble")||c.hasAttribute("data-wip-scrambled")))return true;c=c.parentElement}return false}function sn(n){if(!n.nodeValue)return;var p=n.parentElement;if(!p)return;if(sk(p))return;if(p.hasAttribute("data-original-text"))return;if(!n.nodeValue.trim())return;var o=n.nodeValue;p.setAttribute("data-original-text",o);n.nodeValue=sc(o)}function w(r){var x=document.createTreeWalker(r,NodeFilter.SHOW_TEXT);var n;while(n=x.nextNode())sn(n)}w(document.body);document.body.classList.remove("wip-scrambling");document.body.classList.add("wip-scrambled");document.documentElement.setAttribute("data-wip-scrambled-by","inline-shim");var pending=false;function sched(muts){if(pending)return;pending=true;requestAnimationFrame(function(){pending=false;for(var i=0;i<muts.length;i++){var m=muts[i];if(m.type==="characterData"&&m.target.nodeType===3){var t=m.target,p=t.parentElement;if(p&&!sk(p)){var o=p.getAttribute("data-original-text");if(o&&t.nodeValue===o){t.nodeValue=sc(o)}else if(o){p.setAttribute("data-original-text",o)}}}else if(m.type==="childList"){m.addedNodes.forEach(function(n){if(n.nodeType===3)sn(n);else if(n.nodeType===1)w(n)})}}});}new MutationObserver(sched).observe(document.body,{childList:true,subtree:true,characterData:true,characterDataOldValue:false})})();`,
            }}
          />
        ) : null}
        <WipScrambleAll />
        <WipUnregisterSw />
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
