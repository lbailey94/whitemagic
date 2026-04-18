import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LibrarianChat } from "@/components/LibrarianChat";

export const metadata = {
  title: "Librarian — WhiteMagic Labs",
  description:
    "Ask the Librarian about WhiteMagic, the services Lucas offers, pricing, and the open-source platform. Scope is the public site; no private material.",
};

export default function LibrarianPage() {
  return (
    <>
      <PageHeader
        eyebrow="Librarian"
        title="Ask the Librarian."
        lede="A site-aware AI that knows the public WhiteMagic corpus — services, pricing, timeline, open-source components — and can help you find what you need. Not a substitute for a real conversation with Lucas, but a decent first pass."
      />

      <section className="container-site py-8 md:py-12">
        <LibrarianChat />
      </section>

      <section className="border-t border-border-light bg-surface-alt py-12">
        <div className="container-site mx-auto max-w-3xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            How this works
          </p>
          <h2 className="mb-5 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Transparent, budget-capped, kill-switchable.
          </h2>
          <ul className="mb-6 space-y-3 text-sm leading-relaxed text-muted">
            <li>
              <strong className="text-fg">Scope</strong> — the Librarian
              only knows what&apos;s on the public site. It will refuse
              questions about private material, Lucas&apos;s personal
              life, or unreleased work.
            </li>
            <li>
              <strong className="text-fg">Guardrails</strong> — each
              visitor message is checked against the same Dharma Rules
              Engine that ships in WhiteMagic core. Jailbreak attempts,
              off-scope requests, and crisis topics are refused before
              any LLM call. (We eat our own dogfood in public.)
            </li>
            <li>
              <strong className="text-fg">Rate limits</strong> — 30
              messages per IP per day; sessions cap at 40 messages. Hard
              monthly budget cap with automatic cutoff.
            </li>
            <li>
              <strong className="text-fg">No retention</strong> —
              conversations are not stored server-side. They live in
              your browser tab and vanish when you close it.
            </li>
            <li>
              <strong className="text-fg">Source citations</strong> —
              the Librarian is instructed to cite the specific page or
              section behind its answers.
            </li>
          </ul>

          <div className="flex flex-wrap gap-3">
            <Link href="/contact" className="btn-primary">
              Reach Lucas directly
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/open-source" className="btn-secondary">
              Dharma Rules source
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
