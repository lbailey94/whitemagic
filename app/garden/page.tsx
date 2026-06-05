/**
 * Garden — Password-protected Vaya Vida research portal
 *
 * This route is gated by the same Basic Auth middleware as /admin.
 * Future: link to the full Vaya Vida technospiritual research garden
 * with concept graph, knowledge sphere, and multilingual essays.
 */

export default function GardenPage() {
  return (
    <div className="min-h-screen bg-cream">
      <main className="mx-auto max-w-3xl px-6 py-24">
        <h1 className="font-head text-4xl font-bold text-ink">
          Garden
        </h1>
        <p className="mt-4 text-lg text-muted">
          A protected research space for deep-garden exploration.
        </p>

        <div className="mt-12 space-y-6">
          <section className="rounded-xl border border-border bg-surface p-6">
            <h2 className="font-head text-xl font-semibold text-ink">
              Vaya Vida
            </h2>
            <p className="mt-2 text-muted">
              Technospiritual research portal. 3D knowledge sphere,
              40 interconnected documents, client-side semantic search,
              and multilingual support.
            </p>
            <p className="mt-4 text-sm text-dim">
              Status: Offline — integration in progress.
            </p>
          </section>

          <section className="rounded-xl border border-border bg-surface p-6">
            <h2 className="font-head text-xl font-semibold text-ink">
              The Book of Becoming
            </h2>
            <p className="mt-2 text-muted">
              A living document mapping 64 concepts across the I Ching,
              zodiac, and cognitive architecture. A blueprint for
              technospiritual synthesis.
            </p>
            <p className="mt-4 text-sm text-dim">
              Status: Draft — not yet public.
            </p>
          </section>

          <section className="rounded-xl border border-border bg-surface p-6">
            <h2 className="font-head text-xl font-semibold text-ink">
              CODEX Archive
            </h2>
            <p className="mt-2 text-muted">
              316+ AI-assisted conversations from May 2025–April 2026,
              documenting the research lineage behind WhiteMagic.
            </p>
            <p className="mt-4 text-sm text-dim">
              Status: Private — access by invitation only.
            </p>
          </section>
        </div>

        <p className="mt-12 text-xs text-dim">
          This garden is password-protected. If you need access,
          contact the site administrator.
        </p>
      </main>
    </div>
  );
}
