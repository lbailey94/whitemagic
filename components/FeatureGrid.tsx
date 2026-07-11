import type { Feature } from "@/lib/data/governance";
export function FeatureGrid({ items }: { items: Feature[] }) {
  return (<section className="container-site py-16"><div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
    {items.map((f) => (<div key={f.title} className="rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender/40">
      <f.icon className="mb-4 h-8 w-8 text-lavender" />
      <h3 className="font-head text-lg font-semibold text-ink">{f.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">{f.desc}</p>
    </div>))}
  </div></section>);
}