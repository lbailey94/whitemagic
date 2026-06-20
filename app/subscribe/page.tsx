import { PageHeader } from "@/components/PageHeader";
import Link from "next/link";

export const metadata = {
  title: "Subscribe — WhiteMagic",
  description:
    "Subscribe to the WhiteMagic beta. Be notified when the public beta opens, when the PWA ships, and when new substrate features land.",
};

export default function SubscribePage() {
  return (
    <>
      <PageHeader
        eyebrow="Subscribe"
        title="Be notified when the door opens."
        lede="The public beta is being prepared. Subscribe and you'll be the first to know when the PWA ships, when the substrate is installable, and when new features land."
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-xl">
          <form
            className="rounded-xl border border-border bg-surface p-6"
            action="mailto:whitemagicdev@proton.me"
            method="post"
            encType="text/plain"
          >
            <p className="mb-4 text-sm text-muted">
              We don't run a SaaS email service. Subscribing is a one-line
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
              Subscribe (opens your email client)
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
              talk to Aria
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
