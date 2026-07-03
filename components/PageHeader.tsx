export interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  lede?: string;
}

export function PageHeader({ eyebrow, title, lede }: PageHeaderProps) {
  return (
    <section className="border-b border-border-light bg-surface-alt">
      <div className="container-site max-w-3xl py-16 md:py-24">
        {eyebrow && (
          <p className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
            {eyebrow}
          </p>
        )}
        <h1 className="mb-5 font-head text-4xl font-semibold leading-tight tracking-tight text-ink md:text-5xl">
          {title}
        </h1>
        {lede && (
          <p className="max-w-prose text-lg leading-relaxed text-muted">
            {lede}
          </p>
        )}
      </div>
    </section>
  );
}
