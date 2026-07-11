import { PageHeader } from "@/components/PageHeader";
import Link from "next/link";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Subscribe — WhiteMagic",
  description:
    "Subscribe to WhiteMagic updates. Be notified when the public beta opens, when the PWA ships, and when new substrate features land.",
};

const WHAT_YOU_GET = [
  "Public beta access the moment it opens",
  "PWA release notification (installable local-first substrate)",
  "New capability announcements (tools, governance, polyglot)",
  "Major version releases with changelog highlights",
  "Occasional strategic essays before they go public",
];

const ROADMAP = [
  { phase: "Now", status: "v23.0.0-alpha.1 — galactic substrate rehydration", done: true },
  { phase: "Next", status: "PWA release — installable, offline-capable substrate", done: false },
  { phase: "Soon", status: "Public beta — open registration, full tool surface", done: false },
  { phase: "Later", status: "Polyglot restoration — Rust, Zig, Elixir runtimes reactivated", done: false },
];

export default function SubscribePage() {
  return (
    <>
      <PageHeader
        eyebrow="Subscribe"
        title="Be the first to know when the door opens."
        lede={`The public beta is being prepared. Subscribe and you'll be the first to hear when the PWA ships, when the substrate is installable, and when new features land. No spam, no SaaS email service — just a quiet note when something real is ready. Current state: ${WM_FACTS.version}, ${WM_FACTS.callableTools} tools, ${WM_FACTS.testsPassing} passing tests.`}
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-2xl">
          {/* Value props */}
          <div className="mb-8 rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-4 font-head text-lg font-semibold text-ink">
              What you get
            </h2>
            <ul className="space-y-2">
              {WHAT_YOU_GET.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-muted">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-lavender" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Roadmap */}
          <div className="mb-8 rounded-2xl border border-border bg-surface-alt p-6">
            <h2 className="mb-4 font-head text-lg font-semibold text-ink">
              Where the project is
            </h2>
            <div className="space-y-3">
              {ROADMAP.map((item) => (
                <div key={item.phase} className="flex items-center gap-3">
                  <span
                    className={`h-2 w-2 flex-shrink-0 rounded-full ${
                      item.done ? "bg-green-500" : "bg-lavender/40"
                    }`}
                  />
                  <span className="font-mono text-xs uppercase tracking-wider text-dim w-12 flex-shrink-0">
                    {item.phase}
                  </span>
                  <span className="text-sm text-muted">{item.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Form */}
          <form
            data-no-scramble
            className="rounded-xl border border-border bg-surface p-6"
            action="mailto:whitemagicdev@proton.me"
            method="post"
            encType="text/plain"
          >
            <p className="mb-4 text-sm text-muted">
              We don&apos;t run a SaaS email service. Subscribing is a one-line
              email — your address goes into a single local list, owned by
              the maintainer, and is deleted on request.
            </p>
            <label className="block">
              <span className="mb-1 block font-mono text-[10px] uppercase tracking-widest text-dim">
                Your email
              </span>
              <input
                type="email"
                name="email"
                required
                placeholder="you@example.com"
                className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-ink focus:border-lavender focus:outline-none"
              />
            </label>
            <label className="mt-4 block">
              <span className="mb-1 block font-mono text-[10px] uppercase tracking-widest text-dim">
                Message (optional)
              </span>
              <textarea
                name="message"
                rows={3}
                placeholder="Anything you'd like the maintainer to know."
                className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-ink focus:border-lavender focus:outline-none"
              />
            </label>
            <button
              type="submit"
              className="mt-4 w-full rounded-md bg-lavender px-4 py-2 font-mono text-xs uppercase tracking-widest text-bg hover:bg-lavender-dark"
            >
              Send a note (opens your email client)
            </button>
            <p className="mt-4 text-xs text-dim">
              For the time being, this opens your email client with a
              pre-filled message. A real form lands with the PWA.
            </p>
          </form>

          <p className="mt-8 text-sm text-muted">
            Or explore the substrate now:{" "}
            <Link href="/mcp-bridge" className="text-lavender underline-offset-4 hover:underline">
              browse the bridge catalog
            </Link>
            ,{" "}
            <Link href="/chat" className="text-lavender underline-offset-4 hover:underline">
              chat with Aria
            </Link>
            , or{" "}
            <Link
              href="/.well-known/agent.json"
              className="text-lavender underline-offset-4 hover:underline"
            >
              read the A2A Agent Card
            </Link>
            .
          </p>
        </div>
      </section>
    </>
  );
}
