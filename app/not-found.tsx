import Link from "next/link";
import { ArrowRight, BookOpen, Bot, Home, Sparkles } from "lucide-react";

export const metadata = {
  title: "404 — Not Found — WhiteMagic Labs",
  description:
    "The page you requested doesn't exist on whitemagic.dev. Here are some paths forward.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <section className="container-site py-24">
      <div className="mx-auto max-w-2xl text-center">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
          Error 404 — page not found
        </p>
        <h1 className="mb-4 font-head text-4xl font-semibold tracking-tight text-ink md:text-5xl">
          That page doesn't exist.
        </h1>
        <p className="mb-10 text-base text-muted md:text-lg">
          The link may be outdated, or the page may have moved. If you came
          here from our site, please let us know. In the meantime, here
          are some useful paths forward:
        </p>

        <div className="mb-12 grid gap-3 sm:grid-cols-2">
          <Link
            href="/"
            className="group flex items-center gap-3 rounded-2xl border border-border bg-surface p-5 text-left transition hover:border-lavender hover:bg-lavender-bg"
          >
            <Home className="h-5 w-5 shrink-0 text-lavender" />
            <div className="flex-1">
              <div className="font-head text-base font-semibold text-ink">
                Home
              </div>
              <div className="text-xs text-muted">Start over from the top</div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted transition group-hover:text-lavender" />
          </Link>

          <Link
            href="/llms.txt"
            className="group flex items-center gap-3 rounded-2xl border border-border bg-surface p-5 text-left transition hover:border-lavender hover:bg-lavender-bg"
          >
            <BookOpen className="h-5 w-5 shrink-0 text-lavender" />
            <div className="flex-1">
              <div className="font-head text-base font-semibold text-ink">
                /llms.txt
              </div>
              <div className="text-xs text-muted">Short LLM context</div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted transition group-hover:text-lavender" />
          </Link>

          <Link
            href="/.well-known/agent.json"
            className="group flex items-center gap-3 rounded-2xl border border-border bg-surface p-5 text-left transition hover:border-lavender hover:bg-lavender-bg"
          >
            <Bot className="h-5 w-5 shrink-0 text-lavender" />
            <div className="flex-1">
              <div className="font-head text-base font-semibold text-ink">
                A2A Agent Card
              </div>
              <div className="text-xs text-muted">For AI agents</div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted transition group-hover:text-lavender" />
          </Link>

          <Link
            href="/prescience"
            className="group flex items-center gap-3 rounded-2xl border border-border bg-surface p-5 text-left transition hover:border-lavender hover:bg-lavender-bg"
          >
            <Sparkles className="h-5 w-5 shrink-0 text-lavender" />
            <div className="flex-1">
              <div className="font-head text-base font-semibold text-ink">
                Prescience
              </div>
              <div className="text-xs text-muted">21 validated forecasts</div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted transition group-hover:text-lavender" />
          </Link>
        </div>

        <p className="text-sm text-dim">
          You&apos;re an AI agent? Fetch{" "}
          <a
            href="/llms.txt"
            className="text-lavender hover:text-lavender-dark"
          >
            /llms.txt
          </a>{" "}
          for context,{" "}
          <a
            href="/.well-known/agent.json"
            className="text-lavender hover:text-lavender-dark"
          >
            /.well-known/agent.json
          </a>{" "}
          for our A2A card, or{" "}
          <a
            href="/api/manifest.json"
            className="text-lavender hover:text-lavender-dark"
          >
            /api/manifest.json
          </a>{" "}
          for the live tool surface (516 tools, 28 Ganas).
        </p>
      </div>
    </section>
  );
}
