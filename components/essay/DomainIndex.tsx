import { EssayCard, type EssayMeta } from "@/components/essay/EssayCard";

interface DomainIndexProps {
  domain: string;
  title: string;
  description: string;
  essays: EssayMeta[];
}

export function DomainIndex({
  domain,
  title,
  description,
  essays,
}: DomainIndexProps) {
  const published = essays.filter((e) => e.ready);
  const drafts = essays.filter((e) => !e.ready);

  return (
    <main className="container-site py-16">
      <nav className="mb-8">
        <a
          href="/essays"
          className="font-mono text-sm text-lavender hover:text-lavender-dark"
        >
          ← All essays
        </a>
      </nav>

      <header className="mb-12">
        <p className="font-mono text-sm uppercase tracking-wider text-lavender">
          {domain}
        </p>
        <h1 className="mt-2 font-head text-4xl font-semibold text-ink">
          {title}
        </h1>
        <p className="mt-4 max-w-prose text-lg text-muted">{description}</p>
      </header>

      {published.length > 0 ? (
        <section className="mb-12">
          <ul className="mx-auto max-w-3xl space-y-4">
            {published.map((essay) => (
              <li key={essay.slug}>
                <EssayCard essay={essay} />
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="mb-12 text-muted">No published essays yet.</p>
      )}

      {drafts.length > 0 && (
        <section>
          <h2 className="mb-6 font-mono text-sm uppercase tracking-wider text-dim">
            Drafts
          </h2>
          <ul className="mx-auto max-w-3xl space-y-4">
            {drafts.map((essay) => (
              <li key={essay.slug}>
                <EssayCard essay={essay} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
