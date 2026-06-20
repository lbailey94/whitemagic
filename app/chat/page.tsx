/**
 * /chat — Magic Chat migration page.
 *
 * Replaces the legacy chat.whitemagic.dev (Vercel project "magic-chat",
 * 203d old, now archived). The actual chat UI is the existing
 * <LibrarianChat /> component (driven by the budget-capped
 * /api/librarian/chat endpoint, per site AGENTS.md §2).
 *
 * This page exists so chat.whitemagic.dev has a stable URL after we
 * migrate the domain to whitemagic-site.
 */

import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { LibrarianChat } from "@/components/LibrarianChat";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Chat with Aria — WhiteMagic Labs",
  description:
    "Talk to Aria, the site-aware AI assistant for WhiteMagic Labs. Same AI as the /librarian page; this URL preserves the legacy chat.whitemagic.dev link.",
};

export default function ChatPage() {
  return (
    <>
      <PageHeader
        eyebrow="Aria"
        title="Chat with Aria."
        lede="Talk to Aria — the site-aware AI that knows the public WhiteMagic corpus. Same engine as the /librarian page; this URL exists for legacy chat.whitemagic.dev users."
      />

      <section className="container-site py-8 md:py-12">
        <LibrarianChat />
      </section>

      <section className="border-t border-border-light bg-surface-alt py-12">
        <div className="container-site mx-auto max-w-3xl">
          <Prose>
            <h2>What this is</h2>
            <p>
              This page is the migration target for the legacy
              <code className="text-lavender"> chat.whitemagic.dev </code>
              domain. The original chat was a thin client-side SPA
              backed by an API endpoint that has since been retired.
              Rather than preserve the old client (which depended on
              three different now-deprecated services), we rebuilt the
              same user-facing surface on top of the canonical
              <Link href="/librarian" className="text-lavender underline">
                /librarian
              </Link>{" "}
              engine. Same AI, same budget caps, same dharma governance
              — different stack underneath.
            </p>
            <p>
              The legacy chat was an Aria personality SPA (no real
              retrieval, no library tools, no dharma rules). The new
              chat inherits the v22.2.x{" "}
              <Link href="/mcp-bridge" className="text-lavender underline">
                MCP bridge
              </Link>{" "}
              surface, so it can answer questions about any of the 490
              tools, the v22.5.0 release notes, the 12 zodiac cores,
              the 64 hexagrams, and the rest of the public WhiteMagic
              corpus.
            </p>
            <h2>Constraints (per site AGENTS.md §2)</h2>
            <p>
              This chat is budget-capped at $25/month. Each request
              routes through the same dharma governance as every other
              tool dispatch. Aria will refuse to answer questions that
              fall outside the public WhiteMagic scope.
            </p>
          </Prose>
        </div>
      </section>
    </>
  );
}
