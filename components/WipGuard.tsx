import { WIP_MODE } from "@/lib/wip";
import Link from "next/link";

/**
 * Guard component: replaces a page's content with a WIP placeholder
 * when the route is hidden in WIP mode. Use as the first child of
 * a page that should be obscured during the rewrite.
 *
 * Renders nothing (returns the children as-is) when WIP_MODE is false.
 */
export function WipGuard({ children }: { children: React.ReactNode }) {
  if (!WIP_MODE) {
    return <>{children}</>;
  }
  return <WipPlaceholder />;
}

function WipPlaceholder() {
  return (
    <section className="container-site py-20">
      <div className="mx-auto max-w-2xl text-center">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
          Work in Progress
        </p>
        <h1 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink">
          This page is being rewritten.
        </h1>
        <p className="mb-8 text-lg leading-relaxed text-muted">
          The content that used to live here is being re-thought. Subscribe
          to be notified when the public version returns, or explore the
          substrate now.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/subscribe" className="btn-primary">
            Subscribe to the beta
          </Link>
          <Link href="/" className="btn-ghost">
            Back to the door
          </Link>
        </div>
      </div>
    </section>
  );
}
